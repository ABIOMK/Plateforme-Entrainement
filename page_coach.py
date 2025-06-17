import streamlit as st
import pandas as pd
import os
import ast
import json
import re
from datetime import date,datetime, timedelta
from utils.io import load_csv, save_csv
import ast
import altair as alt

# Fichiers CSV utilisés
ATHLETES_FILE = "data/athletes.csv"
SEANCES_STRUCT_FILE = "data/seances_struct.csv"
#SEANCES_FILE = "data/seances.csv"
ASSIGN_FILE = "data/assignments.csv"
FEEDBACKS_FILE = "data/feedbacks.csv"

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

# --- Fonctions utilitaires ---
def formater_semaine(date_obj):
    semaine_num = f"{date_obj.isocalendar()[1]:02d}"
    lundi = date_obj.strftime("%d/%m")
    return f"S{semaine_num} - {lundi}"

def format_allure(min_float):
    if pd.isna(min_float) or min_float is None:
        return ""
    minutes = int(min_float)
    secondes = int(round((min_float - minutes) * 60))
    return f"{minutes:02d}:{secondes:02d}"

def pretty_allure(val):
    if pd.isna(val) or val is None:
        return "N/A"
    m = int(val)
    s = int(round((val - m) * 60))
    return f"{m:02d}:{s:02d} min/km"

def calc_allure(dist_km, t_min):
    return round(t_min / dist_km, 2) if t_min > 0 else None

def parse_blocs(blocs_str):
    if isinstance(blocs_str, str):
        try:
            return ast.literal_eval(blocs_str)
        except:
            return []
    return blocs_str

def calcul_imc(poids, taille_cm):
    taille_m = taille_cm / 100
    if taille_m <= 0:
        return None
    return round(poids / (taille_m ** 2), 1)

def minutes_to_hmin(minutes):
    if pd.isna(minutes) or minutes == 0:
        return "—"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h{m:02d}min" if h > 0 else f"{m}min"

