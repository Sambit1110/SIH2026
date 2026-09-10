from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings


def _build_engine(use_null_pool: bool = True):
    url = settings.database_url

    if url.startswith("sqlite"):
        # check_same_thread=False: FastAPI may hand the connection to a
        # different thread than the one that created it within one request.
        return create_engine(url, connect_args={"check_same_thread": False})

    # Postgres (Supabase). Two adaptations matter here that wouldn't matter
    # for a traditional long-lived server process:
    #
    # 1. NullPool (default, use_null_pool=True) -- a serverless function
    #    instance handles a handful of requests at most before being
    #    recycled, so maintaining SQLAlchemy's own connection pool across
    #    invocations buys nothing and can leak stale connections. Supabase's
    #    own "Transaction" pooler (pgbouncer, typically the :6543 connection
    #    string) is the intended place for connection pooling in this
    #    architecture -- see DATABASE_URL in .env.example.
    #
    #    use_null_pool=False is for the opposite situation: a single,
    #    long-running local process that issues many sequential commits in
    #    one run (the seed script -- see app/seed/seed_data.py). NullPool
    #    closes the underlying connection on every commit, so a
    #    many-commits-per-run script would open a fresh authenticated
    #    connection to Supabase's Session Pooler on every single commit --
    #    harmless in isolation, but enough rapid reconnect churn in one
    #    script run to occasionally trip the pooler's own connection/auth
    #    handling. A single reused connection for the process's lifetime
    #    avoids that entirely and is the appropriate choice for a script,
    #    not a serverless function.
    # 2. sslmode=require -- Supabase Postgres requires TLS; psycopg2 doesn't
    #    default to it, so we set it explicitly unless the URL already
    #    specifies a sslmode (e.g. a user who wants sslmode=verify-full).
    connect_args = {"sslmode": "require"} if "sslmode=" not in url else {}
    poolclass = NullPool if use_null_pool else None  # None -> SQLAlchemy's default pool (QueuePool)
    kwargs = {"pool_pre_ping": True, "connect_args": connect_args}
    if poolclass is not None:
        kwargs["poolclass"] = poolclass
    else:
        kwargs["pool_size"] = 1
        kwargs["max_overflow"] = 0
    return create_engine(url, **kwargs)


def build_session_local(use_null_pool: bool = True) -> sessionmaker:
    """Builds an independent engine + sessionmaker against the same
    DATABASE_URL. Used by the seed script to get connection-reuse behavior
    (use_null_pool=False) without altering the shared `engine`/`SessionLocal`
    below, which the live API depends on and which is already verified
    against production Supabase."""
    return sessionmaker(autocommit=False, autoflush=False, bind=_build_engine(use_null_pool=use_null_pool))


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
