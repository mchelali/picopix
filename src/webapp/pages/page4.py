from navigation import make_sidebar
import streamlit as st
from time import sleep
import requests

make_sidebar()

st.write(
    """
# 🧾 Préférences

"""
)

favmodel = st.session_state.get("favmodel")
favmodel_list = ["0 - aucun","1 - AutoEncoder","2 - Pix2Pix"]

st.write(f"Modèle préféré : {favmodel_list[favmodel][4:]}")
modelchoice = st.radio(":rainbow[Modifier votre modèle préféré :]",
                       favmodel_list,
                       index=None,
                       )

if st.button("Valider",icon="💖"):
    # Get token value
    token = st.session_state.get("token")
    # request upload bw image endpoint
    headers = {"accept":"application/json","Authorization":f"Bearer {token['access_token']}","Content-Type":"application/json"}
    data = {"mdl":int(modelchoice[:1])}
    res = requests.post(url=f"http://api:8000/set_favorite_model",headers=headers,json=data)
    if res.status_code==200:
        st.success("Modification validée avec succès !")
        sleep(1)
        st.rerun()
    else:
        st.error(f"Erreur : {res.json()}")