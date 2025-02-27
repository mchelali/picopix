# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# API

# Declare libraries
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import and_
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
import botocore

from pixlibs.database import engine
import pixlibs.storage_boto3
import pixlibs.auth
from pixlibs.schemas_api import Imagerating, FavModel
from passlib.context import CryptContext
from pixlibs.auth import get_current_user
from pixlibs.storage_boto3 import get_storage, storageclient
from pixlibs.inference import (
    infer_autoencoder,
    infer_pix2pix,
    models_list,
    get_presigned_url,
)

# Load .env environment variables
load_dotenv()
IMG_SIZE_H_MIN = os.getenv("IMG_SIZE_H_MIN")
IMG_SIZE_W_MIN = os.getenv("IMG_SIZE_W_MIN")
IMG_SIZE_H_MAX = os.getenv("IMG_SIZE_H_MAX")
IMG_SIZE_W_MAX = os.getenv("IMG_SIZE_W_MAX")
IMG_SIZE_KB_MAX = os.getenv("IMG_SIZE_KB_MAX")
AWS_BUCKET_MEDIA = os.getenv("AWS_BUCKET_MEDIA")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")
PICOPIX_ADM = os.getenv("PICOPIX_ADM")
PICOPIX_ADM_FIRSTNAME = os.getenv("PICOPIX_ADM_FIRSTNAME")
PICOPIX_ADM_LASTNAME = os.getenv("PICOPIX_ADM_LASTNAME")
PICOPIX_ADM_PWD = os.getenv("PICOPIX_ADM_PWD")

# Enable logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="main.log",
    filemode="w",
    encoding="utf-8",
    level=logging.ERROR,
    format="%(asctime)s %(levelname)s %(message)s",
)


def format_logger(user: int, error: str, message: str):
    if len(error) == 0:
        return f"User: {user}\tMessage: {message}"
    else:
        return f"User: {user}\tError:{error}\tMessage: {message}"


# Startup sequence
@asynccontextmanager
async def lifespan(application: FastAPI):
    # create temporary folders
    os.makedirs("cache/tmp", exist_ok=True)
    # create database structure
    pixlibs.models.Base.metadata.create_all(bind=engine)
    create_default_user()
    update_db_models()
    yield


