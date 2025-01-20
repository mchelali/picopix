# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# WEBAPP STREAMLIT

# Declare libraries
from navigation import make_sidebar
import streamlit as st
from PIL import Image
from time import sleep
import requests
import pandas as pd

# Configuration de la page
im = Image.open("assets/images/logo.ico")
st.set_page_config(
    page_title="PicoPix - Administration",
    page_icon=im,
    layout="wide",
)

# display sidebar
make_sidebar()

# title
st.title("🔓 Administration")

# get & display users list with automatic refresh
@st.fragment(run_every="10s")
def list_users():
    # get user_list endpoint
    token = st.session_state.get("token")
    headers = {"accept":"application/json","Authorization":f"Bearer {token['access_token']}"}
    res = requests.get(url="http://api:8000/get_users_list",headers=headers)
    infousers = res.json()
    df = pd.DataFrame(columns=["Utilisateur","Prenom","Nom","Statut","Rôle"])
    # construct users list
    users_list=[]
    i = 0
    for user in infousers:
        users_list.append(user)
        if infousers[user]['disabled'] == True:
            #statut= "❌:red[compte désactivé]"
            statut = "❌compte désactivé"
        else:
            #statut= "✅:green[compte activé]"
            statut = "✅compte activé"
        if infousers[user]['isadmin'] == True:
            #adminlogo = "🔑 :orange[administrateur]"
            adminlogo = "🔑 administrateur"
        else:
            adminlogo = "utilisateur"
        df.loc[i] = [user,infousers[user]['firstname'],infousers[user]['lastname'],statut,adminlogo]
        i = i+1
        #st.markdown(f":blue[{user}] ({infousers[user]['firstname']} {infousers[user]['lastname']}) {adminlogo} {statut}")
    st.dataframe(df,hide_index=True)
    return users_list

# display users list
users_list = list_users()

# selectbox with users
selectuser = st.selectbox("Utilisateur",(users_list))
# selectbox with actions (enable,disable,delete user, and unable/disable admin privilege)
selectaction = st.selectbox("Action",(["✅ Activer compte utilisateur","❌ Désactiver compte utilisateur","🔑 Activer/Désactiver rôle administrateur","💣 Supprimer compte utilisateur"]))
if st.button("Executer action",icon="👍"):
    token = st.session_state.get("token")
    headers = {"accept":"application/json","Authorization":f"Bearer {token['access_token']}"}
    # post enable_user endpoint
    if selectaction=="✅ Activer compte utilisateur":
        res = requests.post(url=f"http://api:8000/enable_user?username={selectuser}",headers=headers)
        if res.status_code == 200:
            st.success(f"Le compte {selectuser} a été activé.")
            sleep(1)
        else:
            st.error(f"Erreur : {res.json()}")
    # post disable_user endpoint
    if selectaction=="❌ Désactiver compte utilisateur":
        res = requests.post(url=f"http://api:8000/disable_user?username={selectuser}",headers=headers)
        if res.status_code == 200:
            st.success(f"Le compte {selectuser} a été désactivé.")
            sleep(1)
        else:
            st.error(f"Erreur : {res.json()}")
    # post delete_user endpoint
    if selectaction=="💣 Supprimer compte utilisateur":
        res = requests.post(url=f"http://api:8000/delete_user?username={selectuser}",headers=headers)
        if res.status_code == 200:
            st.success(f"Le compte {selectuser} a été supprimé.")
            sleep(1)
        else:
            st.error(f"Erreur : {res.json()}")
    # post set_admin_access endpoint
    if selectaction=="🔑 Activer/Désactiver rôle administrateur":
        res = requests.post(url=f"http://api:8000/set_admin_access?username={selectuser}",headers=headers)
        if res.status_code == 200:
            st.success(f"Le rôle administrateur a été modifié pour le compte {selectuser}.")
            sleep(1)
        else:
            st.error(f"Erreur : {res.json()}")