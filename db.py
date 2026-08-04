import streamlit as st
import gspread
import pandas as pd
import datetime
import re

@st.cache_resource
def init_connection():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open_by_key("1Vw72-HoJhhYMvI5FpcrmeFAhXfDF-mcjpSazyak9Tc4") 
    return sh

def load_data(sh, sheet_name):
    try:
        worksheet = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=sheet_name, rows=1000, cols=25)

    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    if df.empty:
        headers = worksheet.row_values(1)
        if headers:
            df = pd.DataFrame(columns=headers)
            
    if sheet_name == "DB_Eventy":
        wymagane = ["CMR_Gotowe", "CMR_Podpisane_POD", "Faktura_Oplacona", "PP_Otrzymane", "Zakonczone_Arch"]
        for kol in wymagane:
            if kol not in df.columns: df[kol] = ""
        domyslne_kolumny = {
            "Typ_Transportu": "Zewnętrzny", "ID_Zlecenia": "", "Nazwa_Targow": "",
            "Faza_Procesu": "Inicjacja", "Typ_Pojazdu": "", "Przewoznik": "",
            "Data_Zlecenia_Tr": str(datetime.date.today()), "Status_Magazyn": "Brak gotowości",
            "Notatki": "", "Koszt_Transportu_EUR": 0.0, "Nr_Zlecenia_Zewn": "", "Nr_Faktury": "",
            "Data_Zakonczenia_Uslugi": "", "Data_Platnosci": ""
        }
        for kol, val in domyslne_kolumny.items():
            if kol not in df.columns: df[kol] = val

    elif sheet_name == "DB_Subrenty":
        domyslne_subrenty = {
            "ID_Subrentu": "", "Rodzaj_Zlecenia": "Dry Hire", "Dostawca": "", "Co_Jedzie": "",
            "Data_Odbioru": str(datetime.date.today()), "Deadline_Zwrotu": str(datetime.date.today()),
            "Status_Subrentu": "1. Zamówione (Oczekuje na IN)", "Transport_IN_Kto": "", "Transport_IN_Dokumenty": "",
            "Transport_OUT_Kto": "", "Transport_OUT_Dokumenty": "", "Koszt_Calkowity_EUR": 0.0,
            "Nr_Zlecenia_Zewn": "", "Nr_Faktury": "", "Data_Faktycznego_Zwrotu": "",
            "Data_Platnosci": "", "Faktura_Oplacona": "", "PP_Otrzymane": "", "Zakonczone_Arch": "NIE"
        }
        for kol, val in domyslne_subrenty.items():
            if kol not in df.columns: df[kol] = val
                
    elif sheet_name == "DB_Yestech":
        domyslne_yestech = {
            "ID_Yestech": "", "Data_Zgloszenia": str(datetime.date.today()),
            "Destynacja": "", "Gabaryt": "", "Status_Ofertowy": "1. Zapytanie",
            "Wycena_Dla_Basi": 0.0, "Koszt_Rzeczywisty": 0.0, "Marza_Info": "",
            "Przewoznik": "", "CMR_Gotowe": "", "Nr_Zlecenia_Zewn": "",
            "Nr_Faktury": "", "Data_Zlecenia_Tr": "", "Data_Zakonczenia_Uslugi": "",
            "Data_Platnosci": "", "Faktura_Oplacona": "", "PP_Otrzymane": "",
            "Zakonczone_Arch": "NIE"
        }
        for kol in domyslne_yestech.keys():
            if kol not in df.columns: df[kol] = domyslne_yestech[kol]
        df = df[list(domyslne_yestech.keys())]

    elif sheet_name == "DB_Sloty":
        domyslne_sloty = {
            "ID_Zlecenia": "", "Typ_Operacji": "Montaż", "Data_Slota": str(datetime.date.today()),
            "Godzina_Od": "", "Godzina_Do": "", "Brama_Rampa": "", "Notatki": ""
        }
        for kol, val in domyslne_sloty.items():
            if kol not in df.columns: df[kol] = val
        df = df[list(domyslne_sloty.keys())]
                
    return worksheet, df

