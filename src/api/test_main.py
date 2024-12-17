# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# Unit Tests

from fastapi.testclient import TestClient
import pytest
import os
from dotenv import load_dotenv
from main import app

# Load .env environment variables
load_dotenv()
IMG_SIZE_H_MIN = os.getenv("IMG_SIZE_H_MIN")
IMG_SIZE_W_MIN = os.getenv("IMG_SIZE_W_MIN")
IMG_SIZE_H_MAX = os.getenv("IMG_SIZE_H_MAX")
IMG_SIZE_W_MAX = os.getenv("IMG_SIZE_W_MAX")
IMG_SIZE_KB_MAX = os.getenv("IMG_SIZE_KB_MAX")

# Declare unit tests client
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# authentification valide
@pytest.fixture(scope="module")
def test_user():
    return {"username": "unittestuser", "password": "testpassword"}

# authentification invalide
@pytest.fixture(scope="module")
def test_user_with_bad_password():
    return {"username": "unittestuser", "password": "badpassword"}

# root endpoint test
def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        'message': "Welcome to ColorPix !",
    }

# create_user endpoint test
def test_create_user(client):
    response = client.post("/auth/create_user",json={"username":"unittestuser",
                                                "firstname":"Test",
                                                "lastname":"UNIT",
                                                "password":"testpassword"})
    assert response.status_code == 201
    assert response.json() == {
        'message': f"User unittestuser created !",
    } 

# authenticate test (bad password & no token)
def test_auth_token(client, test_user_with_bad_password):
    response = client.post("/auth/token",data=test_user_with_bad_password)                                           
    assert response.status_code == 401

# authenticate test (get token)
def test_auth_token(client, test_user):
    response = client.post("/auth/token",data=test_user)                                           
    assert response.status_code == 200
    token =response.json()["access_token"]
    assert token is not None
    return token

# upload valid bw image test
def test_upload_bw_image(client, test_user):
    token = test_auth_token(client, test_user)
    file_path = "test/test_main_valid_bw_image.jpg"
    assert os.path.isfile(file_path), f"Test file {file_path} does not exist."
    with open(file_path, "rb") as f:
        response = client.post(
            "/upload_bw_image",
            headers={"Authorization": f"Bearer {token}"},        
            files={"file": f},
        )
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    response_json = response.json()
    assert "url" in response_json, "Response JSON does not contain 'url'."
    assert isinstance(response_json["url"], str), "'url' is not a string."

# upload unvalid bw image test (color image)
def test_upload_color_image(client, test_user):
    token = test_auth_token(client, test_user)
    file_path = "test/test_main_unvalid_bw_image_1.jpg"
    assert os.path.isfile(file_path), f"Test file {file_path} does not exist."
    with open(file_path, "rb") as f:
        response = client.post(
            "/upload_bw_image",
            headers={"Authorization": f"Bearer {token}"},        
            files={"file": f},
        )
    assert response.status_code == 400, f"Unexpected status code: {response.status_code}"
    assert response.json() == {"detail": f"Bad file format (only b&w image, {IMG_SIZE_W_MIN}x{IMG_SIZE_H_MIN} min,{IMG_SIZE_W_MAX}x{IMG_SIZE_H_MAX} max)."} 

# upload unvalid bw image test (bad sized image)
def test_upload_small_image(client, test_user):
    token = test_auth_token(client, test_user)
    file_path = "test/test_main_unvalid_bw_image_2.jpg"
    assert os.path.isfile(file_path), f"Test file {file_path} does not exist."
    with open(file_path, "rb") as f:
        response = client.post(
            "/upload_bw_image",
            headers={"Authorization": f"Bearer {token}"},        
            files={"file": f},
        )
    assert response.status_code == 400, f"Unexpected status code: {response.status_code}"
    assert response.json() == {"detail": f"Bad file format (only b&w image, {IMG_SIZE_W_MIN}x{IMG_SIZE_H_MIN} min,{IMG_SIZE_W_MAX}x{IMG_SIZE_H_MAX} max)."} 

# upload unvalid bw image test (bad image format)
def test_upload_small_image(client, test_user):
    token = test_auth_token(client, test_user)
    file_path = "test/test_main_unvalid_bw_image_3.png"
    assert os.path.isfile(file_path), f"Test file {file_path} does not exist."
    with open(file_path, "rb") as f:
        response = client.post(
            "/upload_bw_image",
            headers={"Authorization": f"Bearer {token}"},        
            files={"file": f},
        )
    assert response.status_code == 400, f"Unexpected status code: {response.status_code}"
    assert response.json() == {"detail": "Bad file format (jpeg only)."} 

# colorize image test
def test_colorize_bw_image(client, test_user):
    token = test_auth_token(client, test_user)
    response = client.get("/colorize_bw_image", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    response_json = response.json()
    assert "url" in response_json, "Response JSON does not contain 'url'."
    assert isinstance(response_json["url"], str), "'url' is not a string."

# get colorized images list test + download one image test + rate one image test
def test_colorized_images_list(client, test_user):
    token = test_auth_token(client, test_user)
    response = client.get("/get_colorized_images_list", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    response2 = client.get(f"/download_colorized_image/{list(response.json().keys())[0]}", headers={"Authorization": f"Bearer {token}"})
    assert response2.status_code == 200
    response3 = client.post(f"/rate_colorized_image/{list(response.json().keys())[0]}?rating=10",headers={"Authorization": f"Bearer {token}"})
    assert response3.status_code == 200
    assert response3.json() == {'message': "Your colorized image has been successfully rated !"} 

# download last colorized image test
def test_download_last_colorized_image(client,test_user):
    token = test_auth_token(client, test_user)
    response = client.get("/download_last_colorized_image", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

# delete_user endpoint test
def test_delete_user(client, test_user):
    token = test_auth_token(client, test_user)
    response = client.post("/delete_user?username=unittestuser", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {'message': "User(unittestuser) + Data deleted successfully !"} 
