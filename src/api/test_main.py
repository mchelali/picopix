# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# Unit Tests

from fastapi.testclient import TestClient
import pytest
from main import app

# Declare unit tests client
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def test_user():
    return {"username": "unittestuser", "password": "testpassword"}

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

# authenticate test (get token)
def test_auth_token(client, test_user):
    response = client.post("/auth/token",data=test_user)                                           
    assert response.status_code == 200
    token =response.json()["access_token"]
    assert token is not None
    return token

# delete_user endpoint test
def test_delete_user(client, test_user):
    token = test_auth_token(client, test_user)
    response = client.post("/delete_user?username=unittestuser", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {'message': "User(unittestuser) + Data deleted succesfully !"} 