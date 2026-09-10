import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["DATABASE_URL"] = "sqlite:///./test_trace_x.db"
# The test suite must be fully hermetic -- offline, deterministic, and never
# touching live infrastructure -- regardless of what real credentials happen
# to exist in backend/.env for local Supabase development. Without this,
# get_evidence_storage() would resolve to SupabaseStorageProvider the moment
# a developer configures real Supabase credentials locally, silently
# uploading every test run's synthetic evidence to the real Storage bucket.
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    db_file = Path("test_trace_x.db")
    if db_file.exists():
        db_file.unlink()


@pytest.fixture()
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c
