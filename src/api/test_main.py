# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# Unit Tests

from fastapi.testclient import TestClient

# Declare unit tests client
from main import app
client = TestClient(app)

# root endpoint test
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        'message': "Welcome to ColorPix !",
    }

# create_user endpoint test
def test_create_user():
    response = client.post("/auth/create_user",json={"username":"testcreateuser",
                                                "firstname":"Test",
                                                "lastname":"CREATEUSER",
                                                "password":"testpassword"})
    assert response.status_code == 201
    assert response.json() == {
        'message': f"User testcreateuser created !",
    } 