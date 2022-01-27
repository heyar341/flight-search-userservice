from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from os import environ

DRIVER = "postgresql+psycopg2"
USER = environ.get("POSTGRES_USER")
PASSWORD = environ.get("POSTGRES_PASSWORD")
HOST = environ.get("POSTGRES_HOST")
PORT = environ.get("POSTGRES_PORT")
DB_NAME = environ.get("POSTGRES_DB")

SQL_ALCHEMY_DATABASE_URL = f"{DRIVER}://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"

engine = create_engine(SQL_ALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
