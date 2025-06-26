import streamlit as st
import pandas as pd
import plotly.express as px
import json
import re
import time
from datetime import date,datetime, timedelta
from utils.io import load_csv, save_csv
import altair as alt
from collections import defaultdict

from utils.calculs import (
    formater_semaine, format_allure, pretty_allure, calc_allure,
    parse_blocs, calcul_imc, minutes_to_hmin, regrouper_zone, format_blocs,formater_semaine,
    extraire_date_lundi, evolution_pct, generer_identifiant
)

# Fichiers CSV utilisés
ATHLETES_FILE = "data/athletes.csv"
SEANCES_STRUCT_FILE = "data/seances_struct.csv"
ASSIGN_FILE = "data/assignments.csv"
FEEDBACKS_FILE = "data/feedbacks.csv"
ATHLETES_HISTO_FILE = "data/athletes_historique.csv"
USERS_FILE = "data/users.csv"

# --- Fonctions de chargement des données ---
@st.cache_data
def load_feedbacks(file_path):
    df = pd.read_csv(file_path)
    df.rename(columns={
        "Athlete": "athlete",
        "Seance": "seance",
        "Semaine": "week",
        "Date seance": "date",
        "Effectuee": "done",
        "RPE": "rpe",
        "Commentaire": "comment"
    }, inplace=True)
    df["date"] = pd.to_datetime(df["date"])
    df["done"] = df["done"].astype(bool)
    df["week"] = df["week"].astype(int)
    return df

@st.cache_data
def load_seances_struct(file_path):
    df = pd.read_csv(file_path)
    df.rename(columns={
        "Nom": "seance",
        "Blocs": "blocs",
        "Charge totale": "charge_total",
        "Volume total": "volume_total"
    }, inplace=True)
    return df

