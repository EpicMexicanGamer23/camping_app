from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

#database is the docker compose service name
DATABASE_URL = (
    "postgresql+psycopg://"
    "appuser:apppassword@database:5432/microservices"
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