import os
import pandas as pd

def load_csv(filepath, columns=None):
    """
    Charge un fichier CSV en DataFrame pandas.
    Si le fichier n'existe pas ou si certaines colonnes sont manquantes,
    un DataFrame vide avec les colonnes spécifiées est retourné.
    """
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        if columns:
            # S'assurer que toutes les colonnes demandées sont présentes
            for col in columns:
                if col not in df.columns:
                    df[col] = None
            df = df[columns]
    else:
        df = pd.DataFrame(columns=columns if columns else [])
    return df

def save_csv(df, filepath):
    """
    Sauvegarde un DataFrame en CSV (sans l’index).
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False)
