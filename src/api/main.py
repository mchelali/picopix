# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# API

# Declare libraries
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import desc,asc
from typing import Annotated
from starlette.background import BackgroundTasks
import tempfile
import os
import cv2
import time
import numpy as np
from dotenv import load_dotenv
import logging
from contextlib import asynccontextmanager
from pixlibs.database import engine
import pixlibs.storage_boto3
import pixlibs.auth
from passlib.context import CryptContext
from pixlibs.auth import get_current_user
from pixlibs.storage_boto3 import get_storage, storageclient

# Load .env environment variables
load_dotenv()
IMG_SIZE_H_MIN = os.getenv("IMG_SIZE_H_MIN")
IMG_SIZE_W_MIN = os.getenv("IMG_SIZE_W_MIN")
IMG_SIZE_H_MAX = os.getenv("IMG_SIZE_H_MAX")
IMG_SIZE_W_MAX = os.getenv("IMG_SIZE_W_MAX")
IMG_SIZE_KB_MAX = os.getenv("IMG_SIZE_KB_MAX")
AWS_BUCKET_MEDIA = os.getenv("AWS_BUCKET_MEDIA")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")

# Enable logging
logger = logging.getLogger(__name__)
logging.basicConfig(filename='main.log',filemode="w", encoding='utf-8',level=logging.ERROR, format="%(asctime)s %(levelname)s %(message)s")
def format_logger(user: int, error: str, message: str):
    if len(error)==0:
        return f"User: {user}\tMessage: {message}"
    else:
        return f"User: {user}\tError:{error}\tMessage: {message}" 

# Etablish db connexion
@asynccontextmanager
async def lifespan(application: FastAPI):
    pixlibs.models.Base.metadata.create_all(bind=engine)
    yield

# Declare API
app = FastAPI(
    title="ColorPix",
    description="DST MLops Image Colorization Project",
    version="0.1"
)
app.mount("/static", StaticFiles(directory="static"), name="static")

# PostgreSQL Database session function
def get_db():
    db = pixlibs.database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Declare Endpoints
# Authentication endpoints
app.include_router(pixlibs.auth.router)

# endpoints dependency
db_dependency = Annotated[Session, Depends(get_db)] # database access is ok
user_dependency = Annotated[dict, Depends(get_current_user)] # user authentication is ok
storage_dependency = Annotated[storageclient, Depends(get_storage)] # storage access is ok

# DB default user creation function
bcrypt_context = CryptContext(schemes=['bcrypt'],deprecated='auto')
def create_default_user():
    db = pixlibs.database.SessionLocal()
    #result = db.query(pixlibs.models.Users).filter_by(pixlibs.models.Users.username == "default")
    # declare new object "Users"
    create_user_model = pixlibs.models.Users(
        username="default",
        firstname="Default",
        lastname="USER",
        hashed_password=bcrypt_context.hash("default"),
        )
    # SQL ADD request
    try:
        db.add(create_user_model)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(format_logger("api","Default user creation failed.",repr(e)), exc_info=True)

# Init default user
create_default_user()

# root endpoint
@app.get('/')
def root():
    """
    Description
    -----------
    Endpoint : Show message : Welcome to ColorPix !

    Returns
    -------
    string : json message with "Welcome to ColorPix !"
    """
    # log
    logger.info(f"request / endpoint!") 
    return {'message': "Welcome to ColorPix !"}

