# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# WEBAPP STREAMLIT

# Declare libraries
from navigation import make_sidebar
import streamlit as st
from PIL import Image

# Configuration de la page
im = Image.open("assets/images/logo.ico")
st.set_page_config(
    page_title="PicoPix - Description",
    page_icon=im,
    layout="wide",
)

# display sidebar
make_sidebar()

# title
st.title("📌 Description")

# description
st.markdown("""
<div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>
    <h2>Bienvenue sur PicoPix !</h2>
    <p>Cette application vous permet de coloriser vos images en noir et blanc en utilisant deux algorithmes 
    d'intelligence artificielle différents (Autoencoder et Pix2Pix).</p>
    <h3>Fonctionnalités principales :</h3>
    <ul>
        <li>🖼️ Colorisation d'images en noir & blanc</li>
        <li>🔄 Comparaison des résultats entre deux algorithmes</li>
        <li>⭐ Notation des images colorisées</li>
        <li>📊 Evaluation continue des modèles par les data scientits</li>
    </ul>     
</div>
""", unsafe_allow_html=True)

# Ajouter des images ou des icônes pour illustrer les fonctionnalités
#col1, col2 = st.columns(2)
#with col1:
#    st.image("path_to_image1.jpg", caption="Exemple de colorisation")
#with col2:
#    st.image("path_to_image2.jpg", caption="Comparaison des algorithmes")

