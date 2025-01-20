from streamlit.testing.v1 import AppTest
from unittest.mock import patch
import pytest
import requests

@pytest.fixture()
def at():
    yield AppTest.from_file("app.py",default_timeout=10).run()
"""
def test_register(at):
    at.text_input[0].input("testunituser").run()
    at.text_input[1].input("User").run()
    at.text_input[2].input("TESTUNIT").run()
    at.text_input[3].input("test").run()
    
    at.button[1].click().run()

    assert "Register successfully ! Please Log in" in at.success[0].value
"""

def test_login(at):

    # Bad password
    at.text_input[0].input("testunituser").run()
    at.text_input[3].input("password").run()
    at.button[0].click().run()
    assert "Incorrect username or password" in at.error[0].value

    # Good password
    at.text_input[0].input("testunituser").run()
    at.text_input[3].input("test").run()
    at.button[0].click().run()

    assert "Logged in successfully!" in at.success[0].value


def test_sidebar_page1():
    at = AppTest.from_file("app.py",default_timeout=10).run()

    at.text_input[0].input("testunituser")
    at.text_input[3].input("test")
    at.button[0].click().run()

    assert "📌 Description" in at.title[0].value

"""
def test_page2():
    headers = {"Content-Type": "application/x-www-form-urlencoded", "accept":"application/json"}
    res = requests.post(url="http://api:8000/auth/token",
                        headers=headers,
                        data=f"grand_type=password&username=testunituser&password=test&scope=?client_id=string&client_secret=string")
    # if success : save token string
    if res.status_code==200:
        at = AppTest.from_file("pages/page2.py",default_timeout=10)
        at.session_state["logged_in"] = True
        at.session_state["user"] = "testunituser"
        at.session_state["token"] = res.json()
        at.run()

        assert "🎨 PicoPix" in at.sidebar.title[0].value
        assert "🔮 Coloriser" in at.title[0].value
"""


