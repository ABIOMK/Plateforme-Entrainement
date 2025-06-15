import ast

def format_blocs(blocs):
    """Affiche les blocs de manière lisible dans une cellule"""
    if isinstance(blocs, str):
        try:
            blocs = ast.literal_eval(blocs)
        except Exception:
            return blocs

    lignes = []
    for b in blocs:
        lignes.append(
            f"{b['Répétitions']}×{b['Durée']}min {b['Zone']} [{b['Type']}] {b.get('Description','')}"
        )
    return "\n".join(lignes)

def format_blocs_athlete(blocs):
    """Affichage optimisé pour les athlètes"""
    if isinstance(blocs, str):
        blocs = ast.literal_eval(blocs)
    lignes = []
    for b in blocs:
        lignes.append(
            f"▶ {b['Répétitions']}× {b['Durée']} min | {b['Zone']} | {b['Type']}"
            + (f" – {b['Description']}" if b.get('Description') else "")
        )
    return "\n".join(lignes)