# Declare API
app = FastAPI(
    title="ColorPix",
    description="DST MLops Image Colorization Project",
    version="0.1",
    lifespan=lifespan,
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
db_dependency = Annotated[Session, Depends(get_db)]  # database access is ok
user_dependency = Annotated[
    dict, Depends(get_current_user)
]  # user authentication is ok
storage_dependency = Annotated[
    storageclient, Depends(get_storage)
]  # storage access is ok

bucket_name = "picopix"
try:
    # Vérifie si le bucket existe
    storage_dependency.meta.client.head_bucket(Bucket=bucket_name)
    print(f"Bucket '{bucket_name}' already exists.")
except botocore.exceptions.ClientError as e:
    # Si le bucket n'existe pas, créez-le
    if e.response["Error"]["Code"] == "404":
        try:
            storage_dependency.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' created successfully.")
        except Exception as creation_error:
            print(f"Error creating bucket '{bucket_name}': {creation_error}")
    else:
        print(f"Error accessing bucket '{bucket_name}': {e}")

# DB default user creation function
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_default_user():
    db = pixlibs.database.SessionLocal()
    # result = db.query(pixlibs.models.Users).filter_by(pixlibs.models.Users.username == "default")
    # declare new object "Users"
    create_user_model = pixlibs.models.Users(
        username=PICOPIX_ADM,
        firstname=PICOPIX_ADM_FIRSTNAME,
        lastname=PICOPIX_ADM_LASTNAME,
        isadmin=True,
        hashed_password=bcrypt_context.hash(PICOPIX_ADM_PWD),
    )
    # SQL ADD request
    try:
        defaultuser = (
            db.query(pixlibs.models.Users)
            .filter(pixlibs.models.Users.username == "default")
            .first()
            or None
        )
        if defaultuser is None:
            db.add(create_user_model)
            db.commit()
            db.close()
    except Exception as e:
        logger.error(
            format_logger("api", "Default user creation failed.", repr(e)),
            exc_info=True,
        )


def update_db_models():
    db = pixlibs.database.SessionLocal()
    for mdl in models_list:
        try:
            mdlex = (
                db.query(pixlibs.models.MODELS)
                .filter(pixlibs.models.MODELS.filename == mdl)
                .first()
                or None
            )
            if mdlex is None:
                newmodel = pixlibs.models.MODELS(filename=mdl)
                db.add(newmodel)
                db.commit()
        except Exception as e:
            logger.error(
                format_logger("api", f"Model {mdl} database add failure.", repr(e)),
                exc_info=True,
            )
    db.close


# root endpoint
@app.get("/")
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
    return {"message": "Welcome to ColorPix !"}


# favicon endpoint
@app.get("/favicon.ico")
async def favicon():
    # log
    logger.info(f"request /favicon.ico endpoint!")

    file_name = "favicon.ico"
    file_path = os.path.join(app.root_path, "static", file_name)
    return FileResponse(
        path=file_path,
        headers={"Content-Disposition": "attachment; filename=" + file_name},
    )


# get user informations
@app.get("/get_user_informations")
async def get_user_informations(user: user_dependency, db: db_dependency):
    """
    Description
    -----------
    endpoint to get list of user's informations

    Parameters
    ----------
    user: oauth2 token required
    db: postgres connexion required

    Returns
    -------
    string: list of data(json)
    """

    # check authentication
    if user is None:
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(
        format_logger(user["id"], "", "Request /get_colorized_images_list endpoint!")
    )

    # contruct dictionnary
    try:
        userdata = (
            db.query(pixlibs.models.Users)
            .filter(pixlibs.models.Users.id == user["id"])
            .first()
        )
        user_informations = {
            "firstname": userdata.firstname,
            "lastname": userdata.lastname,
            "favorite_model": userdata.pref_model,
            "isadmin": userdata.isadmin,
        }
    except Exception as e:
        logger.error(
            format_logger(
                user["id"], f"failed to read color images on Database.", repr(e)
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Database read error.")
    return user_informations


# set favorite model
@app.post("/set_favorite_model")
async def set_favorite_model(
    user: user_dependency, db: db_dependency, favorite_model: FavModel
):
    """
    Description
    -----------
    endpoint to set user's favorite model

    Parameters
    ----------
    user: oauth2 token required
    db: postgres connexion required

    Returns
    -------
    string: json message
    """
    # check authentication
    if user is None:
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(
        format_logger(user["id"], "", "Request /get_colorized_images_list endpoint!")
    )

    #
    if favorite_model is not None:
        if (int(favorite_model.mdl) >= 0) and (int(favorite_model.mdl) <= 2):
            try:
                user = (
                    db.query(pixlibs.models.Users)
                    .filter(pixlibs.models.Users.id == user["id"])
                    .first()
                )
                user.pref_model = int(favorite_model.mdl)
                db.commit()
            except Exception as e:
                logger.error(
                    format_logger(
                        user["id"],
                        f"failed to set favorite model on Database.",
                        repr(e),
                    ),
                    exc_info=True,
                )
                raise HTTPException(status_code=500, detail="Database write error.")
            # return
            if int(favorite_model.mdl) == 0:
                return {"message": f"You don't have favorite model!"}
            elif int(favorite_model.mdl) == 1:
                return {"message": f"Your favorite model is autoencoder !"}
            elif int(favorite_model.mdl) == 2:
                return {"message": f"Your favorite model is pix2pix !"}
        else:
            logger.exception(format_logger(user["id"], "", "Bads arguments."))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Bad arguments."
            )
    else:
        logger.exception(format_logger(user["id"], "", "Bads arguments."))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Bad arguments."
        )


# get users list
@app.get("/get_users_list")
async def get_users_list(user: user_dependency, db: db_dependency):
    """
    Description
    -----------
    endpoint to get users list
    Parameters
    ----------
    user: oauth2 token required
    db: postgres connexion required
    Returns
    -------
    string: users list (json)
    """

    # Check authentication
    if user is None:
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(format_logger(user["id"], "", "Request /disable_user!"))

    # check if username = user authentified or if user is admin
    operator_user = (
        db.query(pixlibs.models.Users)
        .filter(pixlibs.models.Users.id == user["id"])
        .first()
    )
    if not operator_user.isadmin:
        logger.exception("You are not authorized to get users list.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to get users list.",
        )
    else:
        try:
            users = db.query(pixlibs.models.Users).all()
            users_list = dict()
            user_fields = dict()
            for usera in users:
                user_fields = {
                    "firstname": usera.firstname,
                    "lastname": usera.lastname,
                    "isadmin": usera.isadmin,
                    "disabled": usera.disabled,
                }
                users_list[usera.username] = user_fields
        except Exception as e:
            logger.error(
                format_logger(
                    user["id"], f"failed to list users in database.", repr(e)
                ),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail=f"failed to list users in database."
            )
        # return
        return users_list


# disable user
@app.post("/disable_user")
async def disable_user(user: user_dependency, db: db_dependency, username: str):
    """
    Description
    -----------
    endpoint to set favorite model
    Parameters
    ----------
    user: oauth2 token required
    db: postgres connexion required
    Returns
    -------
    string: json message
    """
    # Check authentication
    if user is None:
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(format_logger(user["id"], "", "Request /disable_user!"))

    # check if username = user authentified or if user is admin , get user id
    if user["username"] == username:
        logger.error(
            format_logger(user["id"], "Disable your own account is prohibited.", ""),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Disable your own account is prohibited."
        )
    else:
        operator_user = (
            db.query(pixlibs.models.Users)
            .filter(pixlibs.models.Users.id == user["id"])
            .first()
        )
        if not operator_user.isadmin:
            logger.exception("You are not authorized to disable user.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to disable user.",
            )
        else:
            try:
                usertodisable = (
                    db.query(pixlibs.models.Users)
                    .filter(pixlibs.models.Users.username == username)
                    .first()
                )
                if usertodisable is not None:
                    usertodisable.disabled = True
                    db.commit()
                else:
                    logger.error(
                        format_logger(
                            user["id"],
                            f"failed to find user {username} in database.",
                            repr(e),
                        ),
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"failed to find user {username} in database.",
                    )
            except Exception as e:
                logger.error(
                    format_logger(
                        user["id"],
                        f"failed to disable user {username} in database.",
                        repr(e),
                    ),
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"failed to disable user {username} in database.",
                )
            # return
            return {"message": f"User({username}) is disable !"}


# enable user
@app.post("/enable_user")
async def disable_user(user: user_dependency, db: db_dependency, username: str):
    """
    Description
    -----------
    endpoint to set favorite model
    Parameters
    ----------
    user: oauth2 token required
    db: postgres connexion required
    Returns
    -------
    string: json message
    """
    # Check authentication
    if user is None:
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(format_logger(user["id"], "", "Request /disable_user!"))

    # check if username = user authentified or if user is admin , get user id
    if user["username"] == username:
        logger.error(
            format_logger(user["id"], "Enable your own account is prohibited.", ""),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Enable your own account is prohibited."
        )
    else:
        operator_user = (
            db.query(pixlibs.models.Users)
            .filter(pixlibs.models.Users.id == user["id"])
            .first()
        )
        if not operator_user.isadmin:
            logger.exception("You are not authorized to enable user.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to enable user.",
            )
        else:
            try:
                usertoenable = (
                    db.query(pixlibs.models.Users)
                    .filter(pixlibs.models.Users.username == username)
                    .first()
                )
                if usertoenable is not None:
                    usertoenable.disabled = False
                    db.commit()
                else:
                    logger.error(
                        format_logger(
                            user["id"],
                            f"failed to find user {username} in database.",
                            repr(e),
                        ),
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"failed to find user {username} in database.",
                    )
            except Exception as e:
                logger.error(
                    format_logger(
                        user["id"],
                        f"failed to enable user {username} in database.",
                        repr(e),
                    ),
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"failed to enable user {username} in database.",
                )
            # return
            return {"message": f"User({username}) is enable !"}


# enable user
@app.post("/set_admin_access")
async def set_admin_access(user: user_dependency, db: db_dependency, username: str):
    """
    Description
    -----------
    endpoint to set admin access
    ----------
    user: oauth2 token required
    db: postgres connexion required
    Returns
    -------
    string: json message
    """
    # Check authentication
    if user is None:
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(format_logger(user["id"], "", "Request /disable_user!"))

    # check if username = user authentified or if user is admin , get user id
    if user["username"] == username:
        logger.error(
            format_logger(user["id"], "Enable your own account is prohibited.", ""),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Enable your own account is prohibited."
        )
    else:
        operator_user = (
            db.query(pixlibs.models.Users)
            .filter(pixlibs.models.Users.id == user["id"])
            .first()
        )
        if not operator_user.isadmin:
            logger.exception("You are not authorized to set/unset admin user.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to set/unset admin user.",
            )
        else:
            try:
                usertochange = (
                    db.query(pixlibs.models.Users)
                    .filter(pixlibs.models.Users.username == username)
                    .first()
                )
                if usertochange is not None:
                    usertochange.isadmin = not usertochange.isadmin
                    db.commit()
                else:
                    logger.error(
                        format_logger(
                            user["id"],
                            f"failed to find user {username} in database.",
                            repr(e),
                        ),
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"failed to find user {username} in database.",
                    )
            except Exception as e:
                logger.error(
                    format_logger(
                        user["id"],
                        f"failed to enable user {username} in database.",
                        repr(e),
                    ),
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"failed to enable user {username} in database.",
                )
            # return
            if usertochange.isadmin == True:
                return {"message": f"Admin access is enabled for {username}!"}
            if usertochange.isadmin == False:
                return {"message": f"Admin access is disabled for {username}!"}


# black & white image upload
@app.post("/upload_bw_image")
async def upload_bw_image(
    user: user_dependency,
    db: db_dependency,
    s3client: storage_dependency,
    file: UploadFile = File(...),
):
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
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")

    # log
    logger.info(format_logger(user["id"], "", "Request /upload_bw_image endpoint!"))

    # upload file to localhost
    if not file:
        logger.exception(format_logger(user["id"], "", "No file found."))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No file found."
        )
    if file.content_type != "image/jpeg":
        logger.exception(format_logger(user["id"], "", "Bad file format (jpeg only)."))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad file format (jpeg only).",
        )
    tempfilename = tempfile.NamedTemporaryFile()
    try:
        contents = file.file.read()
        with open(f"cache{tempfilename.name}.jpg", "wb") as f:
            f.write(contents)
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to save file {tempfilename.name}.jpg on server.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Upload to server error.")
    finally:
        file.file.close()

    # check if picture is greyscale & well sized
    if not is_valid_image(f"cache{tempfilename.name}.jpg", user["id"]):
        try:
            if os.path.exists(f"cache{tempfilename.name}.jpg"):
                # if not ok then delete temporary file
                os.remove(f"cache{tempfilename.name}.jpg")
        except Exception as e:
            logger.error(
                format_logger(
                    user["id"],
                    f"failed to delete temporary file {tempfilename.name}.jpg on server.",
                    repr(e),
                ),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete temporary  {tempfilename.name}.jpg on server.",
            )
        logger.error(
            format_logger(
                user["id"],
                "",
                f"Bad file format (only b&w image, {IMG_SIZE_W_MIN}x{IMG_SIZE_H_MIN} min,{IMG_SIZE_W_MAX}x{IMG_SIZE_H_MAX} max).",
            )
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bad file format (only b&w image, {IMG_SIZE_W_MIN}x{IMG_SIZE_H_MIN} min,{IMG_SIZE_W_MAX}x{IMG_SIZE_H_MAX} max).",
        )

    # set new filename (bw_userid_yyyymmdd-hhmmss.jpg)
    s3filename = f"bw_{user['id']}_{time.strftime("%Y%m%d-%H-%M-%S")}.jpg"

    # write file to bucket
    try:
        # s3client.fput_object(AWS_BUCKET_MEDIA,s3filename,f"cache{tempfilename.name}","image/jpg")
        s3client.Bucket(
            AWS_BUCKET_MEDIA,
        ).upload_file(f"cache{tempfilename.name}.jpg", f"bw_images/{s3filename}")
        if os.path.exists(f"cache{tempfilename.name}"):
            # if file writed then delete temporary file
            os.remove(f"cache{tempfilename.name}")
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to save file {tempfilename.name}.jpg on Bucket.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Upload to bucket error.")

    # add bw image ref to database
    try:
        create_bw_image_model = pixlibs.models.BW_Images(
            filename=f"bw_images/{s3filename}",
            user_id=user["id"],
        )
        db.add(create_bw_image_model)
        db.commit()
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to add bw_images/{s3filename} on Database.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Database write error.")

    # return
    return {"url": f"{AWS_ENDPOINT_URL}/{AWS_BUCKET_MEDIA}/bw_images/{s3filename}"}


