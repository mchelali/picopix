# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# API

# Declare libraries
from fastapi import FastAPI,Header,HTTPException, Depends, status, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Annotated
from pydantic import BaseModel
from pixlibs.models import Users
from pixlibs.models import Base
from pixlibs.database import engine, SessionLocal
from pixlibs.auth import get_current_user
import pixlibs.auth
import os

# Etablish db connexion
pixlibs.models.Base.metadata.create_all(bind=engine)

# Declare API
app = FastAPI(
    title="ColorPix",
    description="DST MLops Image Colorization Project",
    version="0.1"
)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Declare Endpoints
# Authentication endpoints
app.include_router(pixlibs.auth.router)

# PostgreSQL Database session function
def get_db():
    db = pixlibs.database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# endpoints dependency
# database access is ok
db_dependency = Annotated[Session, Depends(get_db)]
# user authentication is ok
user_dependency = Annotated[dict, Depends(get_current_user)]

# root endpoint
@app.get('/')
def root():
    """Affiche le message : Welcome to ColorPix !
    """
    return {'message': "Welcome to ColorPix !"}

# favicon endpoint
@app.get('/favicon.ico')
async def favicon():
    file_name = "favicon.ico"
    file_path = os.path.join(app.root_path, "static", file_name)
    return FileResponse(path=file_path, headers={"Content-Disposition": "attachment; filename=" + file_name})

# authorized endpoint test
@app.get('/authonly', status_code=status.HTTP_200_OK)
def authonly(user: user_dependency, db: db_dependency):
    """Affiche le message : ColorPix access granted!
    """
    if user is None:
        raise HTTPEXception(status_code=401, detail='Authentication Failed')
    return {'message': "ColorPix access granted!"}
