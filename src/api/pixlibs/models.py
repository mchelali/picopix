# Projet PicoPix
# Autheurs : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# Classes Base de données

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

# Déclaration des classes pour la base de données (tables)
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    username = Column(String(64), primary_key=True, unique=True, index=True)
    firstname = Column(String(64), nullable=False, index=True)
    lastname = Column(String(64), nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    isadmin = Column(Boolean, default=False, index=True)
    disabled= Column(Boolean, default=False, index=True)
    pref_model = Column(Integer, default=0, index=True)

    bw_images = relationship("BW_Image",foreign_keys="bw_images.username")
    color_images = relationship("COLOR_Image",foreign_keys="color_images.username")

class BW_Image(Base):
    __tablename__ = "bw_images"

    bw_image_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), ForeignKey("users.username"))
    filename = Column(String, nullable=False, index=True)
    filepath = Column(String, nullable=False, index=True)
    add_date = Column(DateTime, default=datetime.now(timezone.utc))

    color_images = relationship("COLOR_Image",foreign_keys="color_images.color_image_id")

class COLOR_Image(Base):
    __tablename__ = "color_images"

    color_image_id = Column(Integer, primary_key=True, index=True)
    bw_image_id = Column(Integer, ForeignKey("bw_images.bw_image_id"))
    mlmodel_id = Column(Integer, ForeignKey("mlmodels.mlmodel_id"))
    username = Column(String(64), ForeignKey("users.username"))
    filename = Column(String, nullable=False, index=True)
    filepath = Column(String, nullable=False, index=True)
    rating = Column(Integer)
    creation_date = Column(DateTime, default=datetime.now(timezone.utc))

class Model(Base):
    __tablename__ = "mlmodels"

    mlmodel_id = Column(Integer, primary_key=True, index=True)
    tag = Column(Integer, default=0)
    disabled = Column(Boolean, default=False, index=True)
    filename = Column(String, nullable=False, index=True)
    filepath = Column(String, nullable=False, index=True)
    creation_date = Column(DateTime, default=datetime.now(timezone.utc))
    score = Column(Integer,nullable=False)

    color_images = relationship("COLOR_Image",foreign_keys="color_images.color_image_id")

