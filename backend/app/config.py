from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000", "http://localhost:3001",
    "http://127.0.0.1:3000", "http://127.0.0.1:3001",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Trace-X"

    # SQLite by default -- zero setup for local development. In production
    # (Vercel) this MUST be a Supabase Postgres connection string; SQLite's
    # on-disk file would not survive between serverless invocations there.
    database_url: str = f"sqlite:///{BASE_DIR / 'trace_x.db'}"

    # Local-filesystem evidence store, used only by LocalStorageProvider
    # (i.e. only when Supabase Storage isn't configured). Vercel's deployed
    # source directory is read-only, so this path is never written to in
    # production -- see app/core/storage/providers.py.
    evidence_dir: Path = BASE_DIR / "evidence_store"

    # "demo" never makes any network call. "live" attempts real lookups
    # (RDAP / DNS / ip-api.com) and falls back to demo data automatically
    # on any error or timeout so the demo can never be broken by the network.
    intel_mode: str = "demo"

    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    allowed_upload_extensions: tuple[str, ...] = (".eml", ".txt")

    # Comma-separated list of allowed frontend origins, e.g.
    # "https://trace-x-frontend.vercel.app,https://trace-x.example.com".
    # Read from CORS_ORIGINS so the deployed Vercel frontend URL never needs
    # to be hardcoded into source -- appended to the localhost defaults so
    # local development keeps working unchanged.
    cors_origins_extra: str = ""

    # Supabase project settings. All optional: when SUPABASE_URL and
    # SUPABASE_SERVICE_ROLE_KEY are both set, evidence storage automatically
    # switches to Supabase Storage (required in production). SUPABASE_ANON_KEY
    # is accepted for completeness/documentation but is never used server-side
    # for privileged operations -- this backend always uses the service role
    # key, which must never be exposed to any client-side code.
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "evidence"

    @property
    def cors_origins(self) -> list[str]:
        extra = [o.strip() for o in self.cors_origins_extra.split(",") if o.strip()]
        return DEFAULT_CORS_ORIGINS + extra

    @property
    def use_supabase_storage(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgres")


settings = Settings()

if not settings.use_supabase_storage:
    # Only touch the filesystem when we're actually going to use it --
    # Vercel's deployed source tree is read-only, and this branch is never
    # taken there once SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY are set.
    settings.evidence_dir.mkdir(parents=True, exist_ok=True)
