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

# token
@app.post("/token", response_model=pixlibs.schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = oauth2.get_user(db, username=form_data.username)
    if not (oauth2.verify_hash(form_data.password,db_user.hashed_password)):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = oauth2.create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token}