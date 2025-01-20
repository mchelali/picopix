# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# WEBAPP STREAMLIT

# Declare libraries
from navigation import make_sidebar
from time import sleep
import requests
from PIL import Image
from io import BytesIO
import streamlit as st

# Configuration de la page
im = Image.open("assets/images/logo.ico")
st.set_page_config(
    page_title="PicoPix - Images colorisées",
    page_icon=im,
    layout="wide",
)

# display sidebar
make_sidebar()

# title
st.title("👀 Images colorisées")

# request get_colorized_images_list endpoint
token = st.session_state.get("token")
headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {token['access_token']}",
}
res = requests.get(url="http://api:8000/get_colorized_images_list", headers=headers)
infoimages = res.json()
images_list = []

# display images & images properties
tab1, tab2 = st.tabs(["Autoencoder", "Pix2Pix"])
for img in infoimages:
    imgmdl = infoimages[img]['model'].split("/")[0]
    if infoimages[img]['rating']!="None":
        image_rating = int(infoimages[img]['rating'])*"⭐"
    else:
        image_rating = "-"
    with tab1:
        col1,col2 = st.columns(2)
        if imgmdl=="autoencoder":
            st.divider()
            with col1:
                st.image(Image.open(requests.get(f"{infoimages[img]['colorized_image_url']}",stream=True).raw),width=256)
            with col2:
                st.text(f"Image {img} ({image_rating})")
                st.text(f"Date : {infoimages[img]['creation_date']}")
                st.text(f"Modèle : {infoimages[img]['model']}")
    with tab2:
        col1,col2 = st.columns(2)
        if imgmdl=="pix2pix":
            st.divider()
            with col1:
                st.image(Image.open(requests.get(f"{infoimages[img]['colorized_image_url']}",stream=True).raw),width=256)
            with col2:
                st.text(f"Image {img} ({image_rating})")
                st.text(f"Date : {infoimages[img]['creation_date']}")
                st.text(f"Modèle : {infoimages[img]['model']}")
    images_list.append(img)

# rating form
st.markdown(":rainbow[Notation]")
# images id
rateimage = st.selectbox("Image", (images_list))
# rating control
rate = st.number_input("Note (0 à 10)", min_value=0, max_value=5, value=2, step=1)
# if click rating button
if st.button("Noter", icon="🥇"):
    # request rate_colorized_image endpoint
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token['access_token']}",
    }
    res2 = requests.post(
        url=f"http://api:8000/rate_colorized_image/{rateimage[len(rateimage)-6:]}?rating={rate}",
        headers=headers,
    )
    if res2.status_code == 200:
        st.success(f"L'image {rateimage} a été notée avec succès !")
        sleep(1)
        st.rerun()
    else:
        st.error(f"Erreur : {res2.json()}")
