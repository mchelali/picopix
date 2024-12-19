# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# Streamlit frontapp

# Declare libraries
import streamlit as st
import requests
import json
import io
import os
import time
from PIL import Image
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

# Load .env environment variables
load_dotenv()
IMG_SIZE_H_MIN = os.getenv("IMG_SIZE_H_MIN")
IMG_SIZE_W_MIN = os.getenv("IMG_SIZE_W_MIN")
IMG_SIZE_H_MAX = os.getenv("IMG_SIZE_H_MAX")
IMG_SIZE_W_MAX = os.getenv("IMG_SIZE_W_MAX")
IMG_SIZE_KB_MAX = os.getenv("IMG_SIZE_KB_MAX")

# Create an empty container
placeholder = st.empty()

# Insert login form in the container
with placeholder.form("login"):
    st.markdown("#### Enter your credentials")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submit = st.form_submit_button("Login")

if submit:
    # post request with username & password
    inputs = {"username":username,"password":password}
    headers = {"Content-Type": "application/x-www-form-urlencoded", "accept":"application/json"}
    res = requests.post(url="http://api:8000/auth/token",
                        headers=headers,
                        data=f"grand_type=password&username={username}&password={password}&scope=?client_id=string&client_secret=string")
    # if success : wait 2 seconds and save token string
    if res.status_code==200:
        placeholder.empty()
        token=res.json()


        #try:
        headers = {"accept":"application/json","Authorization":f"Bearer {token['access_token']}"}
        res2 = requests.get(url="http://api:8000/get_user_informations",headers=headers)
        infouser = res2.json()
        tab1,tab2,tab3,tab4,tab5=st.tabs(['Description','Coloriser une image','Images colorisées','Préréfences','Administration'])
        with tab1:
            # title     
            st.title("🎨 PicoPix - Service de Colorisation d'Images")

            st.markdown(f"User: {infouser['firstname']} {infouser['lastname']}")

            # Presentation   
            st.markdown("""
            Cette application permet de coloriser vos images en noir et blanc en utilisant deux algorithmes 
            d'intelligence artificielle différents. Vous pourrez comparer les résultats et choisir la 
            meilleure colorisation.
            """)

        with tab2:
            # Colorize picture
            st.header("Coloriser une image")
            st.markdown(f"""
            **Spécifications de l'image:**
            - Format: JPG ou JPEG
            - Dimensions: entre {IMG_SIZE_H_MIN}x{IMG_SIZE_W_MIN} et {IMG_SIZE_H_MAX}x{IMG_SIZE_W_MAX} pixels
            - Taille maximale: {IMG_SIZE_KB_MAX} Ko
            - L'image doit être en noir et blanc
            """)

            ## Upload et Traitement
            uploaded_file = st.file_uploader("Choisissez une image en noir et blanc", type=['jpg', 'jpeg'])

            if uploaded_file is not None:
                try:
                    image = Image.open(uploaded_file)
                    
                    # Vérification des dimensions
                    if not (512 <= image.size[0] <= 2024 and 512 <= image.size[1] <= 2024):
                        st.error(f"Les dimensions de l'image doivent être entre {IMG_SIZE_H_MIN}x{IMG_SIZE_W_MIN} et {IMG_SIZE_H_MAX}x{IMG_SIZE_W_MAX} pixels")
                    else:
                        st.subheader("Image Originale")
                        st.image(image, use_column_width=True)
                                    
                except Exception as e:
                    st.error(f"Erreur lors de la colorisation: {str(e)}")
        with tab3:
            # Colorized pictures tab
            st.header("Images colorisées")
        with tab4:
            # Pref tab
            st.header("Préférences")
        if infouser['isadmin'] == True:
            with tab5:
                # Administration tab
                st.header("Administration")
    
        #except Exception as e:
        #    st.error(f"Erreur lors de la récupération des informations de l'utilisateur: {str(e)}")      
    else:
        st.error(f"Login failure ! Error {res.status_code} {res.json()}")
else:
    pass


