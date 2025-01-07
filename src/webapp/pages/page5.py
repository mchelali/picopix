from navigation import make_sidebar
import streamlit as st
from time import sleep
import requests

make_sidebar()

st.write(
    """
# 🔓 Administration

"""
)

@st.fragment(run_every="10s")
def list_users():
    token = st.session_state.get("token")
    headers = {"accept":"application/json","Authorization":f"Bearer {token['access_token']}"}
    res = requests.get(url="http://api:8000/get_users_list",headers=headers)
    infousers = res.json()
    users_list=[]
    for user in infousers:
        users_list.append(user)
        if infousers[user]['disabled'] == True:
            statut= "❌:red[compte désactivé]"
        else:
            statut= "✅:green[compte activé]"
        if infousers[user]['isadmin'] == True:
            adminlogo = "🔑 :orange[administrateur]"
        else:
            adminlogo = ""
        st.markdown(f":blue[{user}] ({infousers[user]['firstname']} {infousers[user]['lastname']}) {adminlogo} {statut}")
    return users_list


users_list = list_users()
selectuser = st.selectbox("Utilisateur",(users_list))
selectaction = st.selectbox("Action",(["✅ Activer compte utilisateur","❌ Désactiver compte utilisateur","🔑 Activer/Désactiver rôle administrateur","💣 Supprimer compte utilisateur"]))
if st.button("Executer action",icon="👍"):
    token = st.session_state.get("token")
    headers = {"accept":"application/json","Authorization":f"Bearer {token['access_token']}"}
    if selectaction=="✅ Activer compte utilisateur":
        res = requests.post(url=f"http://api:8000/enable_user?username={selectuser}",headers=headers)
        if res.status_code == 200:
            st.success(f"Le compte {selectuser} a été activé.")
            sleep(1)
        else:
            st.error(f"Erreur : {res.json()}")
    if selectaction=="❌ Désactiver compte utilisateur":
        res = requests.post(url=f"http://api:8000/disable_user?username={selectuser}",headers=headers)
        if res.status_code == 200:
            st.success(f"Le compte {selectuser} a été désactivé.")
            sleep(1)
        else:
            st.error(f"Erreur : {res.json()}")
    if selectaction=="💣 Supprimer compte utilisateur":
        res = requests.post(url=f"http://api:8000/delete_user?username={selectuser}",headers=headers)
        if res.status_code == 200:
            st.success(f"Le compte {selectuser} a été supprimé.")
            sleep(1)
        else:
            st.error(f"Erreur : {res.json()}")
    if selectaction=="🔑 Activer/Désactiver rôle administrateur":
        res = requests.post(url=f"http://api:8000/set_admin_access?username={selectuser}",headers=headers)
        if res.status_code == 200:
            st.success(f"Le rôle administrateur a été modifié pour le compte {selectuser}.")
            sleep(1)
        else:
            st.error(f"Erreur : {res.json()}")