# favicon endpoint
@app.get('/favicon.ico')
async def favicon():
     # log
    logger.info(f"request /favicon.ico endpoint!")  

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
    user: oauth2 token required,
    db: postgres connexion required,
    file: black & white image (jpeg)

    Returns
    -------
    string: file url --> black & white image uploaded on s3 bucket url 
    """

    # check authentication 
    if user is None:
        logger.exception('Authentication Failed')
        raise HTTPException(status_code=401, detail='Authentication Failed')

    # log
    logger.info(format_logger(user["id"],"","Request /upload_bw_image endpoint!")) 

    # upload file to localhost
    if not file:
        logger.exception(format_logger(user["id"],"","No file found."))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='No file found.')
    if file.content_type != "image/jpeg":
        logger.exception(format_logger(user["id"],"","Bad file format (jpeg only)."))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Bad file format (jpeg only).')
    tempfilename = tempfile.NamedTemporaryFile()
    try:
        contents = file.file.read()
        with open(f"cache{tempfilename.name}", 'wb') as f:
            f.write(contents)
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to save file {tempfilename.name} on server.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Upload to server error.')
    finally:
        file.file.close()

    # check if picture is greyscale & well sized
    if not is_valid_image(f"cache{tempfilename.name}"):
        if os.path.exists(f"cache{tempfilename.name}"):
            # if not ok then delete temporary file
            os.remove(f"cache{tempfilename.name}")
        logger.error(format_logger(user["id"],"",f"Bad file format (only b&w image, {IMG_SIZE_W_MIN}x{IMG_SIZE_H_MIN} min,{IMG_SIZE_W_MAX}x{IMG_SIZE_H_MAX} max)."))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Bad file format (only b&w image, {IMG_SIZE_W_MIN}x{IMG_SIZE_H_MIN} min,{IMG_SIZE_W_MAX}x{IMG_SIZE_H_MAX} max).")       
    
    # set new filename (bw_userid_yyyymmdd-hhmmss.jpg)
    s3filename = f"bw_{user['id']}_{time.strftime("%Y%m%d-%H-%M-%S")}.jpg"
    
    # write file to bucket
    try:
        #s3client.fput_object(AWS_BUCKET_MEDIA,s3filename,f"cache{tempfilename.name}","image/jpg")
        s3client.Bucket(AWS_BUCKET_MEDIA,).upload_file(f"cache{tempfilename.name}",f"bw_images/{s3filename}")
        if os.path.exists(f"cache{tempfilename.name}"):
            # if file writed then delete temporary file
            os.remove(f"cache{tempfilename.name}")
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to save file {tempfilename.name} on Bucket.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Upload to bucket error.')   

    # add bw image ref to database
    try:
        create_bw_image_model = pixlibs.models.BW_Images(
        filename=f"bw_images/{s3filename}",
        user_id=user['id'],
        )
        db.add(create_bw_image_model)
        db.commit()
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to add bw_images/{s3filename} on Database.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Database write error.')

    # return      
    return {"url": f"{AWS_ENDPOINT_URL}/{AWS_BUCKET_MEDIA}/bw_images/{s3filename}"}

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

# bw image colorization
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
     string: file url --> colorized image added on s3 bucket 
    """

    # check authentication 
    if user is None:
        logger.exception('Authentication Failed')
        raise HTTPException(status_code=401, detail='Authentication Failed')
    # log
    logger.info(format_logger(user["id"],"","Request /colorize_bw_image endpoint!"))
    
    # check last uploaded file (or none)
    try:
        lastimageobj = db.query(pixlibs.models.BW_Images).filter(pixlibs.models.BW_Images.user_id == user["id"]).order_by(pixlibs.models.BW_Images.filename.desc()).first() is not None
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to read last image uploaded on Database.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Database read error.')        

    # copy bw image from bucket to server
    tempbwfilename = tempfile.NamedTemporaryFile()
    try:
        s3client.Bucket(AWS_BUCKET_MEDIA,).download_file(lastimageobj.filename,f"cache{tempbwfilename.name}.jpg")
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to download last bw image uploaded on Database.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='File write error on server (s3->server).')

    # image colorization
    try:
        grayscale_image = cv2.imread(f"cache{tempbwfilename.name}.jpg", cv2.IMREAD_GRAYSCALE)
        rgb_image = cv2.cvtColor(grayscale_image, cv2.COLOR_GRAY2RGB)
        cv2.fillPoly(rgb_image, [np.array([[170,50],[240, 40],[240, 150], [210, 100], [130, 130]], np.int32)], (255,150,255))
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to colorize bw image {lastimageobj.filename} on Database.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Image read error or colorize error on server.')      

    # write colorized image to server
    tempcolorfilename = tempfile.NamedTemporaryFile()
    try:
        cv2.imwrite(f"cache{tempcolorfilename.name}.jpg", rgb_image)
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to save colorized bw image {lastimageobj.filename} on server.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='File write error on server (server).')

     # write colorized image from server to bucket
    s3colorfilename = f"color_{lastimageobj.user_id}_{lastimageobj.id}_{time.strftime("%Y%m%d-%H-%M-%S")}.jpg"

    try:
        s3client.Bucket(AWS_BUCKET_MEDIA,).upload_file(f"cache{tempcolorfilename.name}.jpg",f"color_images/{s3colorfilename}")
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to save colorized bw image {lastimageobj.filename} on Bucket.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='File write error on server (server->s3).')

    # delete temporary files
    try:
        if os.path.exists(f"cache{tempbwfilename.name}.jpg"):
            # if file writed then delete temporary file
            os.remove(f"cache{tempbwfilename.name}.jpg")
        if os.path.exists(f"cache{tempcolorfilename.name}.jpg"):
            # if file writed then delete temporary file
            os.remove(f"cache{tempcolorfilename.name}.jpg")
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to delete temporary file cache{tempbwfilename.name}.jpg on server.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Delete file error on server.')             

    # add colororized image ref to database
    try:
        create_color_image_model = pixlibs.models.COLOR_Images(
        filename=f"color_images/{s3colorfilename}",
        user_id=user['id'],
        bwimage_id=lastimageobj.id
        )
        db.add(create_color_image_model)
        db.commit()
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to add color_images/{s3colorfilename} on Database.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Database write error.')        

    # return image
    return {"url": f"{AWS_ENDPOINT_URL}/{AWS_BUCKET_MEDIA}/bw_images/{s3colorfilename}"}

