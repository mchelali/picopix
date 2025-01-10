# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# WEBAPP STREAMLIT

# Declare libraries
import streamlit as st
from time import sleep
import requests
from navigation import make_sidebar

# call sidebar generator
make_sidebar()

# Log in form
st.title("Welcome to Picopix")
st.write("Please log in to continue.")

# textbox fields
username = st.text_input("Username (required for log in)")
firstname = st.text_input("Firstname (optional)")
lastname = st.text_input("Lastname (optional)")
password = st.text_input("Password (required for log in)", type="password")

# if click button log in
if st.button("Log in", type="primary"):
    # request token api endpoint 
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

# if click button register
if st.button("Register"):
    if len(username)>0 and len(firstname)>0 and len(lastname)>0 and len(password)>0:
        # request create user api endpoint 
        headers = {"Content-Type": "application/json", "accept":"application/json"}
        data = {"username":username,"firstname":firstname,"lastname":lastname,"password":password}
        res2 = requests.post(url="http://api:8000/auth/create_user",
                            headers=headers,
                            json=data)
        # if success : save token string
        if res2.status_code==201:
            st.success("Register successfully ! Please Log in")
            sleep(2)
        else:
            st.error("Account creation error")
    else:
        st.error("Required field missing.")