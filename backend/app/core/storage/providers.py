"""Evidence storage provider abstraction.

`LocalStorageProvider` writes/reads a local directory -- convenient for local
development (SQLite mode), but incompatible with Vercel's read-only
deployment filesystem (only `/tmp` is writable there, and it's wiped between
cold starts, so it cannot hold evidence durably).

`SupabaseStorageProvider` uploads/downloads via the Supabase Storage REST
API using the **service role key**, which is a server-side-only secret that
bypasses Row Level Security and Storage bucket policies. The bucket backing
this provider must be created as **private** (not public) -- see
`backend/supabase/migrations/0001_init_schema.sql`. Evidence is never made
publicly accessible; every read goes through this authenticated provider,
which only this backend process holds credentials for.

Selection is automatic: if `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are
both configured, Supabase is used (required in production/Vercel, since the
local filesystem isn't durable there); otherwise the local filesystem is used
(convenient for offline local development).
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import requests

from app.config import settings


class EvidenceStorageProvider(ABC):
    @abstractmethod
    def upload(self, filename: str, content: bytes) -> str:
        """Stores `content` and returns an opaque storage key/path that
        `download()` can later resolve. Never returns a public URL."""

    @abstractmethod
    def download(self, storage_key: str) -> bytes | None:
        """Returns the stored bytes, or None if the object cannot be found."""

    name: str


class LocalStorageProvider(EvidenceStorageProvider):
    name = "local"

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or settings.evidence_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix or ".eml"
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        path = self.base_dir / stored_name
        path.write_bytes(content)
        return str(path)

    def download(self, storage_key: str) -> bytes | None:
        path = Path(storage_key)
        if not path.exists():
            return None
        return path.read_bytes()


class SupabaseStorageProvider(EvidenceStorageProvider):
    name = "supabase"

    def __init__(self):
        self.base_url = settings.supabase_url.rstrip("/")
        self.bucket = settings.supabase_storage_bucket
        self._headers = {
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
        }

    def _object_url(self, storage_key: str) -> str:
        return f"{self.base_url}/storage/v1/object/{self.bucket}/{storage_key}"

    def upload(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix or ".eml"
        storage_key = f"{uuid.uuid4().hex}{suffix}"
        resp = requests.post(
            self._object_url(storage_key),
            headers={**self._headers, "Content-Type": "message/rfc822"},
            data=content,
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Supabase Storage upload failed ({resp.status_code}): {resp.text[:300]}")
        return storage_key

    def download(self, storage_key: str) -> bytes | None:
        resp = requests.get(self._object_url(storage_key), headers=self._headers, timeout=15)
        if resp.status_code != 200:
            return None
        return resp.content


def get_evidence_storage() -> EvidenceStorageProvider:
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseStorageProvider()
    return LocalStorageProvider()
