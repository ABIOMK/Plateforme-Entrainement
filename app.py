import streamlit as st
from page_coach import page_coach
from page_athlete import page_athlete
import pandas as pd
import os
import sys
from utils.calculs import generer_identifiant

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

st.set_page_config(page_title="Plateforme Entraînement", layout="wide")

# --- fonction accueil ---
def afficher_page_accueil():
    st.title("🏃🏽 Plateforme d'entraînement personnalisée 🚴🏼")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("logo_BIOMK.png", width=400)
    st.markdown("""
    👋🏼 Bienvenue sur votre espace d’entraînement individuel et sécurisé !   
    
    Cet espace personnalisé vous est entièrement dédié.
    
    Ici vous pouvez :
    - Consulter votre planning d'entraînement, 
    - Accéder au contenu de chaque séance,
    - Suivre vos progrès,
    - Donner vos feedback après chaque séance, 
    - Ajouter des séances supplémentaires non prévues dans le plan initial. 
    ---
    👉 Saisissez votre rôle, login et mot de passe dans le menu latéral pour commencer.
    """)
    st.info("🔐 Toutes les données sont confidentielles et accessibles uniquement via ID et mot de passe.")

# --- Chargement des utilisateurs
USERS_FILE = "data/users.csv"

@st.cache_data
def load_users():
    if os.path.exists(USERS_FILE):
        return pd.read_csv(USERS_FILE)
    return pd.DataFrame(columns=["Nom", "Mot de passe"])

users_df = load_users()
usernames = users_df["Nom"].tolist()

# --- Sidebar avec sélection espace ---
espace = st.sidebar.selectbox("🔐 Choisir un espace :", ["Accueil", "Athlète", "Coach"])
if espace == "Accueil":
    afficher_page_accueil()

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
    st.sidebar.subheader("Connexion Athlète")
    identifiant = st.sidebar.text_input("Identifiant (ex : prenomnom)")
    mdp = st.sidebar.text_input("Mot de passe", type="password")

    # Normalisation (au cas où l'utilisateur met des majuscules ou accents)
    identifiant = generer_identifiant(identifiant)

    if identifiant and mdp:
        utilisateur = users_df[
            (users_df["Identifiant"] == identifiant) &
            (users_df["Mot de passe"] == mdp) &
            (users_df["Role"] == "athlete")
        ]

        if not utilisateur.empty:
            nom_affiché = utilisateur["Nom"].values[0]
            st.sidebar.success(f"Bienvenue {nom_affiché} !")
            page_athlete(nom_athlete=nom_affiché)
        else:
            st.sidebar.error("Identifiant ou mot de passe incorrect")
