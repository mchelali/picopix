# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# S3 Storage connexion

import boto3
from dotenv import load_dotenv
import os

# Load .env environment variables
load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")
AWS_BUCKET_MEDIA = os.getenv("AWS_BUCKET_MEDIA")

storageclient = boto3.resource(service_name="s3",
    endpoint_url= f'HTTP://{AWS_ENDPOINT_URL}' ,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=None,
    config=boto3.session.Config(signature_version='s3v4'),
    region_name=AWS_REGION_NAME,
    verify=False)

def get_storage():
    bucket = storageclient.Bucket(AWS_BUCKET_MEDIA)

    if bucket.creation_date:
        return storageclient
    else:
        print(f"S3 Bucket {AWS_BUCKET_MEDIA} does not exist.")
        return None    
