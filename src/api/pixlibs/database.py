# Projet PicoPix
# Autheurs : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# Connexion à la base de données PostgreSQL

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Chargement des variables d'environnement
load_dotenv()

# Declaration base de données PostgreSQL
DATABASE_URL = f"postgresql://{os.getenv("POSTGRES_USER")}:{os.getenv("POSTGRES_PASSWORD")}@postgres/{os.getenv("POSTGRES_DB")}"
engine = create_engine(DATABASE_URL, connect_args={})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Connexion base de données PostgreSQL
def get_db():
    db = SessionLocal()
    try:
        yield db
    except:
        print("Error: unable to etablish postgresql database connection.")  
    finally:
        db.close()