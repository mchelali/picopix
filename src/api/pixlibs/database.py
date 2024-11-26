# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# PostgreSQL Database session connexion

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os

# Load .env environment variables
load_dotenv()

# PostgreSQL database connexion string
DATABASE_URL = f"postgresql://{os.getenv("POSTGRES_USER")}:{os.getenv("POSTGRES_PASSWORD")}@postgres/{os.getenv("POSTGRES_DB")}"

# engine & session declaration
engine = create_engine(DATABASE_URL, connect_args={})
#SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal = sessionmaker(bind=engine)

