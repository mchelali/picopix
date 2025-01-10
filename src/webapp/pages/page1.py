# Project PicoPix
# Authors : Mohamed CHELALI, Daniel LEWANDOWSKI, Yannick OREAL
# WEBAPP STREAMLIT

# Declare libraries
from navigation import make_sidebar
import streamlit as st

# display sidebar
make_sidebar()

# description
st.write(
    """
# 📌 Description

Cette application permet de coloriser vos images en noir et blanc en utilisant deux algorithmes 
d'intelligence artificielle différents (Pix2Pix ). Vous pourrez comparer les résultats et choisir votre
algorithme préféré pour vous colorisations.

Il est également possible de noter vos images colorisées afin que les data scientists évaluent
leurs modèles et implémentent de nouvelles itérations de ces derniers.
"""
)
