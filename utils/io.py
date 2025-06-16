import os
import pandas as pd

# Détection environnement : si cloud, on utilise Google Sheets
USE_GOOGLE_SHEETS = "streamlit" in os.getcwd()

if USE_GOOGLE_SHEETS:
    import gspread
    from google.oauth2 import service_account
    import streamlit as st

    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(credentials)

    # 🟡 À PERSONNALISER : ID de fichier Google Sheet (trouvé dans l'URL)
    SHEET_ID = "1TEoqCvFNjRl-qr2kmLEP3pa4l6Gv7adzkCFIGBNBahA"
    sheet = client.open_by_key(SHEET_ID)

def load_csv(name, columns=None):
    if USE_GOOGLE_SHEETS:
        sheet_name = name.replace(".csv", "")
        try:
            worksheet = sheet.worksheet(sheet_name)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
        except gspread.exceptions.WorksheetNotFound:
            df = pd.DataFrame(columns=columns if columns else [])
        if columns:
            for col in columns:
                if col not in df.columns:
                    df[col] = None
            df = df[columns]
        return df
    else:
        filepath = f"{name}"
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            if columns:
                for col in columns:
                    if col not in df.columns:
                        df[col] = None
                df = df[columns]
        else:
            df = pd.DataFrame(columns=columns if columns else [])
        return df

def save_csv(df, name):
    if USE_GOOGLE_SHEETS:
        worksheet = sheet.worksheet(name.replace(".csv", ""))
        worksheet.clear()
        worksheet.update([df.columns.tolist()] + df.values.tolist())
    else:
        filepath = f"{name}"
        os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) else None
        df.to_csv(filepath, index=False)