# download colorized image
@app.get('/download_colorized_image')
async def download_colorized_image(user: user_dependency, db: db_dependency, s3client: storage_dependency, bg_tasks: BackgroundTasks):
    """
    Description
    -----------
    endpoint to download last colorized image

    Parameters
    ----------
    user: oauth2 token required
    db: postgres connexion required

    Returns
    -------
     file: colorized image (jpeg)
    """

   # check authentication 
    if user is None:
        logger.exception('Authentication Failed')
        raise HTTPException(status_code=401, detail='Authentication Failed')
    # log
    logger.info(format_logger(user["id"],"","Request /download_colorized_image endpoint!"))
    
    # check last uploaded file (or none)
    try:
        lastimageobj = db.query(pixlibs.models.COLOR_Images).filter(pixlibs.models.COLOR_Images.user_id == user["id"]).order_by(pixlibs.models.COLOR_Images.filename.desc()).first() is not None
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to read last color image added on Database.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Database read error.')  
    
     # copy color image from bucket to server
    tempcolorfilename = tempfile.NamedTemporaryFile()
    try:
        s3client.Bucket(AWS_BUCKET_MEDIA,).download_file(lastimageobj.filename,f"cache{tempcolorfilename.name}.jpg")
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to download last color image added on Database.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='File write error on server (s3->server).')
    
    # delete temporary files
    try:
        if os.path.exists(f"cache{tempcolorfilename.name}.jpg"):
            # if file writed then add background task to delete temporary file after FileResponse return
            bg_tasks.add_task(os.remove, f"cache{tempcolorfilename.name}.jpg")
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to delete temporary file cache{tempcolorfilename.name}.jpg on server.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Delete file error on server.')     

    # return image
    return FileResponse(f"cache{tempcolorfilename.name}.jpg", media_type="image/jpeg", filename=lastimageobj.filename,background=bg_tasks)     

# delete user
@app.post('/delete_user')
async def delete_user(user: user_dependency, username: str,db: db_dependency, s3client: storage_dependency):
    """
    Description
    -----------
    endpoint to delete user (himself or with admin account)

    Parameters
    ----------
    user: oauth2 token required
    db: postgres connexion required

    Returns
    -------
    string : json message with "User + Data deleted succesfully !"
    """

    # check authentication 
    if user is None:
        logger.exception('Authentication Failed')
        raise HTTPException(status_code=401, detail='Authentication Failed')
    # log
    logger.info(format_logger(user["id"],"","Request /delete_user!"))

    # check if username = user authentified or if user is admin , get user id
    if user["username"]!=username:
        operator_user = db.query(pixlibs.models.Users).filter(pixlibs.models.Users.id == user["id"]).first()
        if not operator_user.isadmin:
            logger.exception('You are not authorized to delete user.')
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='You are not authorized to delete user.')
        else:
            try:
                userid = db.query(pixlibs.models.Users).filter(pixlibs.models.Users.username == username).first().id
            except Exception as e:
                logger.error(format_logger(user["id"],f"failed to find user {username} in database.",repr(e)), exc_info=True)
                raise HTTPException(status_code=500, detail='Unable to find user {username} in database.')     
    else:
        userid = user["id"]

    # delete users's bw images
    try:
        bw_images = db.query(pixlibs.models.BW_Images).filter(pixlibs.models.BW_Images.user_id == userid)
        if bw_images.count()>0:
            for image in bw_images:
                try:
                    s3client.Bucket(AWS_BUCKET_MEDIA,).delete_key(image.name)
                except Exception as e:
                    logger.error(format_logger(user["id"],f"failed to delete {image.name} on bucket.",repr(e)), exc_info=True)
                    raise HTTPException(status_code=500, detail='File delete error on bucket.')
                print(image.filename)
            db.delete(bw_images)
            db.commit()
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to read bw_images on Database.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Database read error.')        
    
    # delete users's color images
    try:
        color_images = db.query(pixlibs.models.COLOR_Images).filter(pixlibs.models.COLOR_Images.user_id == userid)
        if color_images.count()>0:
            for image in color_images:
                try:
                    s3client.Bucket(AWS_BUCKET_MEDIA,).delete_key(image.name)
                except Exception as e:
                    logger.error(format_logger(user["id"],f"failed to delete {image.name} on bucket.",repr(e)), exc_info=True)
                    raise HTTPException(status_code=500, detail='File delete error on bucket.')
            db.delete(color_images)
            db.commit()
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to read color_images on Database.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Database read error.')     

    # delete user
    try:
        usertodelete = db.query(pixlibs.models.Users).filter(pixlibs.models.Users.id == userid).first()
        db.delete(usertodelete)
        db.commit()
    except Exception as e:
        logger.error(format_logger(user["id"],f"failed to delete user({username}) on Database.",repr(e)), exc_info=True)
        raise HTTPException(status_code=500, detail='Database delete error.')    

    # return
    return {'message': f"User({username}) + Data deleted succesfully !"}