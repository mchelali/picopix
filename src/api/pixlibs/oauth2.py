# Projet PicoPix
# Autheurs : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# Oauth2 Fonctions

# Déclarations Librairies
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional
from jwt import *
import json
import time
from dotenv import load_dotenv
from . import models, schemas
from passlib.context import CryptContext
import os

# Load .env environment variables
load_dotenv()
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
AUTH_ALGORITHM = os.getenv("AUTH_ALGORITHM")
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES"))

pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def getSignature(base64Header,base64Payload,secret):
    # print

    block = base64Header.decode('utf-8') + "." + base64Payload.decode('utf-8')
    digest = hmac.new(bytes(secret,'utf-8'),block.encode('utf-8'), digestmod = hashlib.sha256).digest()
    # Digest sometimes returns non alphanumeric characters
    signature = base64.urlsafe_b64encode(digest)
    return signature.decode('utf-8')[: -1]

def encodeJWT(data,key,algorithm):
  payload = data
  # payload={
  # "sub": "1234567890",
  # "name": "John Doe",
  # "iat": 1516239022
  # }
  header = {
  "alg": algorithm,
  "typ": "JWT"
  }
  base64Header = base64.b64encode(json.dumps(header).encode("utf-8"))
  # Dumping header and payload dictionaries to string then encoding in bytes and then finally encoding in base64 bytes
  base64Payload = base64.b64encode(json.dumps(payload).encode("utf-8"))
  sig = getSignature(base64Header,base64Payload,key)
  encodedJWT = base64Header.decode("utf-8")+"."+base64Payload.decode("utf-8")+"."+sig
  return encodedJWT

def decodeJWT(access_token,key):
  header = access_token.split('.')[0]
  payload = access_token.split('.')[1]
  decodedPayload = base64.b64decode(payload)
  sig = getSignature(header.encode('utf-8'),payload.encode('utf-8'),key)
  res = {
    "payload":decodedPayload.decode('utf-8'),
    "verified":(sig==access_token.split('.')[2])
  }
  if(sig==access_token.split('.')[2]):
    return res
  else:
    return "Couldn't Verify Signature"

def verify_hash(password,hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire.isoformat()})
    encoded_jwt = encodeJWT(to_encode, AUTH_SECRET_KEY , algorithm=AUTH_ALGORITHM)
    return encoded_jwt


def get_current_user(token):
    decoded = decodeJWT(token, AUTH_SECRET_KEY)
    # email: str = payload["sub"]
    username = json.loads(decoded["payload"])["sub"]
    return user_email
    # if username is None:
    #     raise credentials_exception
    # token_data = TokenData(username=username)
    # except JWTError:
    #     raise credentials_exception
    # user = get_user(fake_users_db, username=token_data.username)
    # if user is None:
    #     raise credentials_exception
    # return user