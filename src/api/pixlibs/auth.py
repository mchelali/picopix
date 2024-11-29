# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# Class & Functions for authentication

from datetime import timedelta, datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from . import database
from . import models
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
import os
from dotenv import load_dotenv
import logging

# Ignore passlib warning
logging.getLogger('passlib').setLevel(logging.ERROR)

router = APIRouter(prefix='/auth',tags=['auth'])

# Load .env environment variables
load_dotenv()
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
AUTH_ALGORITHM = os.getenv("AUTH_ALGORITHM")
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES"))

# Set Crypt Context
bcrypt_context = CryptContext(schemes=['bcrypt'],deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

# Create User Request class
class CreateUserRequest(BaseModel):
    username: str
    firstname: str
    lastname: str
    password: str

# Token class
class Token(BaseModel):
    access_token: str
    token_type: str

# PostgreSQL Database session function
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# opened database condition
db_dependency = Annotated[Session, Depends(get_db)]

# token attribution function (call authenticate function)
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    # if bad username or bad password
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='Bad username or bad password.')
    # if username/password are ok, create token
    token = create_access_token(user.username,user.id, timedelta(minutes=AUTH_ACCESS_TOKEN_EXPIRE_MINUTES))
    return {'access_token':token, 'token_type':'bearer'}

# authentication function
def authenticate_user(username: str, password: str, db):
    # check if user is in database
    user = db.query(models.Users).filter(models.Users.username == username).first()
    if not user:
        return False
    # check of user's password (hashed) is same as in database
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    # if user exists and his password is ok, then return user
    return user

# token creation function
def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {'sub':username, 'id': user_id}
    expires = datetime.utcnow() + expires_delta
    encode.update({'exp':expires})
    return jwt.encode(encode, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)

# token verification function
async def get_current_user(token: Annotated[str,Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='Could not validate user.')
        return {'username':username, 'id': user_id}
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='Could not validate user.' )

# creation user function
@router.post("/create_user", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    # declare new object "Users"
    create_user_model = models.Users(
        username=create_user_request.username,
        firstname=create_user_request.firstname,
        lastname=create_user_request.lastname,
        hashed_password=bcrypt_context.hash(create_user_request.password),
    )
    # SQL ADD request
    db.add(create_user_model)
    db.commit()

# get authenticated user data
def get_user_data(db: db_dependency, id: int):
    user = db.query(models.Users).filter(models.Users.id == id).first()
    print(f"prenom:{user.firstname}\nnom:{user.lastname}\nmodèle préféré:{user.pref_model}\n")
    return user