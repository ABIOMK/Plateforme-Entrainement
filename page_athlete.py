import streamlit as st
import pandas as pd
import datetime as dt
import json
import calendar
import os
from utils.io import load_csv, save_csv
import plotly.express as px
import plotly.graph_objects as go

ASSIGN_FILE = "data/assignments.csv"
#SEANCES_FILE = "data/seances.csv"
ATHLETES_FILE = "data/athletes.csv"
SEANCES_STRUCT_FILE = "data/seances_struct.csv"
FEEDBACKS_FILE = "data/feedbacks.csv"

def afficher_stats_et_evolution(feedbacks, seances, nom_athlete, debut_entrainement):
    import plotly.express as px

    df_fb = feedbacks[feedbacks["Athlete"] == nom_athlete].copy()
    if df_fb.empty:
        st.info("Pas encore de feedbacks pour afficher les statistiques.")
        return

    df_fb["Date seance"] = pd.to_datetime(df_fb["Date seance"], errors='coerce')

    six_mois_avant = pd.Timestamp.now() - pd.DateOffset(months=6)
    start_date = max(pd.to_datetime(debut_entrainement), six_mois_avant)
    df_fb = df_fb[df_fb["Date seance"] >= start_date]

    # Fusion avec séances (pour la charge externe et volume)
    df_merge = df_fb.merge(
        seances[["Nom", "Charge totale", "Volume total"]],
        left_on="Seance", right_on="Nom",
        how="left"
    )

    # Garder uniquement les séances effectuées
    df_merge = df_merge[df_merge["Effectuee"] == "Oui"]

    # Nettoyage des valeurs manquantes
    df_merge = df_merge.dropna(subset=["Charge totale", "Volume total", "RPE"])

    # Ajout des charges internes (volume × RPE)
    df_merge["Charge_interne"] = df_merge["Volume total"] * df_merge["RPE"]

    # Ajout de la semaine ISO pour regroupement
    df_merge['annee_semaine'] = df_merge['Date seance'].dt.strftime('%Y-%U')

    # Calcul des agrégats par semaine
    stats_hebdo = df_merge.groupby('annee_semaine').agg(
        Charge_externe_totale=('Charge totale', 'sum'),
        Charge_externe_moyenne=('Charge totale', 'mean'),
        Volume_total=('Volume total', 'sum'),
        Charge_interne_totale=('Charge_interne', 'sum'),
        Charge_interne_moyenne=('Charge_interne', 'mean')
    ).reset_index()

    if stats_hebdo.empty:
        st.info("Pas assez de données pour afficher l'évolution.")
        return

    # Affichage dernière semaine
