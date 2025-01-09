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
PICOPIX_ADM = os.getenv("PICOPIX_ADM")
PICOPIX_ADM_PWD = os.getenv("PICOPIX_ADM_PWD")

# Declare unit tests client
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# authentification user valide
@pytest.fixture(scope="module")
def test_user():
    return {"username": "unittestuser", "password": "testpassword"}

# authentification admin valide
@pytest.fixture(scope="module")
def test_admin():
    return {"username": PICOPIX_ADM, "password": PICOPIX_ADM_PWD}

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
    assert response.status_code == 201, f"Unexpected status code: {response.status_code}"
    assert response.json() == {
        'message': f"User unittestuser created !",
    } 

# authenticate test (bad password & no token)
def test_auth_token(client, test_user_with_bad_password):
    response = client.post("/auth/token",data=test_user_with_bad_password)                                           
    assert response.status_code == 401, f"Unexpected status code: {response.status_code}"

# authenticate test (get token)
def test_auth_token(client, test_user):
    response = client.post("/auth/token",data=test_user)                                           
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    token =response.json()["access_token"]
    assert token is not None
    return token

# get user informations test
def test_get_user_informations(client, test_user):
    token = test_auth_token(client, test_user)
    response = client.get("/get_user_informations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    response_json = response.json()
    assert "firstname" in response_json, "Response JSON does not contain 'firstname'."
    assert isinstance(response_json["firstname"], str), "'firstname' is not a string."
    assert "lastname" in response_json, "Response JSON does not contain 'lastname'."
    assert isinstance(response_json["lastname"], str), "'lastname' is not a string."
    assert "favorite_model" in response_json, "Response JSON does not contain 'favorite_model'."
    assert isinstance(response_json["favorite_model"], int), "'favorite_model' is not an integer."
    assert "isadmin" in response_json, "Response JSON does not contain 'isadmin'."
    assert isinstance(response_json["isadmin"], bool), "'isadmin' is not a boolean."
    
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
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    response_json = response.json()
    assert "url1" in response_json, "Response JSON does not contain 'url1'."
    assert isinstance(response_json["url1"], str), "'url' is not a string."
    assert "url2" in response_json, "Response JSON does not contain 'url2'."
    assert isinstance(response_json["url2"], str), "'url' is not a string."


# get colorized images list test + download one image test + rate one image test
def test_colorized_images_list_download_rate_image(client, test_user):
    token = test_auth_token(client, test_user)
    response = client.get("/get_colorized_images_list", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    response2 = client.get(f"/download_colorized_image/{list(response.json().keys())[0]}", headers={"Authorization": f"Bearer {token}"})
    assert response2.status_code == 200, f"Unexpected status code: {response.status_code}"
    response3 = client.post(f"/rate_colorized_image/{list(response.json().keys())[0]}?rating=5",headers={"Authorization": f"Bearer {token}"})
    assert response3.status_code == 200, f"Unexpected status code: {response.status_code}"
    assert response3.json() == {'message': "Your colorized image has been successfully rated !"} 

# download last colorized image test
def test_download_last_colorized_image(client,test_user):
    token = test_auth_token(client, test_user)
    response = client.get("/download_last_colorized_image", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"

# set favorite model endpoint test
def test_set_favorite_model(client, test_user):
    token = test_auth_token(client, test_user)
    response = client.post("/set_favorite_model", headers={"Authorization": f"Bearer {token}"}, json={"mdl":0})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    assert response.json() == {'message': f"You don't have favorite model!"}
    response2 = client.post("/set_favorite_model", headers={"Authorization": f"Bearer {token}"}, json={"mdl":1})
    assert response2.status_code == 200, f"Unexpected status code: {response2.status_code}"
    assert response2.json() == {'message': f"Your favorite model is autoencoder !"}  
    response3 = client.post("/set_favorite_model", headers={"Authorization": f"Bearer {token}"}, json={"mdl":2})
    assert response3.status_code == 200, f"Unexpected status code: {response3.status_code}"
    assert response3.json() == {'message': f"Your favorite model is pix2pix !"}  

# get users list test
def test_users_list(client, test_admin):
    token = test_auth_token(client, test_admin)
    response = client.get("/get_users_list", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"

# disable_user endpoint test
def test_disable_user(client, test_admin):
    token = test_auth_token(client, test_admin)
    response = client.post("/disable_user?username=unittestuser", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    assert response.json() == {'message': "User(unittestuser) is disable !"} 

# enable_user endpoint test
def test_enable_user(client, test_admin):
    token = test_auth_token(client, test_admin)
    response = client.post("/enable_user?username=unittestuser", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    assert response.json() == {'message': "User(unittestuser) is enable !"} 

# set admin access endpoint test
def test_set_admin_access(client, test_admin):
    token = test_auth_token(client, test_admin)
    response = client.post("/set_admin_access?username=unittestuser", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    assert response.json() == {'message': "Admin access is enabled for unittestuser!"}
    response2 = client.post("/set_admin_access?username=unittestuser", headers={"Authorization": f"Bearer {token}"})
    assert response2.status_code == 200, f"Unexpected status code: {response.status_code}"
    assert response2.json() == {'message': "Admin access is disabled for unittestuser!"} 

# delete_user endpoint test
def test_delete_user(client, test_user):
    token = test_auth_token(client, test_user)
    response = client.post("/delete_user?username=unittestuser", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    assert response.json() == {'message': "User(unittestuser) + Data deleted successfully !"} 