def page_coach():
    # --- PAGE CREATION ET GESTION DES ATHLETES ---
    def page_gestion_athletes():
        st.header("👥 Gestion des athlètes")

        athletes = load_csv(ATHLETES_FILE, [
            "Nom", "Sexe", "Amenorrhee", "Date de naissance", "Sports", "Objectif",
            "Record 5km", "Record 10km", "Record Semi", "Record Marathon",
            "Allure 5km", "Allure 10km", "Allure Semi", "Allure Marathon"
        ])

        if not athletes.empty:
            st.subheader("📋 Liste des athlètes")
            df_aff = athletes.copy()
            for col in ["Allure 5km", "Allure 10km", "Allure Semi", "Allure Marathon"]:
                df_aff[col] = df_aff[col].apply(format_allure)
            for col in ["Record 5km", "Record 10km", "Record Semi", "Record Marathon"]:
                df_aff[col] = df_aff[col].apply(minutes_to_hmin)
            st.dataframe(df_aff)

            athlete_to_remove = st.selectbox("Sélectionner un athlète à supprimer", athletes["Nom"])
            if st.button("❌ Supprimer l'athlète"):
                # Suppression dans athletes.csv
                athletes = athletes[athletes["Nom"] != athlete_to_remove]
                save_csv(athletes, ATHLETES_FILE)

                # Suppression dans users.csv uniquement si rôle == 'athlete'
                users = load_csv("data/users.csv", ["Nom", "Mot de passe", "Role"])
                users = users[~((users["Nom"] == athlete_to_remove) & (users["Role"] == "athlete"))]
                save_csv(users, "data/users.csv")

                st.success(f"Athlète {athlete_to_remove} supprimé des fichiers athletes.csv et users.csv.")
                st.rerun()
        else:
            st.info("Aucun athlète enregistré pour l'instant.")

        with st.form("ajout_athlete"):
            nom = st.text_input("Nom")
            sexe = st.selectbox("Sexe", ["Homme", "Femme"])
            amenorrhee = st.checkbox("Aménorrhée (pas de cycle menstruel)", value=False)
            naissance = st.date_input(
                "Date de naissance",
                value=date(1990, 1, 1),
                min_value=date(1900, 1, 1),
                max_value=date.today()
            )
            taille_cm = st.number_input("Taille (cm)", min_value=100, max_value=250, step=1)
            poids_kg = st.number_input("Poids (kg)", min_value=30.0, max_value=200.0, step=0.1)
            sports = st.text_input("Sports pratiqués à côté (libre)")
            objectif = st.text_input("Objectif du plan")
            
            # Saisie des records et conversion pour les alllures 
            st.markdown("### Records (heures et minutes)")
            col5_1, col5_2 = st.columns(2)
            with col5_1:
                h_5k = st.number_input("5 km – heures", min_value=0, max_value=1, step=0, key="h_5k")
            with col5_2:
                min_5k = st.number_input("5 km – minutes", min_value=0, max_value=59, step=1, key="min_5k")
            record_5 = h_5k * 60 + min_5k

            col10_1, col10_2 = st.columns(2)
            with col10_1:
                h_10k = st.number_input("10 km – heures", min_value=0, max_value=2, step=0, key="h_10k")
            with col10_2:
                min_10k = st.number_input("10 km – minutes", min_value=0, max_value=59, step=1, key="min_10k")
            record_10 = h_10k * 60 + min_10k

            colsemi_1, colsemi_2 = st.columns(2)
            with colsemi_1:
                h_semi = st.number_input("Semi-marathon – heures", min_value=0, max_value=5, step=0, key="h_semi")
            with colsemi_2:
                min_semi = st.number_input("Semi-marathon – minutes", min_value=0, max_value=59, step=1, key="min_semi")
            record_semi = h_semi * 60 + min_semi

            colmar_1, colmar_2 = st.columns(2)
            with colmar_1:
                h_marathon = st.number_input("Marathon – heures", min_value=0, max_value=10, step=0, key="h_marathon")
            with colmar_2:
                min_marathon = st.number_input("Marathon – minutes", min_value=0, max_value=59, step=1, key="min_marathon")
            record_marathon = h_marathon * 60 + min_marathon

            mdp = st.text_input("Mot de passe (pour connexion athlète)", type="password")
            submit = st.form_submit_button("Ajouter l'athlète")

            if submit and nom.strip() != "":
                if nom in athletes["Nom"].values:
                    st.warning("Cet athlète existe déjà.")
                else:
                    age = int((date.today() - naissance).days / 365.25)
                    imc = calcul_imc(poids_kg, taille_cm)
                    new_row = pd.DataFrame([{
                        "Nom": nom,
                        "Sexe": sexe,
                        "Amenorrhee": amenorrhee,
                        "Date de naissance": naissance,
                        "Age": age,
                        "Taille (cm)": taille_cm,
                        "Poids (kg)": poids_kg,
                        "IMC": imc,
                        "Sports": sports,
                        "Objectif": objectif,
                        "Record 5km": record_5,
                        "Record 10km": record_10,
                        "Record Semi": record_semi,
                        "Record Marathon": record_marathon,
                        "Allure 5km": calc_allure(5, record_5),
                        "Allure 10km": calc_allure(10, record_10),
                        "Allure Semi": calc_allure(21.097, record_semi),
                        "Allure Marathon": calc_allure(42.195, record_marathon),
                    }])
                    athletes = pd.concat([athletes, new_row], ignore_index=True)
                    save_csv(athletes, ATHLETES_FILE)

                    users = load_csv("data/users.csv", ["Nom", "Mot de passe", "Role"])
                    if nom not in users["Nom"].values:
                        identifiant = generer_identifiant(nom)
                        
                        new_user = pd.DataFrame([{
                            "Nom": nom,
                            "Mot de passe": mdp,
                            "Role": "athlete",
                            "Identifiant": identifiant
                        }])
                        
                        users = pd.concat([users, new_user], ignore_index=True)
                        save_csv(users, "data/users.csv")

                        st.success(f"Athlète {nom} ajouté ✅ (identifiant : {identifiant})")
                        time.sleep(2)
                        st.rerun()
        
    # --- PAGE CREATION SEANCES STRUCTUREES PAR BLOCS ---
    def page_creation_seances():
        st.header("📐 Créer une séance structurée (par blocs)")

        # Chargement des séances existantes
        seances_struct = load_csv(SEANCES_STRUCT_FILE, ["Nom", "Blocs", "Charge totale", "Volume total"])

        # Création de blocs
        if "blocs_temp" not in st.session_state:
            st.session_state["blocs_temp"] = []

        with st.form("ajout_bloc"):
            nom_seance = st.text_input("Nom de la séance")
            bloc_type = st.selectbox("Type de bloc", ["Échauffement", "Intervalles", "Récupération", "Allure continue", "Autre"])
            duree = st.number_input("Durée (min par répétition)", min_value=1, max_value=240, value=5)
            repetitions = st.number_input("Répétitions", min_value=1, max_value=30, value=1)
            zone = st.selectbox("Zone", ["Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5", "Zone 6", 'Zone 7'])
            description = st.text_input("Description (facultatif)")
            add_bloc = st.form_submit_button("Ajouter le bloc")

            if add_bloc:
                bloc = {
                    "Nom de la seance": nom_seance,
                    "Type": bloc_type,
                    "Durée": duree,
                    "Répétitions": repetitions,
                    "Zone": zone,
                    "Description": description
                }
                st.session_state["blocs_temp"].append(bloc)
                st.success("Bloc ajouté ✅")

        if st.session_state["blocs_temp"]:
            st.subheader("🧩 Blocs en cours de création")
            df_blocs = pd.DataFrame(st.session_state["blocs_temp"])

            # Extraction du numéro de zone
            df_blocs["Zone_num"] = df_blocs["Zone"].str.extract(r"(\d)").astype(int)

            # Coefficients personnalisés par zone
            coefficients_zone = {
                1: 1,
                2: 2,
                3: 3,
                4: 4,
                5: 5,
                6: 6,
                7: 7,
            }

            df_blocs["Coeff zone"] = df_blocs["Zone_num"].map(coefficients_zone)
            
            # Format coefficient à 2 décimales
            df_blocs["Coeff zone"] = df_blocs["Coeff zone"].map(lambda x: f"{x:.2f}")

            # Calcul charge, arrondi à l'entier
            df_blocs["Charge"] = (df_blocs["Durée"] * df_blocs["Répétitions"] * df_blocs["Coeff zone"].astype(float)).round().astype(int)
            df_blocs["Volume total"] = df_blocs["Durée"] * df_blocs["Répétitions"]

            # Coloration selon la zone
            zone_couleurs = {
                "1": "#757779FF",
                "2": "#2D93D7",
                "3": "#64AC37",
                "4": "#D08E01",
                "5": "#C81906",
                "6": "#680D03", 
                "7": "#68038A" 
            }

            def surligner_zone(val):
                num = re.search(r"\d", val)
                if num:
                    return f"background-color: {zone_couleurs.get(num.group(), '')}; text-align: center"
                return ""

            st.dataframe(
                df_blocs[["Type", "Durée", "Répétitions", "Zone", "Coeff zone", "Charge", "Description"]]
                .style.applymap(surligner_zone, subset=["Zone"]),
                use_container_width=True,
                hide_index=True
            )

            st.metric("Volume total (min)", int(df_blocs["Volume total"].sum()))
            st.metric("Charge totale", int(df_blocs["Charge"].sum()))

            # Enregistrement de la séance complète
            if st.button("✅ Enregistrer la séance complète"):
                if nom_seance.strip() == "":
                    st.warning("Veuillez entrer un nom de séance.")
                else:
                    seance_dict = {
                        "Nom": nom_seance,
                        "Blocs": json.dumps(df_blocs[["Type", "Durée", "Répétitions", "Zone", "Zone_num", "Description"]].to_dict(orient="records")),
                        "Charge totale": int(df_blocs["Charge"].sum()),
                        "Volume total": df_blocs["Volume total"].sum()
                    }
                    seances_struct = pd.concat([seances_struct, pd.DataFrame([seance_dict])], ignore_index=True)
                    save_csv(seances_struct, SEANCES_STRUCT_FILE)
                    st.success(f"Seance '{nom_seance}' enregistrée ✅")
                    st.session_state["blocs_temp"] = []
                    st.rerun()

        else:
            st.info("Aucun bloc ajouté pour l’instant.")

        # Affichage des séances existantes 
        st.markdown("### 📋 Séances existantes")

        seances = load_csv(SEANCES_STRUCT_FILE)

        if seances.empty:
            st.info("Aucune séance enregistrée.")
            return

                # ----------- 🔍 Filtres dynamiques ----------- #
        with st.expander("🔎 Filtres"):
            # Filtrer par nom de séance
            noms = sorted(seances["Nom"].dropna().unique())
            nom_filtre = st.multiselect("Nom de séance", options=noms, default=noms)

            # Barre de recherche texte
            recherche_texte = st.text_input("Recherche (nom ou description contient...)")

            # Filtrer par durée
            if "Volume total" in seances.columns:
                min_duree = int(seances["Volume total"].min())
                max_duree = int(seances["Volume total"].max())
                if min_duree == max_duree:
                    max_duree += 1  # pour éviter une erreur de slider
            else:
                min_duree, max_duree = 0, 180

            duree_range = st.slider("Durée (minutes)", min_value=min_duree, max_value=max_duree,
                                    value=(min_duree, max_duree))

            # Filtrer par charge
            if "Charge totale" in seances.columns:
                min_charge = int(seances["Charge totale"].min())
                max_charge = int(seances["Charge totale"].max())
                if min_charge == max_charge:
                    max_charge += 1
            else:
                min_charge, max_charge = 0, 1000

            charge_range = st.slider("Charge", min_value=min_charge, max_value=max_charge,
                                    value=(min_charge, max_charge))

        # ----------- 🧮 Application des filtres ----------- #
        df_filtre = seances.copy()

        # Nom de séance
        df_filtre = df_filtre[df_filtre["Nom"].isin(nom_filtre)]

        # Recherche texte libre
        if recherche_texte.strip() != "":
            recherche_texte = recherche_texte.lower()
            df_filtre = df_filtre[df_filtre["Nom"].str.lower().str.contains(recherche_texte) |
                                df_filtre.apply(lambda row: recherche_texte in str(row).lower(), axis=1)]

        # Durée
        df_filtre = df_filtre[(df_filtre["Volume total"] >= duree_range[0]) &
                            (df_filtre["Volume total"] <= duree_range[1])]

        # Charge
        df_filtre = df_filtre[(df_filtre["Charge totale"] >= charge_range[0]) &
                            (df_filtre["Charge totale"] <= charge_range[1])]

        # ----------- 📋 Affichage ----------- #
        st.dataframe(df_filtre, use_container_width=True,hide_index=True)

        # Suppression d'une séance
        if not seances_struct.empty:
            st.subheader("✏️ Supprimer une séance")
            nom_seance_select = st.selectbox("Sélectionner une séance à supprimer", seances_struct["Nom"])
            if st.button("🗑 Supprimer la séance"):
                seances_struct = seances_struct[seances_struct["Nom"] != nom_seance_select]
                save_csv(seances_struct, SEANCES_STRUCT_FILE)
                st.success(f"Seance supprimée.")
                st.rerun()
                
    # --- PAGE ASSIGNATION SEANCES ---
    def page_assignation():
            # --- Notification séances hors plan ---
        try:
            extras = pd.read_csv("extras_seances.csv")
        except FileNotFoundError:
            extras = pd.DataFrame(columns=["Athlete", "Date", "Description"])

        if not extras.empty:
            st.markdown("## ⚠️ Séances hors plan signalées par les athlètes")

            derniers = extras.sort_values("Date", ascending=False).head(10)
            for _, row in derniers.iterrows():
                desc_court = row['Description'][:100] + ("..." if len(row['Description']) > 100 else "")
                st.markdown(f"- **{row['Date']}** - {row['Athlete']} : {desc_court}")

            if st.button("Marquer toutes comme lues"):
                pd.DataFrame(columns=extras.columns).to_csv("extras_seances.csv", index=False)
                st.success("Notifications hors plan vidées.")
                st.rerun()
        else:
            st.info("Aucune séance hors plan signalée pour le moment.")
        
        
        st.header("👥 Profil de l'athlète et assignation des séances")

        # Chargement des fichiers
        athletes = load_csv(ATHLETES_FILE)
        seances_struct = load_csv(SEANCES_STRUCT_FILE)
        assignments = load_csv(ASSIGN_FILE, ["Athlete", "Seance", "Semaine"])

        if athletes.empty or seances_struct.empty:
            st.warning("⚠️ Ajoutez au moins un athlète et une séance avant d’assigner.")
            return

        # 👉 Sélection d’un athlète
        athlete_select = st.selectbox("👤 Choisir un athlète", athletes["Nom"])
        ath = athletes[athletes["Nom"] == athlete_select].iloc[0]

        # 🪪 Affichage des informations de l'athlète séléctionné 
        st.markdown("### 🪪 Informations personnelles")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"👤 **Nom :** {ath.get('Nom', '—')}")
            st.markdown(f"⚧️ **Sexe :** {ath.get('Sexe', '—')}")
            try:
                naissance = datetime.strptime(str(ath.get("Date de naissance", "")), "%Y-%m-%d").date()
                age = int((date.today() - naissance).days / 365.25)
                st.markdown(f"🎂 **Âge :** {age} ans")
            except Exception:
                st.markdown("🎂 **Âge :** —")

        with col2:
            st.markdown(f"📏 **Taille :** {ath.get('Taille (cm)', '—')} cm")
            st.markdown(f"⚖️ **Poids :** {ath.get('Poids (kg)', '—')} kg")
            st.markdown(f"🧮 **IMC :** {ath.get('IMC', '—')}")

        with col3:
            st.markdown(f"📆 **Naissance :** {ath.get('Date de naissance', '—')}")
            st.markdown(f"🏃 **Sports :** {ath.get('Sports', '—')}")
            st.markdown(f"🎯 **Objectif :** {ath.get('Objectif', '—')}")

        st.markdown("### 🏅 Records — allures")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"🏃 **5 km** : {minutes_to_hmin(ath['Record 5km'])} — {pretty_allure(ath['Allure 5km'])}/km")
            st.markdown(f"🏃 **10 km** : {minutes_to_hmin(ath['Record 10km'])} — {pretty_allure(ath['Allure 10km'])}/km")
        with col2:
            st.markdown(f"🏃 **Semi** : {minutes_to_hmin(ath['Record Semi'])} — {pretty_allure(ath['Allure Semi'])}/km")
            st.markdown(f"🏃 **Marathon** : {minutes_to_hmin(ath['Record Marathon'])} — {pretty_allure(ath['Allure Marathon'])}/km")

        # Assignation de séances pour l'athlète selectionné  
        st.markdown("### 🗓️ Assignation des séances")
        seance_select = st.selectbox("📋 Choisir une séance", seances_struct["Nom"])
        annee = st.number_input("📆 Année", value=datetime.today().year, min_value=2020, max_value=2100)
        num_semaine = st.number_input(
            "📅 Numéro de semaine (1 à 53)", min_value=1, max_value=53, value=datetime.today().isocalendar()[1]
        )

        try:
            semaine = datetime.fromisocalendar(annee, num_semaine, 1)
            semaine_formatee = formater_semaine(semaine)
        except ValueError:
            st.error("⛔ Semaine invalide pour cette année.")
            return

        if st.button("✅ Assigner la séance"):
            already_exists = (
                (assignments["Athlete"] == athlete_select) &
                (assignments["Seance"] == seance_select) &
                (assignments["Semaine"] == semaine_formatee)
            ).any()

            if already_exists:
                st.warning("⚠️ Cette assignation existe déjà.")
            else:
                new_assign = {
                    "Athlete": athlete_select,
                    "Seance": seance_select,
                    "Semaine": semaine_formatee
                }
                assignments = pd.concat([assignments, pd.DataFrame([new_assign])], ignore_index=True)
                save_csv(assignments, ASSIGN_FILE)
                st.success("Séance assignée avec succès 🎯")
                st.rerun()

        # Visualisation des charges planifiées pour l'athlète selectionné 
        st.markdown("### 📊 Evolution de la charge externe planifiée")

        df_assign = assignments[assignments["Athlete"] == athlete_select].copy()
        if df_assign.empty:
            st.info("Aucune séance assignée à cet athlète.")
        else:
            seances_info = seances_struct[["Nom", "Charge totale", "Volume total"]]
            df_assign = df_assign.merge(seances_info, left_on="Seance", right_on="Nom", how="left").dropna(subset=["Charge totale", "Volume total"])

            df_assign["Charge totale"] = pd.to_numeric(df_assign["Charge totale"], errors="coerce")
            df_assign["Volume total"] = pd.to_numeric(df_assign["Volume total"], errors="coerce")
            df_assign["Date_lundi"] = df_assign["Semaine"].apply(extraire_date_lundi)
            df_assign = df_assign.dropna(subset=["Date_lundi"])
            df_assign = df_assign[df_assign["Date_lundi"] >= datetime.today() - timedelta(weeks=4)]

            df_semaines = df_assign.groupby("Semaine").agg({
                "Charge totale": "sum",
                "Volume total": "sum",
                "Seance": "count"
            }).reset_index()

            df_semaines["Charge moyenne"] = df_semaines.apply(
                lambda row: row["Charge totale"] / row["Seance"] if row["Seance"] > 0 else 0, axis=1
            )

            chart = alt.Chart(df_semaines).mark_bar(color="#4B4B4B").encode(
                x=alt.X("Semaine", title="Semaine", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Charge totale", title="Charge externe", axis=alt.Axis(tickCount=15), scale=alt.Scale(nice=True)),
                tooltip=["Semaine", "Charge totale"]
            ).properties(height=200)
            st.altair_chart(chart, use_container_width=True)

            # Chargement feedbacks et calcul séances effectuées
            feedbacks = load_csv(FEEDBACKS_FILE)
            feedbacks = feedbacks[feedbacks["Athlete"] == athlete_select]
            feedbacks["Semaine"] = feedbacks["Date seance"].apply(
                lambda d: formater_semaine(pd.to_datetime(d)) if pd.notnull(d) else None
            )
            feedbacks = feedbacks[feedbacks["Effectuee"] == "Oui"]

            effectuees = feedbacks.groupby("Semaine")["Seance"].count().rename("Séances effectuées")
            df_semaines = df_semaines.set_index("Semaine").join(effectuees, how="left").fillna(0)
            df_semaines["Séances programmées"] = df_semaines["Seance"]
            df_semaines["Charge moyenne"] = df_semaines["Charge totale"] / df_semaines["Séances programmées"]
            df_semaines = df_semaines.sort_index()

            # Histogramme de l'évolution du temps passé par zone sur les 6 dernières semaines 
            st.markdown("### 📈 Évolution sur 6 semaines — temps passé par zone")

            zone_couleurs = {
                "1": "gray",
                "2": "#2D93D7",
                "3": "#64AC37",
                "4": "#D08E01",
                "5": "#C81906",
                "6": "#680D03", 
                "7": "#68038A" 
            }

            try:
                date_ref = datetime.fromisocalendar(annee, num_semaine, 1)
            except Exception:
                st.info("Impossible de générer le graphique sur 6 semaines.")
                date_ref = None

            if date_ref:
                durees_par_semaine = defaultdict(lambda: {str(z): 0 for z in range(1, 8)})

                for delta in range(5, -1, -1):  # 6 dernières semaines, la plus ancienne à gauche
                    semaine_dt = date_ref - timedelta(weeks=delta)
                    semaine_str = formater_semaine(semaine_dt)

                    df_assign_zone = assignments[
                        (assignments["Athlete"] == athlete_select) &
                        (assignments["Semaine"] == semaine_str)
                    ]

                    for _, assign in df_assign_zone.iterrows():
                        nom_seance = assign["Seance"]
                        seance_row = seances_struct[seances_struct["Nom"] == nom_seance]
                        if seance_row.empty:
                            continue

                        try:
                            blocs = json.loads(seance_row["Blocs"].values[0])
                        except Exception:
                            continue

                        for bloc in blocs:
                            zone_num = bloc.get("Zone_num")
                            if zone_num is None:
                                zone = bloc.get("Zone", "")
                                match = re.search(r"\d", zone)
                                zone_num = int(match.group()) if match else None

                            try:
                                zone_num = str(int(zone_num))  # Converti en string ici
                                duree = float(bloc.get("Durée", 0))
                                repetitions = int(bloc.get("Répétitions", 1))
                                total_duree = duree * repetitions

                                if zone_num in durees_par_semaine[semaine_str]:
                                    durees_par_semaine[semaine_str][zone_num] += total_duree
                            except Exception:
                                continue

                if not durees_par_semaine:
                    st.info("Aucune donnée sur les 6 dernières semaines.")
                else:
                    df_cumule = pd.DataFrame(durees_par_semaine).T.reset_index()
                    df_cumule = df_cumule.rename(columns={"index": "Semaine"})
                    df_cumule = df_cumule.sort_values(by="Semaine")
                    df_melt = df_cumule.melt(id_vars="Semaine", var_name="Zone", value_name="Durée (min)")
                    # Zone est déjà string

                    fig_bar = px.bar(
                        df_melt,
                        x="Semaine",
                        y="Durée (min)",
                        color="Zone",
                        text_auto=True,
                        color_discrete_map=zone_couleurs,
                        title="Histogramme empilé - Temps passé par zone (6 dernières semaines)"
                    )
                    fig_bar.update_layout(
                        barmode="stack",
                        yaxis_title="Temps cumulé (min)",
                        xaxis_title="Semaine",
                        legend_title="Zone",
                        height=350
                    )

                    st.plotly_chart(fig_bar, use_container_width=True)

        #VISUALISATION DES SEANCES ASSIGNEES + SUPPRESSION POSSIBLE
        st.markdown(f"### 📅 Assignations existantes pour {athlete_select}")

        # Choix de tri en ligne
        col_tri1, col_tri2 = st.columns([1, 1])
        with col_tri1:
            tri_seance = st.button("🔤 Trier par Séance")
        with col_tri2:
            tri_semaine = st.button("📅 Trier par Semaine")

        # Filtrer et trier
        df_assign = assignments[assignments["Athlete"] == athlete_select]

        if df_assign.empty:
            st.info("Aucune séance assignée.")
        else:
            if tri_seance:
                tri_colonne = "Seance"
            else:
                tri_colonne = "Semaine"  # Par défaut ou si "Trier par Semaine" cliqué

            df_assign = df_assign.sort_values(by=tri_colonne).reset_index(drop=True)

            for idx, row in df_assign.iterrows():
                with st.container():
                    st.markdown(
                        """
                        <div style="background-color:#f0f2f6; padding:5px; border-radius:5px; margin-bottom:5px;">
                        """,
                        unsafe_allow_html=True
                    )

                    col1, col2, col3 = st.columns([4, 4, 2])
                    col1.markdown(f"**Séance :** {row['Seance']}")
                    col2.markdown(f"**Semaine :** {row['Semaine']}")
                    with col3:
                        if st.button("🗑️", key=f"del_{idx}"):
                            idx_global = assignments[(assignments["Athlete"] == athlete_select) &
                                                    (assignments["Seance"] == row["Seance"]) &
                                                    (assignments["Semaine"] == row["Semaine"])].index[0]
                            assignments.drop(idx_global, inplace=True)
                            assignments.reset_index(drop=True, inplace=True)
                            save_csv(assignments, ASSIGN_FILE)
                            st.success("Assignation supprimée")
                            st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)

    # --- MAIN ---
    def main():
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Aller à", ["Gestion Athlètes", "Profil Athlète"])

        if page == "Gestion Athlètes":
            page_gestion_athletes()
    if __name__ == "__main__":
        main()
    
    page = st.sidebar.selectbox("Menu", [
        "Gestion des athlètes",
        "Création séances",
        "Profil et assignation des séances"
    ])

    if page == "Gestion des athlètes":
        page_gestion_athletes()
    elif page == "Création séances":
        page_creation_seances()
    elif page == "Profil et assignation des séances":
        page_assignation()