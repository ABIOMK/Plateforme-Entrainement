import pandas as pd
from datetime import datetime, timedelta
import ast
import json
import unicodedata


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

# --- Fonctions utilitaires déplacées depuis page_athlete
def extraire_date_lundi(chaine_semaine):
    try:
        jour_mois = chaine_semaine.split(" - ")[1]
        annee = datetime.today().year
        return datetime.strptime(f"{jour_mois}/{annee}", "%d/%m/%Y")
    except Exception:
        return None

def format_h_min(minutes):
    h = int(minutes) // 60
    m = int(minutes) % 60
    return f"{h}h{m:02d}"

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

    def zone_to_emoji(zone):
        z = str(zone).strip()[-1]  # Dernier caractère, souvent un chiffre
        return {
            "1": "🔘",
            "2": "🔵",
            "3": "🟢",
            "4": "🟡",
            "5": "🔴",
            "6": "🟤",
            "7": "🟣"
        }.get(z, "🎯")

    lignes = []
    for b in blocs:
        repetitions = b.get('Répétitions', 1)
        volume = b.get('Volume total') or b.get('Durée', '')
        zone = b.get('Zone', '')
        type_ = b.get('Type', '')
        description = b.get('Description', '')

        emoji_zone = zone_to_emoji(zone)
        ligne = f"{repetitions}× {volume}min ⏱ – {zone} {emoji_zone} [{type_}]"
        if description:
            ligne += f" - {description}"
        lignes.append(ligne)

    return "\n".join(lignes)

# --- Fonctions utilitaires déplacées depuis page_coach ---
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

def regrouper_zone(zone_num):
    if zone_num in [1, 2]:
        return "basse"
    elif zone_num in [3, 4]:
        return "moyenne"
    elif zone_num == 5:
        return "haute"
    elif zone_num in [6, 7]:
        return "extreme"
    else:
        return None
    
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
    
def evolution_pct(df, col, semaine_courante):
    if semaine_courante not in df.index:
        return 0, 0
    idx = df.index.get_loc(semaine_courante)
    if idx == 0:
        return 0, 0
    prev_row = df.iloc[idx - 1]
    curr_row = df.loc[semaine_courante]
    prev = prev_row[col]
    curr = curr_row[col]
    delta = curr - prev
    pct = (delta / prev * 100) if prev else 0
    return delta, pct

def generer_identifiant(nom_complet):
    # Met en minuscules
    nom = nom_complet.strip().lower()
    # Supprime les accents
    nom = unicodedata.normalize('NFKD', nom).encode('ASCII', 'ignore').decode('utf-8')
    # Supprime les espaces
    identifiant = nom.replace(" ", "")
    return identifiant

