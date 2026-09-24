import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = (
    "postgresql+psycopg://"
    f"{os.getenv('POSTGRES_USER', 'appuser')}:{os.getenv('POSTGRES_PASSWORD', 'apppassword')}@"
    f"{os.getenv('DATABASE_HOST', 'database')}:5432/{os.getenv('POSTGRES_DB', 'microservices')}"
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()