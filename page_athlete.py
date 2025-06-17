import streamlit as st
import pandas as pd
from datetime import date,datetime, timedelta
import datetime as dt
import json
import calendar
import os
from utils.io import load_csv, save_csv
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components

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

def extraire_date_lundi(chaine_semaine):
    try:
        jour_mois = chaine_semaine.split(" - ")[1]
        annee = datetime.today().year
        return datetime.strptime(f"{jour_mois}/{annee}", "%d/%m/%Y")
    except Exception:
        return None

def page_athlete(nom_athlete):
    st.header("🏃 Espace Athlètes")
    st.write(f"Bonjour {nom_athlete}, voici ton plan personnel.")

    # Chargement des fichiers
    athletes = load_csv(ATHLETES_FILE)
    assignations = load_csv(ASSIGN_FILE)
    seances = load_csv(SEANCES_STRUCT_FILE)
    feedbacks = load_csv(FEEDBACKS_FILE)

    if feedbacks.empty:
        st.info("Aucun feedback enregistré pour le moment.")
        return

    # Appliquer la date du lundi
    assignations["Date_lundi"] = pd.to_datetime(assignations["Semaine"].apply(extraire_date_lundi), errors="coerce")
    assignations = assignations.dropna(subset=["Date_lundi"])
    user_assign = assignations[assignations["Athlete"] == nom_athlete].sort_values("Date_lundi")

    # Sélection de la semaine par défaut : lundi courant
    today = dt.date.today()
    default_lundi = today - dt.timedelta(days=today.weekday())
    semaine_debut = st.date_input("Choisir une semaine (sélectionner le lundi)", default_lundi, format="DD/MM/YYYY")
    semaine_fin = semaine_debut + dt.timedelta(days=6)

    st.subheader("📝 Séances prévues cette semaine")
    st.markdown(f"📆 Semaine du {semaine_debut.strftime('%d/%m')} au {semaine_fin.strftime('%d/%m')}")

    # Filtrage des assignations de la semaine sélectionnée
    semaine_debut_dt = pd.to_datetime(semaine_debut)
    semaine_fin_dt = pd.to_datetime(semaine_fin)
    filtres = user_assign[(user_assign["Date_lundi"] >= semaine_debut_dt) & (user_assign["Date_lundi"] <= semaine_fin_dt)]

    if filtres.empty:
        st.info("Aucune séance assignée cette semaine.")
        return

    # Vérifier les séances orphelines
    assign_seances = filtres["Seance"].unique()
    base_seances = seances["Nom"].unique()
    orphan_seances = [s for s in assign_seances if s not in base_seances]
    if orphan_seances:
        st.warning(f"⚠️ Certaines séances assignées n'existent plus dans la base : {orphan_seances}")

    for jour in pd.date_range(semaine_debut_dt, semaine_fin_dt):
        daily = filtres[filtres["Date_lundi"] == jour]

        if not daily.empty:
            st.markdown("---")

        for i, (_, row) in enumerate(daily.iterrows()):
            nom_seance = row["Seance"]
            subset = seances[seances["Nom"] == nom_seance]

            if subset.empty:
                st.error(f"⚠️ La séance '{nom_seance}' n'existe plus.")
                continue

            seance = subset.iloc[0]
            blocs = afficher_blocs(seance["Blocs"])
            duree = seance["Volume total"]
            charge = seance["Charge totale"]
            key_suffix = f"{nom_seance}_{jour.date()}_{i}"

            with st.expander(f"📝 {nom_seance} – {duree} min / Charge {charge}"):
                st.code(blocs)

                # Feedback existant ?
                fb_mask = (
                    (feedbacks["Athlete"] == nom_athlete) &
                    (feedbacks["Seance"] == nom_seance) &
                    (pd.to_datetime(feedbacks["Semaine"]) == jour)
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
                    fait_init, rpe_init, comm_init, phase_init, symptomes_init = "Oui", 5, "", "", ""

                # Saisie du feedback
                fait = st.radio("✅ Séance effectuée ?", ["Oui", "Non"], index=0 if fait_init == "Oui" else 1, key=f"fait_{key_suffix}")
                rpe = st.slider("RPE (1 à 10)", 1, 10, rpe_init, key=f"rpe_{key_suffix}")
                glucides = st.slider("🍌 Glucides ingérés (g/h)", 0, 200, 0, step=5, key=f"glucides_{key_suffix}")
                commentaire = st.text_area("Commentaire", comm_init, key=f"comm_{key_suffix}")

                # Suivi menstruel ?
                ath_info = athletes[athletes["Nom"] == nom_athlete].iloc[0]
                sexe = ath_info["Sexe"].lower()
                amenorrhee = str(ath_info.get("Amenorrhee", "")).strip().lower()

                phase = symptomes = ""
                if sexe == "femme" and amenorrhee != "oui":
                    st.subheader("🌸 Suivi du cycle")
                    phase = st.selectbox("Phase actuelle", ["Règles", "Post-règles", "Ovulation", "Prémenstruel"],
                                         index=0 if phase_init == "" else ["Règles", "Post-règles", "Ovulation", "Prémenstruel"].index(phase_init),
                                         key=f"phase_{key_suffix}")
                    symptomes = st.text_area("Symptômes / sensations (facultatif)", symptomes_init, key=f"symptomes_{key_suffix}")

                if st.button("💾 Enregistrer le feedback", key=f"save_{key_suffix}"):
                    now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_entry = {
                        "Athlete": nom_athlete,
                        "Seance": nom_seance,
                        "Semaine": jour.date(),
                        "Date seance": now_str,
                        "Effectuee": fait,
                        "RPE": rpe,
                        "Glucides (g/h)": glucides,
                        "Commentaire": commentaire,
                        "Phase menstruelle": phase,
                        "Symptomes": symptomes,
                    }

                    if not existing_feedback.empty:
                        feedbacks.loc[existing_feedback.index[0]] = new_entry
                    else:
                        feedbacks = pd.concat([feedbacks, pd.DataFrame([new_entry])], ignore_index=True)

                    save_csv(feedbacks, FEEDBACKS_FILE)
                    st.success("Feedback enregistré ✅")

    # Statistiques hebdo
    st.markdown("---")
    st.subheader("📊 Statistiques hebdomadaires")

    # Fusion avec les infos de séance
    merge = filtres.merge(seances, left_on="Seance", right_on="Nom", how="left")
    total_charge = merge["Charge totale"].sum()
    total_duree = merge["Volume total"].sum()
    moy_charge = merge["Charge totale"].mean()
    moy_duree = merge["Volume total"].mean()

    # Semaine précédente
    prec_debut = pd.to_datetime(semaine_debut - dt.timedelta(days=7))
    prec_fin = pd.to_datetime(semaine_fin - dt.timedelta(days=7))
    precedent = user_assign[
        (user_assign["Date_lundi"] >= prec_debut) & (user_assign["Date_lundi"] <= prec_fin)
    ].merge(seances, left_on="Seance", right_on="Nom", how="left")

    # Calculs variation
    if not precedent.empty:
        charge_prec = precedent["Charge totale"].sum()
        charge_moy_prec = precedent["Charge totale"].mean()
        volume_prec = precedent["Volume total"].sum()
        volume_moy_prec = precedent["Volume total"].mean()

        var_tot_charge = ((total_charge - charge_prec) / charge_prec * 100) if charge_prec else None
        var_moy_charge = ((moy_charge - charge_moy_prec) / charge_moy_prec * 100) if charge_moy_prec else None
        var_tot_volume = ((total_duree - volume_prec) / volume_prec * 100) if volume_prec else None
        var_moy_volume = ((moy_duree - volume_moy_prec) / volume_moy_prec * 100) if volume_moy_prec else None
    else:
        var_tot_charge = var_moy_charge = var_tot_volume = var_moy_volume = None

    # Affichage évolutions intégrées
    def format_variation(pct):
        if pct is None:
            return ""
        arrow = "▲" if pct >= 0 else "▼"
        color = "green" if abs(pct) <= 12 else "red"
        return f"<span style='font-size:0.75em; color:{color}; margin-left:6px'>{arrow} {abs(pct):.1f}%</span>"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"⚡️ **Charge totale :** {int(total_charge)} {format_variation(var_tot_charge)}", unsafe_allow_html=True)
    with col2:
        st.markdown(f"⏱️ **Volume total (min) :** {int(total_duree)} min {format_variation(var_tot_volume)}", unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown(f"⚖️ **Charge moyenne :** {int(round(moy_charge))} {format_variation(var_moy_charge)}", unsafe_allow_html=True)
    with col4:
        st.markdown(f"🕐 **Volume moyen (min) :** {int(round(moy_duree))} min {format_variation(var_moy_volume)}", unsafe_allow_html=True)

        