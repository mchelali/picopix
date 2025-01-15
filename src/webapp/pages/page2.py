# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# WEBAPP STREAMLIT

# Declare libraries
from navigation import make_sidebar
import streamlit as st
import os
import requests
import tempfile
from PIL import Image
from dotenv import load_dotenv

# display sidebar
make_sidebar()

# title
st.write(
    """
# 🔮 Coloriser

"""
)

# Load .env environment variables
load_dotenv()
IMG_SIZE_H_MIN = os.getenv("IMG_SIZE_H_MIN")
IMG_SIZE_W_MIN = os.getenv("IMG_SIZE_W_MIN")
IMG_SIZE_H_MAX = os.getenv("IMG_SIZE_H_MAX")
IMG_SIZE_W_MAX = os.getenv("IMG_SIZE_W_MAX")
IMG_SIZE_KB_MAX = os.getenv("IMG_SIZE_KB_MAX")
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES"))

# Display required image properties
st.markdown(
    f"""
    **Spécifications de l'image:**
    - Format: JPG ou JPEG
    - Dimensions: entre {IMG_SIZE_H_MIN}x{IMG_SIZE_W_MIN} et {IMG_SIZE_H_MAX}x{IMG_SIZE_W_MAX} pixels
    - Taille maximale: {IMG_SIZE_KB_MAX} Ko
    - L'image doit être en noir et blanc
    """
)

# Upload control zone
uploaded_file = st.file_uploader(
    "Choisissez une image en noir et blanc",
    type=["jpg", "jpeg"],
    accept_multiple_files=False,
)

if uploaded_file is not None:
    image = Image.open(uploaded_file)

    # Check image height & width
    if not (512 <= image.size[0] <= 2024 and 512 <= image.size[1] <= 2024):
        st.error(
            f"Les dimensions de l'image doivent être entre {IMG_SIZE_H_MIN}x{IMG_SIZE_W_MIN} et {IMG_SIZE_H_MAX}x{IMG_SIZE_W_MAX} pixels"
        )
    else:
        # Display image
        st.subheader("Image Originale")
        st.image(image, use_container_width=True)
        # Colorize
        if st.button("Coloriser", icon="🎨"):
            # Get token value
            token = st.session_state.get("token")
            # write file on streamlit server
            os.makedirs("cache/tmp", exist_ok=True)
            tempfilename = f"cache{tempfile.NamedTemporaryFile().name}.jpg"
            with open(tempfilename, "wb") as f:
                f.write(uploaded_file.getvalue())
            f.close()
            # request upload bw image endpoint
            headers = {"Authorization": f"Bearer {token['access_token']}"}
            res = requests.post(
                url=f"http://api:8000/upload_bw_image",
                headers=headers,
                files=[
                    ("file", ("upload.jpg", open(tempfilename, "rb"), "image/jpeg"))
                ],
            )
            if res.status_code == 200:
                # if upload ok then request colorize endpoint
                headers = {
                    "accept": "application/json",
                    "Authorization": f"Bearer {token['access_token']}",
                }
                res2 = requests.get(
                    url=f"http://api:8000/colorize_bw_image",
                    headers=headers,
                )
                if res2.status_code == 200:
                    # if colorize ok then display colorized image (bucket url)
                    st.subheader("Images Colorisées")
                    if res2.json()["url1"] != "":
                        st.write("Modèle Autoencoder:")
                        st.image(
                            Image.open(
                                requests.get(f"{res2.json()['url1']}", stream=True).raw
                            ),
                            use_container_width=True,
                        )
                    if res2.json()["url2"] != "":
                        st.write("Modèle Pix2Pix:")
                        st.image(
                            Image.open(
                                requests.get(f"{res2.json()['url2']}", stream=True).raw
                            ),
                            use_container_width=True,
                        )
                else:
                    st.error(f"Error {res2.status_code} {res2.json()['detail']}")
            else:
                st.error(f"Error {res.status_code} {res.json()['detail']}")
            # delete temporary file
            if os.path.exists(tempfilename):
                os.remove(tempfilename)
