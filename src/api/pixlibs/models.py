# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# Declarative database class 

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

Base = declarative_base()

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True)
    hashed_password = Column(String(128), unique=True)
    firstname = Column(String(64), nullable=True, index=True)
    lastname = Column(String(64), nullable=True, index=True)
    isadmin = Column(Boolean, default=False, index=True)
    disabled= Column(Boolean, default=False, index=True)
    pref_model = Column(Integer, default=0, index=True)
