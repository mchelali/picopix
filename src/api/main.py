# Declare libraries
from fastapi import FastAPI,Header,HTTPException, Depends, status, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
import pixlibs.models
from pixlibs.database import SessionLocal, engine, get_db
import pixlibs.oauth2
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
# root
@app.get('/')
def root():
    """Affiche le message : Welcome to ColorPix !
    """
    return {'message': "Welcome to ColorPix !"}

# favicon
@app.get('/favicon.ico')
async def favicon():
    file_name = "favicon.ico"
    file_path = os.path.join(app.root_path, "static", file_name)
    return FileResponse(path=file_path, headers={"Content-Disposition": "attachment; filename=" + file_name})
