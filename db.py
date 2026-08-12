import streamlit as st
import gspread
import pandas as pd
import datetime
import re

@st.cache_resource
def init_connection():
    # Połączenie z Google Sheets zoptymalizowane pod kątem zasobów
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open("NOWY PODZIAŁ OBOWIĄZKÓW") 
    return sh

def get_col_letter(col_idx):
    """Pomocnicza funkcja zamieniająca indeks kolumny (np. 1) na literę Excela (np. A)"""
    string = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        string = chr(65 + remainder) + string
    return string

# Zoptymalizowana i KULOODPORNA funkcja load_data z keszowaniem
@st.cache_data(ttl=60, show_spinner=False)
def load_data(_sh, sheet_name):
    try:
        worksheet = _sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = _sh.add_worksheet(title=sheet_name, rows=1000, cols=30)

    # =======================================================
    # AUTO-HEALING: Twarda synchronizacja nagłówków Eventów
    # =======================================================
    if sheet_name == "DB_Eventy":
        expected_headers = [
            "Typ_Transportu", "ID_Zlecenia", "Nazwa_Targow", "Faza_Procesu", "Typ_Pojazdu", "Przewoznik",
            "Data_Zlecenia_Tr", "Status_Magazyn", "Notatki", "Koszt_Transportu_EUR", "Nr_Zlecenia_Zewn",
            "Nr_Faktury", "Data_Zakonczenia_Uslugi", "Data_Platnosci", "CMR_Gotowe", "CMR_Podpisane_POD", 
            "Faktura_Oplacona", "PP_Otrzymane", "Zakonczone_Arch", 
            "Miejsce_Przeznaczenia", "Waga", "Nr_Rejestracyjny", "Kierowca", "Nr_CMR"
        ]
        try:
            current_headers = worksheet.row_values(1)
        except:
            current_headers = []
            
        # Jeśli arkusz ma rozjechane, brakujące lub źle wpisane kolumny - wymuszamy ich nadpisanie poprawnymi
        if current_headers[:len(expected_headers)] != expected_headers:
            letter = get_col_letter(len(expected_headers))
            worksheet.update(values=[expected_headers], range_name=f"A1:{letter}1")

    # BARDZO BEZPIECZNE POBIERANIE DANYCH (odporne na błędy pustych/podwójnych nagłówków)
    raw_data = worksheet.get_all_values()
    if raw_data and len(raw_data) > 0:
        headers = raw_data[0]
        # Zabezpieczenie przed pustymi nagłówkami w arkuszu (np. dodano kolumnę, ale nie wpisano nazwy)
        headers = [f"Brak_Nazwy_{i}" if str(h).strip() == "" else str(h).strip() for i, h in enumerate(headers)]
        
        # Zabezpieczenie przed duplikatami nagłówków
        seen = set()
        for i, h in enumerate(headers):
            if h in seen:
                headers[i] = f"{h}_duplikat_{i}"
            seen.add(headers[i])
            
        data = raw_data[1:]
        df = pd.DataFrame(data, columns=headers)
    else:
        df = pd.DataFrame()
            
    # Śledzenie fizycznego wiersza w Google Sheets
    if not df.empty:
        df['sheet_row'] = df.index + 2
    else:
        df['sheet_row'] = []

    # Fallback dla innych arkuszy
    if sheet_name == "DB_Subrenty":
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
            
        kolumny_do_zostawienia = list(domyslne_yestech.keys())
        if 'sheet_row' in df.columns:
            kolumny_do_zostawienia.append('sheet_row')
        df = df[kolumny_do_zostawienia]

    elif sheet_name == "DB_Sloty":
        domyslne_sloty = {
            "ID_Zlecenia": "", "Typ_Operacji": "Montaż", "Data_Slota": str(datetime.date.today()),
            "Godzina_Od": "", "Godzina_Do": "", "Brama_Rampa": "", "Notatki": ""
        }
        for kol, val in domyslne_sloty.items():
            if kol not in df.columns: df[kol] = val
            
        kolumny_do_zostawienia = list(domyslne_sloty.keys())
        if 'sheet_row' in df.columns:
            kolumny_do_zostawienia.append('sheet_row')
        df = df[kolumny_do_zostawienia]
                
    return worksheet, df

# Pobieranie danych z pamięci podręcznej (RAM) - również odporne na puste nagłówki
@st.cache_data(ttl=60, show_spinner=False)
def fetch_data(sheet_name):
    sh = init_connection()
    try:
        ws = sh.worksheet(sheet_name)
        raw_data = ws.get_all_values()
        if raw_data and len(raw_data) > 0:
            headers = raw_data[0]
            headers = [f"Brak_Nazwy_{i}" if str(h).strip() == "" else str(h).strip() for i, h in enumerate(headers)]
            seen = set()
            for i, h in enumerate(headers):
                if h in seen:
                    headers[i] = f"{h}_duplikat_{i}"
                seen.add(headers[i])
            df = pd.DataFrame(raw_data[1:], columns=headers)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Błąd pobierania arkusza {sheet_name}: {e}")
        return pd.DataFrame()