# Image validity function
def is_valid_image(imgfilename: str, userid: int):
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
        if (os.path.getsize(imgfilename) / 1024) > int(IMG_SIZE_KB_MAX):
            print("Bad image size in kb")
            return False

        # open image
        img = cv2.imread(imgfilename)
        # split channels
        b, g, r = cv2.split(img)
        # check if image is greyscale
        r_g = np.count_nonzero(abs(r - g))
        r_b = np.count_nonzero(abs(r - b))
        g_b = np.count_nonzero(abs(g - b))
        diff_sum = float(r_g + r_b + g_b)
        ratio = diff_sum / img.size
        if ratio > 0.005:
            print("not bw image")
            return False
        # check height and width
        h, w, c = img.shape
        if w < int(IMG_SIZE_W_MIN) or h < int(IMG_SIZE_H_MIN):
            print("bad min size image")
            return False
        if w > int(IMG_SIZE_W_MAX) or h > int(IMG_SIZE_H_MAX):
            print("bad max size image")
            return False
    except Exception as e:
        logger.error(
            format_logger(
                userid,
                f"failed to check image validity imgfilename on Server.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="File read error.")

    # return
    return True


# bw image colorization
@app.get("/colorize_bw_image")
async def colorize_bw_image(
    user: user_dependency,
    db: db_dependency,
    s3client: storage_dependency,
    bg_tasks: BackgroundTasks,
):
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
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(format_logger(user["id"], "", "Request /colorize_bw_image endpoint!"))

    # check last uploaded file (or none)
    try:
        lastimageobj = (
            db.query(pixlibs.models.BW_Images)
            .filter(pixlibs.models.BW_Images.user_id == user["id"])
            .order_by(pixlibs.models.BW_Images.filename.desc())
            .first()
        )
    except Exception as e:
        logger.error(
            format_logger(
                user["id"], f"failed to read last image uploaded on Database.", repr(e)
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Database read error.")

    # copy bw image from bucket to server
    tempbwfilename = tempfile.NamedTemporaryFile()
    try:
        s3client.Bucket(
            AWS_BUCKET_MEDIA,
        ).download_file(lastimageobj.filename, f"cache{tempbwfilename.name}.jpg")
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to download last bw image uploaded on Database.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="File write error on server (s3->server)."
        )

    # get user favorite model
    favmodeluser = (
        db.query(pixlibs.models.Users)
        .filter(pixlibs.models.Users.id == user["id"])
        .first()
        .pref_model
    )
    if favmodeluser == 0:
        favmodeluser = 3
    # set value in binary string
    favmodeluser = str(bin(favmodeluser)[2:]).rjust(2, "0")

    # image colorization
    print(models_list)
    try:
        grayscale_image = cv2.imread(
            f"cache{tempbwfilename.name}.jpg", cv2.IMREAD_GRAYSCALE
        )
        if favmodeluser[1:] == "1":
            rgb_image1 = infer_autoencoder(grayscale_image)
        if favmodeluser[:1] == "1":
            rgb_image2 = infer_pix2pix(grayscale_image)
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to colorize bw image {lastimageobj.filename} on Database.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Image read error or colorize error on server."
        )

    # write colorized image to server
    if favmodeluser[1:] == "1":
        tempcolorfilename1 = tempfile.NamedTemporaryFile()
    if favmodeluser[:1] == "1":
        tempcolorfilename2 = tempfile.NamedTemporaryFile()
    try:
        if favmodeluser[1:] == "1":
            cv2.imwrite(f"cache{tempcolorfilename1.name}.jpg", rgb_image1)
        if favmodeluser[:1] == "1":
            cv2.imwrite(f"cache{tempcolorfilename2.name}.jpg", rgb_image2)
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to save colorized bw image {lastimageobj.filename} on server.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="File write error on server (server)."
        )

    # write colorized image from server to bucket
    if favmodeluser[1:] == "1":
        s3colorfilename1 = f"color_{lastimageobj.user_id}_{lastimageobj.id}_autoencoder_{time.strftime("%Y%m%d-%H-%M-%S")}.jpg"
    if favmodeluser[:1] == "1":
        s3colorfilename2 = f"color_{lastimageobj.user_id}_{lastimageobj.id}_pix2pix_{time.strftime("%Y%m%d-%H-%M-%S")}.jpg"

    try:
        if favmodeluser[1:] == "1":
            s3client.Bucket(
                AWS_BUCKET_MEDIA,
            ).upload_file(
                f"cache{tempcolorfilename1.name}.jpg",
                f"color_images/{s3colorfilename1}",
            )
        if favmodeluser[:1] == "1":
            s3client.Bucket(
                AWS_BUCKET_MEDIA,
            ).upload_file(
                f"cache{tempcolorfilename2.name}.jpg",
                f"color_images/{s3colorfilename2}",
            )
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to save colorized bw image {lastimageobj.filename} on Bucket.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="File write error on server (server->s3)."
        )

    # delete temporary files
    try:
        if os.path.exists(f"cache{tempbwfilename.name}.jpg"):
            # if file writed then delete temporary file
            os.remove(f"cache{tempbwfilename.name}.jpg")
        if favmodeluser[1:] == "1" and os.path.exists(
            f"cache{tempcolorfilename1.name}.jpg"
        ):
            # if file writed then delete temporary file
            os.remove(f"cache{tempcolorfilename1.name}.jpg")
        if favmodeluser[:1] == "1" and os.path.exists(
            f"cache{tempcolorfilename2.name}.jpg"
        ):
            # if file writed then delete temporary file
            os.remove(f"cache{tempcolorfilename2.name}.jpg")
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to delete temporary file cache{tempbwfilename.name}.jpg on server.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Delete file error on server.")

    # add colororized image ref to database
    try:
        if favmodeluser[1:] == "1":
            # get model id
            last_autoencoder_model = (
                db.query(pixlibs.models.MODELS)
                .filter(pixlibs.models.MODELS.filename == models_list[0])
                .first()
            )
            # add image
            color_image_autoencoder = pixlibs.models.COLOR_Images(
                filename=f"color_images/{s3colorfilename1}",
                user_id=user["id"],
                bwimage_id=lastimageobj.id,
                model_id=last_autoencoder_model.id,
            )
            db.add(color_image_autoencoder)

        if favmodeluser[:1] == "1":
            # get model id
            last_pix2pix_model = (
                db.query(pixlibs.models.MODELS)
                .filter(pixlibs.models.MODELS.filename == models_list[1])
                .first()
            )
            # add image
            color_image_pix2pix = pixlibs.models.COLOR_Images(
                filename=f"color_images/{s3colorfilename2}",
                user_id=user["id"],
                bwimage_id=lastimageobj.id,
                model_id=last_pix2pix_model.id,
            )
            db.add(color_image_pix2pix)

        db.commit()
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to add color_images/{s3colorfilename1} and {s3colorfilename2} on Database.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Database write error.")

    # return image
    url_autoencoder = ""
    url_pix2pix = ""
    if favmodeluser[1:] == "1":
        url_autoencoder = get_presigned_url(
            s3client, AWS_BUCKET_MEDIA, f"color_images/{s3colorfilename1}"
        )
    if favmodeluser[:1] == "1":
        url_pix2pix = get_presigned_url(
            s3client, AWS_BUCKET_MEDIA, f"color_images/{s3colorfilename2}"
        )
    return {"url1": url_autoencoder, "url2": url_pix2pix}


