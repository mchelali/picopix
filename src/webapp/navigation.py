import streamlit as st
from time import sleep
import requests
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.source_util import get_pages


def get_current_page_name():
    ctx = get_script_run_ctx()
    if ctx is None:
        raise RuntimeError("Couldn't get script context")

    pages = get_pages("")

    return pages[ctx.page_script_hash]["page_name"]


def make_sidebar():
    with st.sidebar:
        st.title("🎨 PicoPix")
        if st.session_state.get("logged_in", False):
            token = st.session_state.get("token")
            headers = {"accept":"application/json","Authorization":f"Bearer {token['access_token']}"}
            res2 = requests.get(url="http://api:8000/get_user_informations",headers=headers)
            infouser = res2.json()
            st.session_state.favmodel = infouser['favorite_model']
            st.markdown(f"Utilisateur : {infouser['firstname']} {infouser['lastname']}")
            st.page_link("pages/page1.py", label="Description", icon="📌")
            st.page_link("pages/page2.py", label="Coloriser", icon="🔮")
            st.page_link("pages/page3.py", label="Images colorisées", icon="👀")
            st.page_link("pages/page4.py", label="Préférences", icon="🧾")
            if infouser['isadmin'] == True:
                st.page_link("pages/page5.py", label="Administration", icon="🔒")

            st.write("")
            st.write("")

            if st.button("Log out"):
                logout()

        elif get_current_page_name() != "app":
            st.switch_page("app.py")

def logout():
    st.session_state.logged_in = False
    st.session_state.user = ""
    st.session_state.token = ""
    st.info("Logged out successfully!")
    sleep(0.5)
    st.switch_page("app.py")