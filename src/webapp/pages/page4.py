# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# WEBAPP STREAMLIT

# Declare libraries
from navigation import make_sidebar
import streamlit as st
from PIL import Image
from time import sleep
import requests

# Configuration de la page
im = Image.open("assets/images/logo.ico")
st.set_page_config(
    page_title="PicoPix - Préférences",
    page_icon=im,
    layout="wide",
)

# display sidebar
make_sidebar()

# title
st.title("🧾 Préférences")

# get favorite model with session_state variable
favmodel = st.session_state.get("favmodel")

# display current favorite model
favmodel_list = ["0 - aucun","1 - AutoEncoder","2 - Pix2Pix"]
st.write(f"Modèle préféré : {favmodel_list[favmodel][4:]}")

# radio control with choice 0,1,2
modelchoice = st.radio(
    ":rainbow[Modifier votre modèle préféré :]",
    favmodel_list,
)

# if click validate button
if st.button("Valider",icon="💖"):
    # Get token value
    token = st.session_state.get("token")
    # request set_favorite_model endpoint
    headers = {"accept":"application/json","Authorization":f"Bearer {token['access_token']}","Content-Type":"application/json"}
    data = {"mdl":int(modelchoice[:1])}
    res = requests.post(url=f"http://api:8000/set_favorite_model",headers=headers,json=data)
    if res.status_code==200:
        st.success("Modification validée avec succès !")
        sleep(1)
        st.rerun()
    else:
        st.error(f"Erreur : {res.json()}")