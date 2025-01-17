# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# WEBAPP STREAMLIT

# Declare libraries
from navigation import make_sidebar
import streamlit as st
import os
import requests
import tempfile
import io
from PIL import Image
from dotenv import load_dotenv

# Configuration de la page
im = Image.open("assets/images/logo.ico")
st.set_page_config(
    page_title="PicoPix - Coloriser",
    page_icon=im,
    layout="wide",
)

# display sidebar
make_sidebar()

# Load .env environment variables
load_dotenv()
IMG_SIZE_H_MIN = os.getenv("IMG_SIZE_H_MIN")
IMG_SIZE_W_MIN = os.getenv("IMG_SIZE_W_MIN")
IMG_SIZE_H_MAX = os.getenv("IMG_SIZE_H_MAX")
IMG_SIZE_W_MAX = os.getenv("IMG_SIZE_W_MAX")
IMG_SIZE_KB_MAX = os.getenv("IMG_SIZE_KB_MAX")
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES"))

# Title
st.title("🔮 Description")

# Display required image properties
with st.expander("Spécifications de l'image"):
    st.markdown(f"""
    - Format: JPG ou JPEG
    - Dimensions: entre {IMG_SIZE_H_MIN}x{IMG_SIZE_W_MIN} et {IMG_SIZE_H_MAX}x{IMG_SIZE_W_MAX} pixels
    - Taille maximale: {IMG_SIZE_KB_MAX} Ko
    - L'image doit être en noir et blanc
    """)

# Upload control zone
uploaded_file = st.file_uploader("Choisissez une image en noir et blanc", type=['jpg', 'jpeg'], accept_multiple_files=False,)

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    
    # Check image height & width
    if not (512 <= image.size[0] <= 2024 and 512 <= image.size[1] <= 2024):
        st.error(f"Les dimensions de l'image doivent être entre {IMG_SIZE_H_MIN}x{IMG_SIZE_W_MIN} et {IMG_SIZE_H_MAX}x{IMG_SIZE_W_MAX} pixels")
    else:
        # Display image
        col1, col2, col3 = st.columns(3)
        col1.subheader("Image Originale")
        col1.image(image, width=256)
        # Colorize
        if st.button("Coloriser",icon="🎨"):
            with st.spinner("Upload de l'image en cours..."):
                # Get token value
                token = st.session_state.get("token")
                # write file on streamlit server
                os.makedirs("cache/tmp", exist_ok=True)
                tempfilename = f"cache{tempfile.NamedTemporaryFile().name}.jpg"
                with open(tempfilename, "wb") as f:
                        f.write(uploaded_file.getvalue())
                f.close()
                # request upload bw image endpoint
                headers = {"Authorization":f"Bearer {token['access_token']}"}
                res = requests.post(url=f"http://api:8000/upload_bw_image",headers=headers,files=[("file",("upload.jpg",open(tempfilename, "rb"),"image/jpeg"))])
            if res.status_code==200:
                # if upload ok then request colorize endpoint
                with st.spinner("Colorisation de l'image en cours..."):
                    headers = {"accept":"application/json","Authorization":f"Bearer {token['access_token']}"}
                    res2 = requests.get(url=f"http://api:8000/colorize_bw_image",
                                    headers=headers,)
                if res2.status_code==200:
                    # if colorize ok then display colorized image (bucket url)
                    if res2.json()['url1'] != "":
                        col2.subheader("Colorisation Autoencoder")
                        im_ae = Image.open(requests.get(f"{res2.json()['url1']}",stream=True).raw)
                        col2.image(im_ae,width=256)
                        buf2 = io.BytesIO()
                        im_ae.save(buf2, format='JPEG')
                        btn2 = col2.download_button(
                            label="Télécharger image",
                            data=buf2.getvalue(),
                            file_name=f"autoencoder_color_picture.jpg",
                            mime="image/jpg",
                        )
                    if res2.json()['url2'] != "":
                        col3.subheader("Colorisation Pix2Pix")
                        im_p2p = Image.open(requests.get(f"{res2.json()['url2']}",stream=True).raw)
                        col3.image(im_p2p,width=256)
                        buf3 = io.BytesIO()
                        im_p2p.save(buf3, format='JPEG')                        
                        btn3 = col3.download_button(
                            label="Télécharger image",
                            data=buf3.getvalue(),
                            file_name=f"pix2pix_color_picture.jpg",
                            mime="image/jpg",
                        )
                else:
                    st.error(f"Error {res2.status_code} {res2.json()['detail']}")
            else:
                st.error(f"Error {res.status_code} {res.json()['detail']}")
            # delete temporary file
            if os.path.exists(tempfilename):
                os.remove(tempfilename)