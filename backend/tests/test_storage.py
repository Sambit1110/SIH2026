import tempfile
from pathlib import Path

from app.core.storage.providers import (
    LocalStorageProvider,
    SupabaseStorageProvider,
    get_evidence_storage,
)


def test_local_storage_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        provider = LocalStorageProvider(base_dir=Path(tmp))
        key = provider.upload("test.eml", b"hello evidence")
        assert provider.download(key) == b"hello evidence"


def test_local_storage_missing_object_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        provider = LocalStorageProvider(base_dir=Path(tmp))
        assert provider.download(str(Path(tmp) / "does-not-exist.eml")) is None


def test_local_storage_generates_unique_keys():
    with tempfile.TemporaryDirectory() as tmp:
        provider = LocalStorageProvider(base_dir=Path(tmp))
        key1 = provider.upload("a.eml", b"one")
        key2 = provider.upload("a.eml", b"two")
        assert key1 != key2
        assert provider.download(key1) == b"one"
        assert provider.download(key2) == b"two"


def test_factory_picks_local_when_supabase_not_configured(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_service_role_key", "")
    provider = get_evidence_storage()
    assert isinstance(provider, LocalStorageProvider)


def test_factory_picks_supabase_when_configured(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_service_role_key", "fake-service-role-key")
    provider = get_evidence_storage()
    assert isinstance(provider, SupabaseStorageProvider)