def page_coach():
    # --- PAGE GESTION ATHLETES ---
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
                        new_user = pd.DataFrame([{
                            "Nom": nom,
                            "Mot de passe": mdp,
                            "Role": "athlete"
                        }])
                        users = pd.concat([users, new_user], ignore_index=True)
                        save_csv(users, "data/users.csv")

                    st.success(f"Athlète {nom} ajouté ✅")
                    st.rerun()

    # --- PAGE PROFIL ATHLETE ---
    def page_profil_athlete():
        st.header("👤 Profil athlète")

        df = load_csv(ATHLETES_FILE)
        if df.empty:
            st.warning("Aucun athlète enregistré.")
            return

        # 👉 Sélection d’un athlète depuis la liste
        nom_select = st.selectbox("Choisir un athlète", df["Nom"].unique())
        ath = df[df["Nom"] == nom_select].iloc[0]

        st.markdown("### 🪪 Informations personnelles")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"👤 **Nom :** {ath.get('Nom', '—')}")
            st.markdown(f"⚧️ **Sexe :** {ath.get('Sexe', '—')}")

            try:
                naissance = datetime.strptime(str(ath.get("Date de naissance", "")), "%Y-%m-%d").date()
                age = int((date.today() - naissance).days / 365.25)
                st.markdown(f"🎂 **Âge :** {age} ans")
            except:
                st.markdown("🎂 **Âge :** —")

        with col2:
            st.markdown(f"📏 **Taille :** {ath.get('Taille (cm)', '—')} cm")
            st.markdown(f"⚖️ **Poids :** {ath.get('Poids (kg)', '—')} kg")
            st.markdown(f"🧮 **IMC :** {ath.get('IMC', '—')}")

        with col3:
            st.markdown(f"📆 **Naissance :** {ath.get('Date de naissance', '—')}")
            st.markdown(f"🏃 **Sports :** {ath.get('Sports', '—')}")
            st.markdown(f"🎯 **Objectif :** {ath.get('Objectif', '—')}")


        st.markdown("### 🏅 Records et allures")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"🏃 **5 km** : {minutes_to_hmin(ath['Record 5km'])} — {pretty_allure(ath['Allure 5km'])}/km")
            st.markdown(f"🏃 **10 km** : {minutes_to_hmin(ath['Record 10km'])} — {pretty_allure(ath['Allure 10km'])}/km")

        with col2:
            st.markdown(f"🏃 **Semi** : {minutes_to_hmin(ath['Record Semi'])} — {pretty_allure(ath['Allure Semi'])}/km")
            st.markdown(f"🏃 **Marathon** : {minutes_to_hmin(ath['Record Marathon'])} — {pretty_allure(ath['Allure Marathon'])}/km")

        # --- Affichage séances assignées ---
        st.markdown("### Séances assignées")
        assignments = load_csv(ASSIGN_FILE)
        seances = load_csv(SEANCES_STRUCT_FILE)

        seances_ath = assignments[assignments["Athlete"] == nom_select]

        if seances_ath.empty:
            st.info("Aucune séance assignée à cet athlète.")
        else:
            seances_ath["Semaine"] = pd.to_datetime(seances_ath["Semaine"], errors="coerce")

            # Filtrer sur les 4 dernières semaines
            date_limite = datetime.today() - timedelta(weeks=4)
            seances_ath_recente = seances_ath[seances_ath["Semaine"] >= date_limite]

            if seances_ath_recente.empty:
                st.info("Aucune séance assignée sur les 4 dernières semaines.")
            else:
                # Ajout d’une colonne affichée pour le format Semaine
                seances_ath_recente["Semaine affichée"] = seances_ath_recente["Semaine"].apply(formater_semaine)
                df_aff = seances_ath_recente[["Semaine affichée", "Seance"]].sort_values("Semaine affichée")
                st.dataframe(df_aff, use_container_width=True, hide_index=True)
        
        # --- 🔄 Feedback de l’athlète ---
        st.markdown("### 🗣️ Feedbacks de l’athlète")
        feedbacks = load_csv(FEEDBACKS_FILE)
        
        # feedbacks["Semaine"] = pd.to_datetime(feedbacks["Semaine"], errors="coerce")  # à réactiver si nécessaire plus tard
        if feedbacks.empty or "Athlete" not in feedbacks.columns:
            st.info("Aucun feedback enregistré.")
        else:
            feedback_ath = feedbacks[feedbacks["Athlete"] == nom_select]

            if feedback_ath.empty:
                st.info("Cet athlète n’a encore donné aucun feedback.")
            else:
                # Conversion en datetime pour filtrage
                feedback_ath["Date seance"] = pd.to_datetime(feedback_ath["Date seance"], errors="coerce")

                # Date limite = aujourd’hui - 28 jours
                date_limite = datetime.today() - timedelta(days=28)

                # Filtrage des feedbacks récents
                feedback_ath = feedback_ath[feedback_ath["Date seance"] >= date_limite]

                if feedback_ath.empty:
                    st.info("Aucun feedback sur les 4 dernières semaines.")
                else:
                    feedback_ath = feedback_ath.sort_values(by="Date seance", ascending=False)
                    # Re-formatage date en JJ/MM/AAAA
                    feedback_ath["Date seance"] = feedback_ath["Date seance"].dt.strftime("%d/%m/%Y")

                    # Détection du suivi menstruel à afficher
                    sexe = str(ath.get("Sexe", "")).lower()
                    amenorrhee = str(ath.get("Aménorrhée", "Non")).strip().lower()
                    afficher_cycle = sexe == "femme" and amenorrhee != "oui"

                    # Renommage des colonnes avec icônes
                    feedback_ath = feedback_ath.rename(columns={
                        "Seance": "🏃 Séance",
                        "Date seance": "📅 Date",
                        "Effectuee": "✅ Effectuée",
                        "RPE": "📊 RPE",
                        "Glucides (g/h)": "🍌 Glucides (g/h)",
                        "Commentaire": "💬 Commentaire",
                        "Phase menstruelle": "🌸 Phase",
                        "Symptomes": "😖 Symptômes"
                    })

                    colonnes_aff = ["📅 Date", "🏃 Séance", "✅ Effectuée", "📊 RPE","🍌 Glucides (g/h)", "💬 Commentaire"]
                    if afficher_cycle:
                        colonnes_aff += ["🌸 Phase", "😖 Symptômes"]

                    st.dataframe(feedback_ath[colonnes_aff], use_container_width=True, hide_index=True)
    
    # --- PAGE CREATION SEANCES STRUCTUREES ---
    def page_creation_seances():
        st.header("📐 Créer une séance structurée (par blocs)")

        # Chargement des séances existantes
        seances_struct = load_csv(SEANCES_STRUCT_FILE, ["Nom", "Blocs", "Charge totale", "Volume total"])

        def format_blocs(blocs):
            if not blocs or isinstance(blocs, float):
                return ""

            if isinstance(blocs, str):
                try:
                    blocs = ast.literal_eval(blocs)
                except (ValueError, SyntaxError):
                    return ""

            lines = []
            for b in blocs:
                repetitions = b.get('Répétitions', 1)
                duree = b.get('Durée', '')
                zone = b.get('Zone', '')
                bloc_type = b.get('Type', '')
                description = b.get('Description', '')

                ligne = f"{repetitions}× {duree}min {zone} [{bloc_type}]"
                if description:
                    ligne += f" - {description}"
                lines.append(ligne)
            return "\n".join(lines)

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
                "1": "#D6EAF8",
                "2": "#AED6F1",
                "3": "#F9E79F",
                "4": "#F5B7B1",
                "5": "#E74C3C"
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

            if st.button("✅ Enregistrer la séance complète"):
                if nom_seance.strip() == "":
                    st.warning("Veuillez entrer un nom de séance.")
                else:
                    seance_dict = {
                        "Nom": nom_seance,
                        "Blocs": json.dumps(df_blocs.to_dict(orient="records")),
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

        # ----------- ↕️ Tri utilisateur ----------- #
        colonnes_triables = [col for col in df_filtre.columns if df_filtre[col].dtype in [int, float, object]]
        colonne_tri = st.selectbox("Trier par :", options=colonnes_triables, index=0)
        ordre_croissant = st.checkbox("Ordre croissant", value=True)

        df_filtre = df_filtre.sort_values(by=colonne_tri, ascending=ordre_croissant)

        # ----------- 📋 Affichage ----------- #
        st.dataframe(df_filtre, use_container_width=True,hide_index=True)

        # Suppression d'une séance
        if not seances_struct.empty:
            st.subheader("✏️ Supprimer une séance")
            nom_seance_select = st.selectbox("Sélectionner une séance à supprimer", seances_struct["Nom"])
            if st.button("🗑 Supprimer la séance"):
                seances_struct = seances_struct[seances_struct["Nom"] != nom_seance_select]
                save_csv(seances_struct, SEANCES_STRUCT_FILE)
                st.success(f"Seance '{nom_seance_select}' supprimée.")
                st.rerun()
                
    # --- PAGE ASSIGNATION SEANCES ---
    def formater_semaine(date_obj):
        semaine_num = f"{date_obj.isocalendar()[1]:02d}"
        lundi = date_obj.strftime("%d/%m")
        return f"S{semaine_num} - {lundi}"

    def extraire_date_lundi(chaine_semaine):
        try:
            jour_mois = chaine_semaine.split(" - ")[1]
            jour, mois = map(int, jour_mois.split("/"))
            today = datetime.today()
            annee = today.year if mois >= today.month else today.year - 1
            return datetime.strptime(f"{jour_mois}/{annee}", "%d/%m/%Y")
        except Exception:
            return None

    def page_assignation():
        st.header("🗓️ Assigner une séance à un athlète")

        # Chargement des fichiers
        athletes = load_csv(ATHLETES_FILE)
        seances_struct = load_csv(SEANCES_STRUCT_FILE)
        assignments = load_csv(ASSIGN_FILE, ["Athlete", "Seance", "Semaine"])

        if athletes.empty or seances_struct.empty:
            st.warning("⚠️ Ajoutez au moins un athlète et une séance avant d’assigner.")
            return

        # Sélection athlète, séance, semaine
        athlete_select = st.selectbox("👤 Choisir un athlète", athletes["Nom"])
        seance_select = st.selectbox("📋 Choisir une séance", seances_struct["Nom"])
        annee = st.number_input("📆 Année", value=datetime.today().year, min_value=2020, max_value=2100)
        num_semaine = st.number_input("📅 Numéro de semaine (1 à 53)", min_value=1, max_value=53, value=datetime.today().isocalendar()[1])

        try:
            semaine = datetime.fromisocalendar(annee, num_semaine, 1)
        except ValueError:
            st.error("⛔ Semaine invalide pour cette année.")
            return
        
                # --- Bouton assignation ---
        if st.button("✅ Assigner la séance"):
            semaine_formatee = formater_semaine(semaine)
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

        # --- Visualisation des charges planifiées ---
        st.markdown("### 📊 Charge externe planifiée (4 dernières semaines)")

        df_assign = assignments[assignments["Athlete"] == athlete_select].copy()

        if df_assign.empty:
            st.info("Aucune séance assignée à cet athlète.")
        else:
            seances_info = seances_struct[["Nom", "Charge totale", "Volume total"]]
            df_assign = df_assign.merge(seances_info, left_on="Seance", right_on="Nom", how="left")
            df_assign = df_assign.dropna(subset=["Charge totale", "Volume total"])

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
                lambda row: row["Charge totale"] / row["Seance"] if row["Seance"] > 0 else 0,
                axis=1
            )

            chart = alt.Chart(df_semaines).mark_bar(color="#2CA02C").encode(
                x=alt.X("Semaine", title="Semaine"),
                y=alt.Y("Charge totale", title="Charge externe"),
                tooltip=["Semaine", "Charge totale"]
            ).properties(height=200)
            st.altair_chart(chart, use_container_width=True)

            def evolution_pct(df, col):
                if len(df) < 2:
                    return 0, 0
                last, prev = df.iloc[-1][col], df.iloc[-2][col]
                delta = last - prev
                pct = (delta / prev * 100) if prev else 0
                return delta, pct

            col1, col2, col3 = st.columns(3)
            metrics = [
                ("⚡️ **Charge totale**", "Charge totale", col1),
                ("⚖️ **Charge moyenne**", "Charge moyenne", col2),
                ("⏱️ **Volume total (min)**", "Volume total", col3),
            ]

            for label, col_name, col in metrics:
                delta, pct = evolution_pct(df_semaines, col_name)
                val = df_semaines.iloc[-1][col_name] if len(df_semaines) > 0 else 0
                delta_color = "inverse" if pct > 12 else "normal"
                col.metric(label, f"{val:.1f}", delta=f"{pct:+.1f} %", delta_color=delta_color)
                
        # --- Affichage & suppression assignations ---
        st.subheader("📅 Assignations existantes")

        if assignments.empty:
            st.info("Aucune assignation encore enregistrée.")
            return

        df_aff = assignments.copy()
        df_aff["Date_lundi"] = df_aff["Semaine"].apply(extraire_date_lundi)
        df_aff = df_aff[df_aff["Date_lundi"] >= datetime.today() - timedelta(weeks=4)]

        with col1:
            athlete_filter = st.selectbox("👤 Filtrer par athlète", ["Tous"] + sorted(df_aff["Athlete"].unique()), key="filtre_athlete_assign")
        with col2:
            seance_filter = st.selectbox("🏃 Filtrer par séance", ["Tous"] + sorted(df_aff["Seance"].unique()), key="filtre_seance_assign")
        with col3:
            semaine_filter = st.selectbox("📆 Filtrer par semaine", ["Toutes"] + sorted(df_aff["Semaine"].unique()), key="filtre_semaine_assign")

        if athlete_filter != "Tous":
            df_aff = df_aff[df_aff["Athlete"] == athlete_filter]
        if seance_filter != "Tous":
            df_aff = df_aff[df_aff["Seance"] == seance_filter]
        if semaine_filter != "Toutes":
            df_aff = df_aff[df_aff["Semaine"] == semaine_filter]

        df_aff = df_aff.sort_values(by=["Athlete", "Date_lundi"])
        colonnes_aff = [col for col in df_aff.columns if col != "Date_lundi"]
        st.dataframe(df_aff[colonnes_aff], use_container_width=True, hide_index=True)

        # --- Suppression assignation ---
        st.subheader("✏️ Supprimer une assignation")

        def format_assignation(i):
            ath = df_aff.at[i, "Athlete"]
            seance = df_aff.at[i, "Seance"]
            semaine = df_aff.at[i, "Semaine"]
            return f"{ath} - {seance} - {semaine}"

        if not df_aff.empty:
            ligne_sel = st.selectbox("Sélectionner une assignation", df_aff.index, format_func=format_assignation, key="selectbox_suppression_assign")

            if st.button("🗑 Supprimer cette assignation"):
                ligne = df_aff.loc[ligne_sel]
                mask = (
                    (assignments["Athlete"] == ligne["Athlete"]) &
                    (assignments["Seance"] == ligne["Seance"]) &
                    (assignments["Semaine"] == ligne["Semaine"])
                )
                assignments = assignments[~mask]
                save_csv(assignments, ASSIGN_FILE)
                st.success("Assignation supprimée.")
                st.rerun()

        
    # --- MAIN ---
    def main():
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Aller à", ["Gestion Athlètes", "Profil Athlète"])

        if page == "Gestion Athlètes":
            page_gestion_athletes()
        elif page == "Profil Athlète":
            page_profil_athlete()
    if __name__ == "__main__":
        main()
    
    
    page = st.sidebar.selectbox("Menu", [
        "Gestion des athlètes",
        "Profil athlète",
        "Création séances structurées",
        "Assignation séances"
    ])

    if page == "Gestion des athlètes":
        page_gestion_athletes()
    elif page == "Profil athlète":
        page_profil_athlete()
    elif page == "Création séances structurées":
        page_creation_seances()
    elif page == "Assignation séances":
        page_assignation()