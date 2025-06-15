import streamlit as st
from page_coach import page_coach
from page_athlete import page_athlete
import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

st.set_page_config(page_title="Plateforme Entraînement", layout="wide")

# --- Chargement des utilisateurs
USERS_FILE = "data/users.csv"

@st.cache_data
def load_users():
    if os.path.exists(USERS_FILE):
        return pd.read_csv(USERS_FILE)
    return pd.DataFrame(columns=["Nom", "Mot de passe"])

users_df = load_users()
usernames = users_df["Nom"].tolist()

# --- Choix de l'espace
espace = st.sidebar.selectbox("🔐 Choisir un espace :", ["Athlète", "Coach"])

if espace == "Coach":
    mdp = st.sidebar.text_input("Mot de passe coach", type="password")
    if mdp == "coach123":  # 🔒 À personnaliser ou sécuriser via fichier
        st.sidebar.success("Accès coach validé ✅")
        # Choix du profil athlète à afficher (optionnel)
        st.sidebar.markdown("---")
        #st.sidebar.markdown("👁️ Voir l'espace d'un athlète :")
        #athlètes = sorted(users_df["Nom"].tolist())
        #athlète_choisi = st.sidebar.selectbox("Athlète à consulter", athlètes)
        #Page_athlete(nom_athlete=athlète_choisi)
        st.header("👨‍🏫 Espace Coach")
        page_coach()
    elif mdp != "":
        st.sidebar.error("Mot de passe incorrect")

elif espace == "Athlète":
    nom = st.sidebar.selectbox("Nom", usernames)
    mdp = st.sidebar.text_input("Mot de passe", type="password")

    if not users_df.empty:
        vrai_mdp = users_df[users_df["Nom"] == nom]["Mot de passe"].values[0]
        if mdp == str(vrai_mdp):
            st.sidebar.success(f"Bienvenue {nom} !")
            page_athlete(nom_athlete=nom)
        elif mdp != "":
            st.sidebar.error("Mot de passe incorrect.")
