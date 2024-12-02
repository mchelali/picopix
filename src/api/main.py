# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# API

# Declare libraries
from fastapi import FastAPI, Header, HTTPException, Depends, status, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc,asc
from typing import Annotated
from pydantic import BaseModel
from starlette.background import BackgroundTasks
from pixlibs.models import Users
from pixlibs.models import Base
from pixlibs.database import engine, SessionLocal
from pixlibs.auth import get_current_user, get_user_data
#from pixlibs.storage_minio import get_storage, storageclient
#import pixlibs.storage_minio
from pixlibs.storage_boto3 import get_storage, storageclient
import pixlibs.storage_boto3
import pixlibs.auth
import tempfile
import os
import io
import cv2
import time
import numpy as np
from dotenv import load_dotenv

# Load .env environment variables
load_dotenv()
IMG_SIZE_H_MIN = os.getenv("IMG_SIZE_H_MIN")
IMG_SIZE_W_MIN = os.getenv("IMG_SIZE_W_MIN")
IMG_SIZE_H_MAX = os.getenv("IMG_SIZE_H_MAX")
IMG_SIZE_W_MAX = os.getenv("IMG_SIZE_W_MAX")
IMG_SIZE_KB_MAX = os.getenv("IMG_SIZE_KB_MAX")
AWS_BUCKET_MEDIA = os.getenv("AWS_BUCKET_MEDIA")

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
# storage access is ok
storage_dependency = Annotated[storageclient, Depends(get_storage)]

# root endpoint
@app.get('/')
def root():
    """
    Description
    -----------
    Endpoint : Show message : Welcome to ColorPix !

    Returns
    -------
    string
    """
    return {'message': "Welcome to ColorPix !"}

# favicon endpoint
@app.get('/favicon.ico')
async def favicon():
    file_name = "favicon.ico"
    file_path = os.path.join(app.root_path, "static", file_name)
    return FileResponse(path=file_path, headers={"Content-Disposition": "attachment; filename=" + file_name})

# black & white image upload
@app.post('/upload_bw_image')
async def upload_bw_image(user: user_dependency, db: db_dependency, s3client: storage_dependency, file: UploadFile = File(...)):
    """
    Description
    -----------
    endpoint to upload black & white image

    Parameters
    ----------
    user: oauth2 token required
    db: postgres connexion required
    file: uploaded file  (File)

    Returns
    -------
    string
    """
    # check authentication 
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    # upload file to localhost
    if not file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='No file found.')
    if file.content_type != "image/jpeg":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Bad file format (jpeg only).')
    tempfilename = tempfile.NamedTemporaryFile()
    try:
        contents = file.file.read()
        with open("cache"+tempfilename.name, 'wb') as f:
            f.write(contents)
    except Exception:
        raise HTTPException(status_code=500, detail='Upload to server error.')
    finally:
        file.file.close()

    # check if picture is greyscale & well sized
    if not is_valid_image(f"cache{tempfilename.name}"):
        if os.path.exists(f"cache{tempfilename.name}"):
            # if not ok then delete temporary file
            os.remove(f"cache{tempfilename.name}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Bad file format (only b&w image, {IMG_SIZE_W_MIN}x{IMG_SIZE_H_MIN} min,{IMG_SIZE_W_MAX}x{IMG_SIZE_H_MAX} max).")       
    
    # set new filename (bw_userid_yyyymmdd-hhmmss.jpg)
    s3filename = f"bw_{user['id']}_{time.strftime("%Y%m%d-%H-%M-%S")}.jpg"
    
    # write file to bucket
    try:
        #s3client.fput_object(AWS_BUCKET_MEDIA,s3filename,f"cache{tempfilename.name}","image/jpg")
        s3client.Bucket(AWS_BUCKET_MEDIA,).upload_file(f"cache{tempfilename.name}",s3filename)
        if os.path.exists(f"cache{tempfilename.name}"):
            # if file writed then delete temporary file
            os.remove(f"cache{tempfilename.name}")
    except Exception:
        raise HTTPException(status_code=500, detail='Upload to bucket error.')   

    # add bw image ref to database
    try:
        create_bw_image_model = pixlibs.models.BW_Images(
        filename=s3filename,
        user_id=user['id'],
        )
        db.add(create_bw_image_model)
        db.commit()
    except Exception:
        raise HTTPException(status_code=500, detail='Database write error.')

    # return          
    return {"message": f"Successfully uploaded {file.filename}"}

