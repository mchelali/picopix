import streamlit as st
from time import sleep
import requests
from navigation import make_sidebar

make_sidebar()

st.title("Welcome to Picopix")

st.write("Please log in to continue.")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Log in", type="primary"):
    inputs = {"username":username,"password":password}
    headers = {"Content-Type": "application/x-www-form-urlencoded", "accept":"application/json"}
    res = requests.post(url="http://api:8000/auth/token",
                        headers=headers,
                        data=f"grand_type=password&username={username}&password={password}&scope=?client_id=string&client_secret=string")
    # if success : save token string
    if res.status_code==200:
        st.session_state.logged_in = True
        st.session_state.user = username
        st.session_state.token = res.json()
        st.success("Logged in successfully!")
        sleep(0.5)
        st.switch_page("pages/page1.py")
    else:
        st.error("Incorrect username or password")