def save_data(worksheet, edited_df):
    with st.spinner('Synchronizacja z chmurą Google... ☁️'):
        worksheet.clear()
        worksheet.update(values=[edited_df.columns.values.tolist()] + edited_df.values.tolist(), range_name='A1')
    st.toast("Zmiany zapisane pomyślnie!", icon="✅")

def generuj_smart_id(df, kolumna_glowna, kolumna_dodatkowa, nazwa_kolumny_id="ID_Zlecenia"):
    licznik_elementow = {}
    if nazwa_kolumny_id not in df.columns:
        df[nazwa_kolumny_id] = ""
    for idx, row in df.iterrows():
        wartosc1 = str(row.get(kolumna_glowna, '')).strip().upper()
        wartosc2 = str(row.get(kolumna_dodatkowa, '')).strip().upper()
        if not wartosc1 and not wartosc2: continue
        if wartosc1 not in licznik_elementow: licznik_elementow[wartosc1] = 1
        else: licznik_elementow[wartosc1] += 1
        czesc1 = re.sub(r'[^A-Z0-9]', '', wartosc1)[:4] if wartosc1 else "BRAK"
        czesc2 = re.sub(r'[^A-Z0-9]', '', wartosc2)[:4] if wartosc2 else "BRAK"
        numer = str(licznik_elementow[wartosc1]).zfill(2)
        df.at[idx, nazwa_kolumny_id] = f"{czesc1}-{czesc2}-{numer}"
    return df

# ==========================================
# NOWE FUNKCJE CRUD (DODANE Z CORE.PY)
# ==========================================

def fetch_data(sheet_name):
    """Szybkie pobieranie danych jako DataFrame bez tworzenia brakujących kolumn."""
    sh = init_connection()
    try:
        ws = sh.worksheet(sheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Błąd pobierania arkusza {sheet_name}: {e}")
        return pd.DataFrame()

def append_data(sheet_name, row_data):
    """Dodawanie nowego wiersza na sam dół arkusza."""
    sh = init_connection()
    try:
        ws = sh.worksheet(sheet_name)
        ws.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Błąd zapisu w {sheet_name}: {e}")
        return False

def update_row(sheet_name, row_index, row_data):
    """Nadpisywanie konkretnego wiersza (np. podczas edycji przewoźnika/zlecenia)."""
    sh = init_connection()
    try:
        ws = sh.worksheet(sheet_name)
        # Obliczamy zakres od kolumny A do litery odpowiadającej długości danych
        ostatnia_kolumna = chr(65 + len(row_data) - 1) 
        zakres = f"A{row_index}:{ostatnia_kolumna}{row_index}"
        ws.update(values=[row_data], range_name=zakres)
        return True
    except Exception as e:
        st.error(f"Błąd aktualizacji wiersza {row_index} w {sheet_name}: {e}")
        return False

def delete_row(sheet_name, row_index):
    """Trwałe usuwanie wiersza z bazy danych."""
    sh = init_connection()
    try:
        ws = sh.worksheet(sheet_name)
        ws.delete_rows(row_index)
        return True
    except Exception as e:
        st.error(f"Błąd usuwania wiersza {row_index} w {sheet_name}: {e}")
        return False

def get_next_daily_number(date_str):
    """Generowanie unikalnego numeru dziennego dla nowych zleceń PRO."""
    df = fetch_data("Zlecenia")
    if df.empty or 'Data/Czas Operacji' not in df.columns:
        return 1
    # Zliczamy zlecenia, które w kolumnie systemowej daty (np. 2026-08-04) zaczynają się od tej frazy
    dzisiejsze_zlecenia = sum(df['Data/Czas Operacji'].astype(str).str.startswith(date_str))
    return dzisiejsze_zlecenia + 1