# Image validity function
def is_valid_image(imgfilename: str):
    """
    Description
    -----------
    this function checks if image is valid (format, greyscale, height, width, size)

    Parameters
    ----------
    imgfilename: file path (string)

    Returns
    -------
    boolean
    """
    try:
    # check file size
        if (os.path.getsize(imgfilename)/1024)>int(IMG_SIZE_KB_MAX):
            return False
        # open image
        img=cv2.imread(imgfilename)
        # split channels
        b,g,r=cv2.split(img)
        # check if image is greyscale
        r_g=np.count_nonzero(abs(r-g))
        r_b=np.count_nonzero(abs(r-b))
        g_b=np.count_nonzero(abs(g-b))
        diff_sum=float(r_g+r_b+g_b)
        ratio=diff_sum/img.size
        if ratio>0.005:
            return False
        # check height and width
        h,w,c = img.shape
        if (w<int(IMG_SIZE_W_MIN) or h<int(IMG_SIZE_H_MIN)):
            return False
        if (w>int(IMG_SIZE_W_MAX) or h>int(IMG_SIZE_H_MAX)):  
            return False
    except Exception:
        return False
    
    # return
    return True

# bw image traitement
@app.get('/colorize_bw_image')
async def colorize_bw_image(user: user_dependency, db: db_dependency, s3client: storage_dependency, bg_tasks: BackgroundTasks):
    """
    Description
    -----------
    endpoint to colorize last black & white image uploaded

    Parameters
    ----------
    user: oauth2 token required
    db: postgres connexion required

    Returns
    -------
    jpeg file
    """
    # check authentication 
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    # check last uploaded file (or none)
    try:
        lastimageobj = db.query(pixlibs.models.BW_Images).filter(pixlibs.models.BW_Images.user_id == user["id"]).order_by(pixlibs.models.BW_Images.filename.desc()).first()
    except:
        raise HTTPException(status_code=500, detail='Database read error.')        

    # copy bw image from bucket to server
    tempbwfilename = tempfile.NamedTemporaryFile()
    try:
        s3client.Bucket(AWS_BUCKET_MEDIA,).download_file(lastimageobj.filename,f"cache{tempbwfilename.name}.jpg")
        #s3client.fget_object(AWS_BUCKET_MEDIA,lastimageobj.filename,f"cache{tempbwfilename.name}.jpg")
    except Exception:
        raise HTTPException(status_code=500, detail='File write error on server (s3->server).')

    # image colorization
    try:
        grayscale_image = cv2.imread(f"cache{tempbwfilename.name}.jpg", cv2.IMREAD_GRAYSCALE)
        rgb_image = cv2.cvtColor(grayscale_image, cv2.COLOR_GRAY2RGB)
        cv2.fillPoly(rgb_image, [np.array([[170,50],[240, 40],[240, 150], [210, 100], [130, 130]], np.int32)], (255,150,255))
    except Exception:
        raise HTTPException(status_code=500, detail='Image read error or colorize error on server.')      

    # write colorized image to server
    tempcolorfilename = tempfile.NamedTemporaryFile()
    try:
        cv2.imwrite(f"cache{tempcolorfilename.name}.jpg", rgb_image)
    except Exception:
        raise HTTPException(status_code=500, detail='File write error on server (server).')

     # write colorized image from server to bucket
    s3colorfilename = f"color_{lastimageobj.user_id}_{lastimageobj.id}_{time.strftime("%Y%m%d-%H-%M-%S")}.jpg"

    try:
        s3client.Bucket(AWS_BUCKET_MEDIA,).upload_file(f"cache{tempcolorfilename.name}.jpg",s3colorfilename)
        #s3client.fput_object(AWS_BUCKET_MEDIA,s3colorfilename,f"cache{tempcolorfilename.name}.jpg","image/jpg")
    except Exception:
        raise HTTPException(status_code=500, detail='File write error on server (server->s3).')

    # delete temporary files
    try:
        if os.path.exists(f"cache{tempbwfilename.name}.jpg"):
            # if file writed then delete temporary file
            os.remove(f"cache{tempbwfilename.name}.jpg")
        if os.path.exists(f"cache{tempcolorfilename.name}.jpg"):
            # if file writed then add background task to delete temporary file after FileResponse return
            bg_tasks.add_task(os.remove, f"cache{tempcolorfilename.name}.jpg")
    except:
        raise HTTPException(status_code=500, detail='Delete file error on server.')             

    # add colororized image ref to database
    try:
        create_color_image_model = pixlibs.models.COLOR_Images(
        filename=s3colorfilename,
        user_id=user['id'],
        bwimage_id=lastimageobj.id
        )
        db.add(create_color_image_model)
        db.commit()
    except:
        raise HTTPException(status_code=500, detail='Database write error.')        

    # return image
    return FileResponse(f"cache{tempcolorfilename.name}.jpg", media_type="image/jpeg", filename=s3colorfilename,background=bg_tasks)