#    derniere = stats_hebdo.iloc[-1]
#    st.subheader("📊 Statistiques hebdomadaires (dernière semaine)")
#    st.write(f"⚡ Charge externe totale : {derniere['Charge_externe_totale']:.1f}")
#    st.write(f"📈 Charge externe moyenne : {derniere['Charge_externe_moyenne']:.1f}")
#    st.write(f"🕒 Volume total : {derniere['Volume_total']:.1f} min")
#    st.write(f"🧠 Charge interne totale : {derniere['Charge_interne_totale']:.1f}")
#    st.write(f"📉 Charge interne moyenne : {derniere['Charge_interne_moyenne']:.1f}")

    # Graphique 1 : Charges totales + volume
    fig1 = go.Figure()

    fig1.add_trace(go.Bar(
        x=stats_hebdo['annee_semaine'],
        y=stats_hebdo['Charge_externe_totale'],
        name="Charge externe totale",
        marker_color='rgba(99, 110, 250, 0.8)'
    ))
    fig1.add_trace(go.Bar(
        x=stats_hebdo['annee_semaine'],
        y=stats_hebdo['Charge_interne_totale'],
        name="Charge interne totale",
        marker_color='rgba(239, 85, 59, 0.8)'
    ))
    fig1.add_trace(go.Scatter(
        x=stats_hebdo['annee_semaine'],
        y=stats_hebdo['Volume_total'],
        name="Durée totale (min)",
        mode='lines+markers',
        yaxis='y2',
        line=dict(color='rgba(0, 204, 150, 0.9)', width=3)
    ))

    fig1.update_layout(
        title="📊 Évolution hebdomadaire – Charges totales & Volume",
        barmode='group',
        xaxis_title="Semaine",
        yaxis_title="Charge (totale)",
        yaxis2=dict(
            title="Durée (min)",
            overlaying='y',
            side='right'
        ),
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Graphique 2 : Charges moyennes + volume
    fig2 = go.Figure()

    fig2.add_trace(go.Bar(
        x=stats_hebdo['annee_semaine'],
        y=stats_hebdo['Charge_externe_moyenne'],
        name="Charge externe moyenne",
        marker_color='rgba(99, 110, 250, 0.6)'
    ))
    fig2.add_trace(go.Bar(
        x=stats_hebdo['annee_semaine'],
        y=stats_hebdo['Charge_interne_moyenne'],
        name="Charge interne moyenne",
        marker_color='rgba(239, 85, 59, 0.6)'
    ))
    fig2.add_trace(go.Scatter(
        x=stats_hebdo['annee_semaine'],
        y=stats_hebdo['Volume_total'],
        name="Durée totale (min)",
        mode='lines+markers',
        yaxis='y2',
        line=dict(color='rgba(0, 204, 150, 1)', width=3)
    ))

    fig2.update_layout(
        title="📊 Évolution hebdomadaire – Charges moyennes & Volume",
        barmode='group',
        xaxis_title="Semaine",
        yaxis_title="Charge (moyenne)",
        yaxis2=dict(
            title="Durée (min)",
            overlaying='y',
            side='right'
        ),
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig2, use_container_width=True)


def afficher_blocs(blocs):
    if not blocs or isinstance(blocs, float):
        return ""

    if isinstance(blocs, str):
        try:
            blocs = json.loads(blocs)
        except Exception:
            return ""

    if not isinstance(blocs, list):
        return ""

    lignes = []
    for b in blocs:
        repetitions = b.get('Répétitions', 1)
        volume = b.get('Volume total', b.get('Durée', ''))
        zone = b.get('Zone', '')
        bloc_type = b.get('Type', '')
        description = b.get('Description', '')

        ligne = f"{repetitions}× {volume}min – {zone} [{bloc_type}]"
        if description:
            ligne += f" - {description}"
        lignes.append(ligne)

    return "\n".join(lignes)


def afficher_blocs(blocs):
    blocs = json.loads(blocs) if isinstance(blocs, str) else blocs
    return "\n".join([
        f"{b['Répétitions']}× {b['Volume total']}min – {b['Zone']} [{b['Type']}] {b.get('Description', '')}"
        for b in blocs
    ])

def page_athlete(nom_athlete):
    st.header("🏃 Espace Athlètes")

    st.write(f"Bonjour {nom_athlete}, voici ton plan personnel.")

    athletes = load_csv(ATHLETES_FILE)
    noms_athletes = athletes["Nom"].unique().tolist()
    nom = nom_athlete

    today = dt.date.today()
    assignations = load_csv(ASSIGN_FILE)
    seances = load_csv(SEANCES_STRUCT_FILE)
    feedbacks = load_csv(FEEDBACKS_FILE)
    if feedbacks.empty:
        feedbacks = pd.DataFrame(columns=["Athlete", "Seance", "Semaine", "Date seance", "Effectuee", "RPE", "Commentaire"])

    assignations["Semaine"] = pd.to_datetime(assignations["Semaine"], errors="coerce").dt.date
    user_assign = assignations[assignations["Athlete"] == nom].sort_values("Semaine")

    semaine_debut = st.date_input("Choisir une semaine (sélectionner le lundi)", today, format="DD/MM/YYYY")
    semaine_fin = semaine_debut + dt.timedelta(days=6)
    st.subheader("📝 Séances prévues cette semaine")
    st.markdown(f"📆 Semaine du {semaine_debut.strftime('%d/%m')} au {semaine_fin.strftime('%d/%m')}")

    filtres = user_assign[
        (user_assign["Semaine"] >= semaine_debut) & (user_assign["Semaine"] <= semaine_fin)
    ]

    if filtres.empty:
        st.info("Aucune séance assignée cette semaine.")
        return

    assign_seances = filtres["Seance"].unique()
    base_seances = seances["Nom"].unique()
    orphan_seances = [s for s in assign_seances if s not in base_seances]
    if orphan_seances:
        st.warning(f"⚠️ Certaines séances assignées n'existent pas dans la base : {orphan_seances}")

    for jour in pd.date_range(semaine_debut, semaine_fin):
        jour = jour.date()
        daily = filtres[filtres["Semaine"] == jour]

        if not daily.empty:
            st.markdown("---")

        for i, (_, row) in enumerate(daily.iterrows()):
            nom_seance = row["Seance"]
            subset = seances[seances["Nom"] == nom_seance]
            if subset.empty:
                st.error(f"⚠️ La séance '{nom_seance}' n'existe pas dans la base des séances structurées.")
                continue
            seance = subset.iloc[0]

            blocs = afficher_blocs(seance["Blocs"])
            duree = seance["Volume total"]
            charge = seance["Charge totale"]

            key_suffix = f"{nom_seance}_{jour}_{i}"

            with st.expander(f"📝 {nom_seance} – {duree} min / Charge {charge}"):
                st.code(blocs)

                fb_mask = (
                    (feedbacks["Athlete"] == nom) &
                    (feedbacks["Seance"] == nom_seance) &
                    (feedbacks["Semaine"] == jour)
                )
                existing_feedback = feedbacks[fb_mask]

                if not existing_feedback.empty:
                    existing = existing_feedback.iloc[0]
                    fait_init = existing["Effectuee"]
                    rpe_init = int(existing["RPE"]) if pd.notna(existing["RPE"]) else 5
                    comm_init = existing["Commentaire"]
                    phase_init = existing.get("Phase menstruelle", "")
                    symptomes_init = existing.get("Symptômes", "")
                else:
                    fait_init = "Oui"
                    rpe_init = 5
                    comm_init = ""
                    phase_init = ""
                    symptomes_init = ""

                fait = st.radio("✅ Séance effectuée ?", ["Oui", "Non"], index=0 if fait_init == "Oui" else 1, key=f"fait_{key_suffix}")
                rpe = st.slider("RPE (1 à 10)", 1, 10, rpe_init, key=f"rpe_{key_suffix}")
                glucides = st.slider("🍌 Glucides ingérés (g/h)", 0, 200, 0, step=5, key=f"glucides_{key_suffix}")
                commentaire = st.text_area("Commentaire", comm_init, key=f"comm_{key_suffix}")

                athlete_data = pd.read_csv("data/athletes.csv")
                sexe = athlete_data[athlete_data["Nom"] == nom]["Sexe"].iloc[0].lower()
                amenorrhee = str(athlete_data[athlete_data["Nom"] == nom]["Amenorrhee"].iloc[0]).strip().lower()

                phase = ""
                symptomes = ""

                if sexe == "femme" and amenorrhee != "oui":
                    st.subheader("🌸 Suivi du cycle")
                    phase = st.selectbox("Phase actuelle", ["Règles", "Post-règles", "Ovulation", "Prémenstruel"],
                                        index=0 if phase_init == "" else ["Règles", "Post-règles", "Ovulation", "Prémenstruel"].index(phase_init),
                                        key=f"phase_{key_suffix}")
                    symptomes = st.text_area("Symptômes / sensations (facultatif)", symptomes_init, key=f"symptomes_{key_suffix}")

                if st.button("Enregistrer le feedback", key=f"save_{key_suffix}"):
                    now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_entry = {
                        "Athlete": nom,
                        "Seance": nom_seance,
                        "Semaine": jour,
                        "Date seance": now_str,
                        "Effectuee": fait,
                        "RPE": rpe,
                        "Glucides (g/h)": glucides,
                        "Commentaire": commentaire,
                        "Phase menstruelle": phase,
                        "Symptomes": symptomes,
                    }

                    if not existing_feedback.empty:
                        idx = existing_feedback.index[0]
                        feedbacks.loc[idx] = new_entry
                    else:
                        feedbacks = pd.concat([feedbacks, pd.DataFrame([new_entry])], ignore_index=True)

                    save_csv(feedbacks, FEEDBACKS_FILE)
                    st.success("Feedback enregistré ✅")

    # Statistiques hebdo
    st.markdown("---")
    st.subheader("📊 Statistiques hebdomadaires")

    merge = filtres.merge(seances, left_on="Seance", right_on="Nom", how="left")
    total_charge = merge["Charge totale"].sum()
    total_duree = merge["Volume total"].sum()
    moy_charge = merge["Charge totale"].mean()
    moy_duree = merge["Volume total"].mean()

    col1, col2 = st.columns(2)
    col1.metric("⚡ Charge totale", int(total_charge))
    col2.metric("⏱ Volume total (min)", int(total_duree))

    col3, col4 = st.columns(2)
    col3.metric("⚖️ Charge moyenne", int(round(moy_charge)))
    col4.metric("🕐 Volume moyen (min)", int(moy_duree))

        # Comparaison avec semaine précédente
    prec_debut = semaine_debut - dt.timedelta(days=7)
    prec_fin = semaine_fin - dt.timedelta(days=7)
    precedent = user_assign[
        (user_assign["Semaine"] >= prec_debut) & (user_assign["Semaine"] <= prec_fin)
    ].merge(seances, left_on="Seance", right_on="Nom", how="left")

    if not precedent.empty:
        charge_prec = precedent["Charge totale"].sum()
        variation_charge = ((total_charge - charge_prec) / charge_prec) * 100 if charge_prec != 0 else 0

        volume_prec = precedent["Volume total"].sum()
        variation_volume = ((total_duree - volume_prec) / volume_prec) * 100 if volume_prec != 0 else 0

        col1, col2 = st.columns(2)
        col1.metric("📈 Évolution charge semaine", f"{variation_charge:+.1f}%")
        col2.metric("📉 Évolution volume semaine", f"{variation_volume:+.1f}%")

# Date de début de l'athlète
    debut_str = athletes[athletes["Nom"] == nom]["Date debut"].iloc[0] if "Date debut" in athletes.columns else "2023-01-01"
    afficher_stats_et_evolution(feedbacks, seances, nom, debut_str)

    # Suivi menstruel
    ath_info = athletes[athletes["Nom"] == nom].iloc[0]
    sexe = ath_info["Sexe"]
    amenorrhee = ath_info.get("Aménorrhée", False)

    if sexe.lower() == "f" and not amenorrhee:
        st.subheader("🌸 Suivi du cycle")
        phase = st.selectbox("Phase actuelle", ["Règles", "Post-règles", "Ovulation", "Prémenstruel"])
        symptomes = st.text_area("Symptômes / sensations (facultatif)")