# get colorized images list
@app.get("/get_colorized_images_list")
async def get_colorized_images_list(
    user: user_dependency, db: db_dependency, s3client: storage_dependency
):
    """
    Description
    -----------
    endpoint to get list of user's colorized images

    Parameters
    ----------
    user: oauth2 token required
    db: postgres connexion required

    Returns
    -------
    string: list of images (json)
    """

    # check authentication
    if user is None:
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(
        format_logger(user["id"], "", "Request /get_colorized_images_list endpoint!")
    )

    # contruct dict of dictionnaries
    try:
        color_images = (
            db.query(pixlibs.models.COLOR_Images)
            .filter(pixlibs.models.COLOR_Images.user_id == user["id"])
            .all()
        )
        images_list = dict()
        imageitem = dict()
        for image in color_images:
            bw_image = (
                db.query(pixlibs.models.BW_Images)
                .filter(pixlibs.models.BW_Images.id == image.bwimage_id)
                .first()
            )
            imagemodel = (
                db.query(pixlibs.models.MODELS)
                .filter(pixlibs.models.MODELS.id == image.model_id)
                .first()
            )
            print(f"{AWS_ENDPOINT_URL}/{AWS_BUCKET_MEDIA}/{bw_image.filename}")
            print(f"{AWS_ENDPOINT_URL}/{AWS_BUCKET_MEDIA}/{image.filename}")
            imageitem = {
                "bw_image_url": get_presigned_url(
                    s3client, AWS_BUCKET_MEDIA, f"{bw_image.filename}"
                ),
                # f"{AWS_ENDPOINT_URL}/{AWS_BUCKET_MEDIA}/{bw_image.filename}",
                "colorized_image_url": get_presigned_url(
                    s3client, AWS_BUCKET_MEDIA, f"{image.filename}"
                ),
                # f"{AWS_ENDPOINT_URL}/{AWS_BUCKET_MEDIA}/{image.filename}",
                "rating": f"{image.rating}",
                "creation_date": f"{image.creation_date}",
                "model": f"{imagemodel.filename}",
            }
            images_list[image.id] = imageitem
    except Exception as e:
        logger.error(
            format_logger(
                user["id"], f"failed to read color images on Database.", repr(e)
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Database read error.")
    return images_list


# rate colorized image
@app.post("/rate_colorized_image/{id}")
async def rate_colorized_image(
    user: user_dependency,
    db: db_dependency,
    id: Annotated[int, Path(title="The ID of the image to rate")],
    rating=Imagerating,
):
    """
    Description
    -----------
    endpoint to rate an colorized image

    Parameters
    ----------
    user: oauth2 token required
    db: postgres connexion required

    Returns
    -------
    boolean: status of rating
    """

    # check authentication
    if user is None:
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(
        format_logger(user["id"], "", "Request /rate_colorized_image endpoint!")
    )

    if (id is not None) and (rating is not None):
        if (int(rating) >= 0) and (int(rating) <= 5):
            color_image = (
                db.query(pixlibs.models.COLOR_Images)
                .filter(
                    and_(
                        pixlibs.models.COLOR_Images.user_id == user["id"],
                        pixlibs.models.COLOR_Images.id == int(id),
                    )
                )
                .first()
                or None
            )
            if color_image is not None:
                try:
                    color_image.rating = rating
                    db.commit()
                except Exception as e:
                    logger.error(
                        format_logger(
                            user["id"],
                            f"failed to rate color image {color_image.filename} on Database.",
                            repr(e),
                        ),
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=500, detail="Database update error."
                    )
            else:
                logger.exception(
                    format_logger(
                        user["id"], "", "Bads arguments (image id does not exist)"
                    )
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bads arguments (image id does not exist)",
                )
        else:
            logger.exception(
                format_logger(
                    user["id"], "", "Bads arguments (rating must between 0 and 5)"
                )
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bads arguments (rating must between 0 and 10)",
            )

    else:
        logger.exception(format_logger(user["id"], "", "Bads arguments."))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Bad arguments."
        )
    return {"message": "Your colorized image has been successfully rated !"}


# download last colorized image
@app.get("/download_last_colorized_image")
async def download_last_colorized_image(
    user: user_dependency,
    db: db_dependency,
    s3client: storage_dependency,
    bg_tasks: BackgroundTasks,
):
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
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(
        format_logger(user["id"], "", "Request /download_colorized_image endpoint!")
    )

    # check last created color image
    try:
        lastimageobj = (
            db.query(pixlibs.models.COLOR_Images)
            .filter(pixlibs.models.COLOR_Images.user_id == user["id"])
            .order_by(pixlibs.models.COLOR_Images.filename.desc())
            .first()
        )
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to read last color image added on Database.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Database read error.")

    # copy color image from bucket to server
    tempcolorfilename = tempfile.NamedTemporaryFile()
    try:
        s3client.Bucket(
            AWS_BUCKET_MEDIA,
        ).download_file(lastimageobj.filename, f"cache{tempcolorfilename.name}.jpg")
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to download last color image added on Database.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="File write error on server (s3->server)."
        )

    # delete temporary files
    try:
        if os.path.exists(f"cache{tempcolorfilename.name}.jpg"):
            # if file writed then add background task to delete temporary file after FileResponse return
            bg_tasks.add_task(os.remove, f"cache{tempcolorfilename.name}.jpg")
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to delete temporary file cache{tempcolorfilename.name}.jpg on server.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Delete file error on server.")

    # return image
    return FileResponse(
        f"cache{tempcolorfilename.name}.jpg",
        media_type="image/jpeg",
        filename=lastimageobj.filename,
        background=bg_tasks,
    )


