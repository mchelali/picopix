from navigation import make_sidebar
import requests
from PIL import Image
import streamlit as st

make_sidebar()

st.write(
    """
# 👀 Images colorisées

"""
)
token = st.session_state.get("token")
headers = {"accept":"application/json","Authorization":f"Bearer {token['access_token']}"}
res = requests.get(url="http://api:8000/get_colorized_images_list",headers=headers)
infoimages = res.json()
images_list = []
for img in infoimages:
    st.text(f"Image {img}")
    st.image(Image.open(requests.get(f"{infoimages[img]['colorized_image_url']}",stream=True).raw),width=60)
    images_list.append(img)

st.write("")
st.write("")
st.markdown(":rainbow[Notation]")
rateimage = st.selectbox("Image",(images_list))
rate = st.number_input('Note (0 à 10)', min_value=0, max_value=10, value=5, step=1)
if st.button("Noter",icon="🥇"):
    headers = {"accept":"application/json","Authorization":f"Bearer {token['access_token']}"}
    res2 = requests.post(url=f"http://api:8000/rate_colorized_image/{rateimage[len(rateimage)-6:]}?rating={rate}",headers=headers)
    if res2.status_code==200:
        st.write(f"{rateimage} a été notée avec succès.")
