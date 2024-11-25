# Projet PicoPix
# Autheurs : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# Classes API

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

# Classes BW Images
class BW_Image(BaseModel):
    bw_image_id: int
    username: str
    filename: str
    filepath: str
    add_date: datetime

# Classes BW Images
class COLOR_Image(BaseModel):
    color_image_id: int 
    bw_image_id: int 
    mlmodel_id : int 
    username: str
    filename: str
    filepath: str
    creation_date: datetime

# Classes Utilisateurs
class UserBase(BaseModel):
    username: str | None = None

class UserCreate(UserBase):
    password: str | None = None

class User(UserBase):
    firstname: str | None = None
    lastname: str | None = None
    isadmin: bool | None = None
    disabled: bool | None = None
    pref_model: int | None = None
    bw_images: List[BW_Image] = []
    color_images: List[COLOR_Image] = []

# Classes Token
class Token(BaseModel):
        access_token: str
        token_type: str

class TokenData(BaseModel):
     username: str | None = None