# download colorized image with id
@app.get("/download_colorized_image/{id}")
async def download_colorized_image(
    user: user_dependency,
    db: db_dependency,
    s3client: storage_dependency,
    id: Annotated[int, Path(title="The ID of the image to download")],
    bg_tasks: BackgroundTasks,
):
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
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(
        format_logger(user["id"], "", "Request /download_colorized_image endpoint!")
    )

    # check color image by id
    try:
        imageobj = (
            db.query(pixlibs.models.COLOR_Images)
            .filter(
                and_(
                    pixlibs.models.COLOR_Images.user_id == user["id"],
                    pixlibs.models.COLOR_Images.id == id,
                )
            )
            .first()
        )
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to read color image {id} added on Database.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Database read error.")

    # copy color image from bucket to server
    tempcolorfilename = tempfile.NamedTemporaryFile()
    try:
        s3client.Bucket(
            AWS_BUCKET_MEDIA,
        ).download_file(imageobj.filename, f"cache{tempcolorfilename.name}.jpg")
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to download last color image added on Database.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="File write error on server (s3->server)."
        )

    # delete temporary files
    try:
        if os.path.exists(f"cache{tempcolorfilename.name}.jpg"):
            # if file writed then add background task to delete temporary file after FileResponse return
            bg_tasks.add_task(os.remove, f"cache{tempcolorfilename.name}.jpg")
    except Exception as e:
        logger.error(
            format_logger(
                user["id"],
                f"failed to delete temporary file cache{tempcolorfilename.name}.jpg on server.",
                repr(e),
            ),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Delete file error on server.")

    # return image
    return FileResponse(
        f"cache{tempcolorfilename.name}.jpg",
        media_type="image/jpeg",
        filename=imageobj.filename,
        background=bg_tasks,
    )


# delete user
@app.post("/delete_user")
async def delete_user(
    user: user_dependency,
    username: str,
    db: db_dependency,
    s3client: storage_dependency,
):
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
        logger.exception("Authentication Failed")
        raise HTTPException(status_code=401, detail="Authentication Failed")
    # log
    logger.info(format_logger(user["id"], "", "Request /delete_user!"))

    # check if username = user authentified or if user is admin , get user id
    if user["username"] != username:
        operator_user = (
            db.query(pixlibs.models.Users)
            .filter(pixlibs.models.Users.id == user["id"])
            .first()
        )
        if not operator_user.isadmin:
            logger.exception("You are not authorized to delete user.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to delete user.",
            )
        else:
            try:
                userid = (
                    db.query(pixlibs.models.Users)
                    .filter(pixlibs.models.Users.username == username)
                    .first()
                    .id
                )
            except Exception as e:
                logger.error(
                    format_logger(
                        user["id"],
                        f"failed to find user {username} in database.",
                        repr(e),
                    ),
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Unable to find user {username} in database.",
                )
    else:
        userid = user["id"]

    # delete users's bw images
    try:
        bw_images = db.query(pixlibs.models.BW_Images).filter(
            pixlibs.models.BW_Images.user_id == userid
        )
        if bw_images.count() > 0:
            for image in bw_images.all():
                try:
                    s3client.Object(AWS_BUCKET_MEDIA, image.filename).delete()
                except Exception as e:
                    logger.error(
                        format_logger(
                            user["id"],
                            f"failed to delete {image.filename} on bucket.",
                            repr(e),
                        ),
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"File delete error : failed to delete {image.filename} on bucket.",
                    )
                try:
                    imagetodelete = (
                        db.query(pixlibs.models.BW_Images)
                        .filter(pixlibs.models.BW_Images.id == image.id)
                        .first()
                    )
                    db.delete(imagetodelete)
                    db.commit()
                except Exception as e:
                    logger.error(
                        format_logger(
                            user["id"],
                            f"failed to delete {image.filename} on database.",
                            repr(e),
                        ),
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"File delete error : failed to delete {image.filename} on database.",
                    )
    except Exception as e:
        logger.error(
            format_logger(
                user["id"], f"failed to read bw_images on Database.", repr(e)
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Database read error : failed to read bw_images on Database.",
        )

    # delete users's color images
    try:
        color_images = db.query(pixlibs.models.COLOR_Images).filter(
            pixlibs.models.COLOR_Images.user_id == userid
        )
        if color_images.count() > 0:
            for image in color_images.all():
                try:
                    s3client.Object(AWS_BUCKET_MEDIA, image.filename).delete()
                except Exception as e:
                    logger.error(
                        format_logger(
                            user["id"],
                            f"failed to delete {image.filename} on bucket.",
                            repr(e),
                        ),
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"File delete error : failed to delete {image.filename} on bucket.",
                    )
                try:
                    imagetodelete = (
                        db.query(pixlibs.models.COLOR_Images)
                        .filter(pixlibs.models.COLOR_Images.id == image.id)
                        .first()
                    )
                    db.delete(imagetodelete)
                    db.commit()
                except Exception as e:
                    logger.error(
                        format_logger(
                            user["id"],
                            f"failed to delete {image.filename} on database.",
                            repr(e),
                        ),
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"File delete error : failed to delete {image.filename} on database.",
                    )
    except Exception as e:
        logger.error(
            format_logger(
                user["id"], f"failed to read color_images on Database.", repr(e)
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Database read error : failed to read color_images on Database.",
        )

    # delete user
    try:
        usertodelete = (
            db.query(pixlibs.models.Users)
            .filter(pixlibs.models.Users.id == userid)
            .first()
        )
        if usertodelete is not None:
            db.delete(usertodelete)
            db.commit()
        else:
            logger.error(
                format_logger(
                    user["id"], f"failed to find user {username} in database.", repr(e)
                ),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail=f"failed to find user {username} in database."
            )
    except Exception as e:
        logger.error(
            format_logger(
                user["id"], f"failed to delete user({username}) on Database.", repr(e)
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Database delete error : failed to delete user({username}) on Database.",
        )

    # return
    return {"message": f"User({username}) + Data deleted successfully !"}
