import pandas as pd
from datetime import datetime, timedelta

def calculer_charge_bloc(bloc):
    """Renvoie la charge d’un bloc : Durée x Répétitions x Zone"""
    return bloc["Durée"] * bloc["Répétitions"] * int(bloc["Zone"].strip("🔘🔵🟢🟡🔴Zone "))

def calculer_duree_bloc(bloc):
    """Renvoie la durée d’un bloc (min)"""
    return bloc["Durée"] * bloc["Répétitions"]

def evolution_pourcentage(nouvelle_valeur, ancienne_valeur):
    """Renvoie l'évolution en % entre deux valeurs"""
    if ancienne_valeur == 0:
        return None
    return round(((nouvelle_valeur - ancienne_valeur) / ancienne_valeur) * 100, 2)

def charge_et_duree_par_semaine(df):
    """Renvoie un DataFrame avec la charge et durée moyennes et totales par semaine"""
    if df.empty or "Date" not in df.columns:
        return pd.DataFrame()

    df["Semaine"] = pd.to_datetime(df["Date"]).dt.isocalendar().week
    df["Année"] = pd.to_datetime(df["Date"]).dt.isocalendar().year
    resume = df.groupby(["Année", "Semaine"]).agg({
        "Charge": ["sum", "mean"],
        "Durée (min)": ["sum", "mean"]
    }).reset_index()
    resume.columns = ["Année", "Semaine", "Charge totale", "Charge moyenne", "Volume total", "Volume moyen"]
    return resume