import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
from sqlalchemy.pool import QueuePool
import redis

redis_client = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)

DATABASE_URL = f"postgresql://{settings.DATABASE_USERNAME}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOSTNAME}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables!")

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,  
    pool_size=20,         
    max_overflow=0,    
    echo=False  
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def shutdown_database():
    engine.dispose()