# ==========================================
# GŁÓWNY REJESTR NUMERACJI CMR
# ==========================================
def get_next_cmr_number():
    sh = init_connection()
    try:
        ws = sh.worksheet("System_Ustawienia")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="System_Ustawienia", rows=5, cols=2)
        ws.update(values=[['Klucz', 'Wartosc'], ['Ostatni_CMR', '24122253']], range_name='A1:B2')
        ws = sh.worksheet("System_Ustawienia")
        
    val = ws.acell('B2').value
    if not val or not str(val).isdigit():
        ws.update_acell('B2', '24122253')
        val = '24122253'
        
    next_cmr = int(val) + 1
    ws.update_acell('B2', str(next_cmr))
    return str(next_cmr)

# ==========================================
# FUNKCJE BEZPIECZNEGO ZAPISU I ARCHIWIZACJI
# ==========================================
def update_single_row_safe(sheet_name, gs_row_index, row_series):
    sh = init_connection()
    ws = sh.worksheet(sheet_name)
    
    dane_do_zapisu = row_series.copy()
    if 'sheet_row' in dane_do_zapisu:
        dane_do_zapisu = dane_do_zapisu.drop('sheet_row')
        
    row_list = dane_do_zapisu.tolist()
    ostatnia_kolumna = get_col_letter(len(row_list))
    zakres = f"A{gs_row_index}:{ostatnia_kolumna}{gs_row_index}"
    
    ws.update(values=[row_list], range_name=zakres)
    st.cache_data.clear()
    return True

def archive_row_safe(source_sheet, archive_sheet, row_index, row_data_list):
    sh = init_connection()
    try:
        try:
            ws_arch = sh.worksheet(archive_sheet)
        except gspread.exceptions.WorksheetNotFound:
            ws_source = sh.worksheet(source_sheet)
            headers = ws_source.row_values(1)
            ws_arch = sh.add_worksheet(title=archive_sheet, rows=1000, cols=len(headers))
            ws_arch.append_row(headers)
        
        ws_arch.append_row(row_data_list)
        ws_source = sh.worksheet(source_sheet)
        ws_source.delete_rows(row_index)
        
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd fizycznej archiwizacji: {e}")
        return False

# ==========================================
# POZOSTAŁE FUNKCJE CRUD I POMOCNICZE
# ==========================================
def save_data(worksheet, edited_df):
    df_to_save = edited_df.copy()
    if 'sheet_row' in df_to_save.columns:
        df_to_save = df_to_save.drop(columns=['sheet_row'])
        
    with st.spinner('Synchronizacja z chmurą Google... ☁️'):
        worksheet.clear()
        worksheet.update(values=[df_to_save.columns.values.tolist()] + df_to_save.values.tolist(), range_name='A1')
    st.cache_data.clear()
    st.toast("Zmiany zapisane pomyślnie!", icon="✅")

def append_data(sheet_name, row_data):
    sh = init_connection()
    try:
        ws = sh.worksheet(sheet_name)
        ws.append_row(row_data)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd zapisu w {sheet_name}: {e}")
        return False

def update_row(sheet_name, row_index, row_data):
    sh = init_connection()
    try:
        ws = sh.worksheet(sheet_name)
        ostatnia_kolumna = chr(65 + len(row_data) - 1) 
        zakres = f"A{row_index}:{ostatnia_kolumna}{row_index}"
        ws.update(values=[row_data], range_name=zakres)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd aktualizacji wiersza {row_index} w {sheet_name}: {e}")
        return False

def delete_row(sheet_name, row_index):
    sh = init_connection()
    try:
        ws = sh.worksheet(sheet_name)
        ws.delete_rows(row_index)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Błąd usuwania wiersza {row_index} w {sheet_name}: {e}")
        return False

def generuj_smart_id(df, kolumna_glowna, kolumna_dodatkowa, nazwa_kolumny_id="ID_Zlecenia"):
    licznik_elementow = {}
    if nazwa_kolumny_id not in df.columns:
        df[nazwa_kolumny_id] = ""
        
    for idx, row in df.iterrows():
        wartosc1 = str(row.get(kolumna_glowna, '')).strip().upper()
        wartosc2 = str(row.get(kolumna_dodatkowa, '')).strip().upper()
        
        if wartosc1:
            if wartosc1 not in licznik_elementow: 
                licznik_elementow[wartosc1] = 1
            else: 
                licznik_elementow[wartosc1] += 1
                
        if not wartosc1 and not wartosc2: continue
        
        current_id = str(row.get(nazwa_kolumny_id, "")).strip()
        if not current_id:
            czesc1 = re.sub(r'[^A-Z0-9]', '', wartosc1)[:4] if wartosc1 else "BRAK"
            czesc2 = re.sub(r'[^A-Z0-9]', '', wartosc2)[:4] if wartosc2 else "BRAK"
            numer = str(licznik_elementow.get(wartosc1, 1)).zfill(2)
            df.at[idx, nazwa_kolumny_id] = f"{czesc1}-{czesc2}-{numer}"
            
    return df

def get_next_daily_number(date_str):
    df = fetch_data("Zlecenia")
    if df.empty or 'Data/Czas Operacji' not in df.columns:
        return 1
    dzisiejsze_zlecenia = sum(df['Data/Czas Operacji'].astype(str).str.startswith(date_str))
    return dzisiejsze_zlecenia + 1
