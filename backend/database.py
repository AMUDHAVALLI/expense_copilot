import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

load_dotenv()

# Read Vercel Postgres / Neon / Supabase environment variables
raw_url = (
    os.getenv("POSTGRES_URL") 
    or os.getenv("DATABASE_URL") 
    or os.getenv("DATABASE_URL_UNPOOLED")
    or "postgresql://postgres:root@localhost:5432/expense_copilot"
)

# Normalize URL for SQLAlchemy (postgres:// -> postgresql://)
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

# Check if running in a serverless environment (e.g. Vercel)
is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

engine_kwargs = {
    "pool_pre_ping": True,
}

if is_serverless:
    # Use NullPool in serverless environments to prevent connection exhaustion
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

try:
    engine = create_engine(raw_url, **engine_kwargs)
    db_type = "PostgreSQL"
except Exception as e:
    print(f"[DB] PostgreSQL engine initialization warning: {e}")
    engine = None
    db_type = "PostgreSQL (Configuring)"

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    if engine is None:
        raise RuntimeError("PostgreSQL database engine is not initialized. Check DATABASE_URL or POSTGRES_URL.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
