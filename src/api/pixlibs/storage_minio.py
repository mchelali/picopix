# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# S3 Storage connexion

from minio import Minio
from dotenv import load_dotenv
import os

# Load .env environment variables
load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")
AWS_BUCKET_MEDIA = os.getenv("AWS_BUCKET_MEDIA")

storageclient = Minio(
    endpoint=AWS_ENDPOINT_URL,
    access_key=AWS_ACCESS_KEY_ID,
    secret_key=AWS_SECRET_ACCESS_KEY,
    secure=False,
)


def get_storage():
    if storageclient.bucket_exists(AWS_BUCKET_MEDIA):
        return storageclient
    else:
        print(f"S3 Bucket {AWS_BUCKET_MEDIA} does not exist.")
        return None
