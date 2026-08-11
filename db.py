import streamlit as st
import gspread
import pandas as pd
import datetime
import re

@st.cache_resource
def init_connection():
    # Poprawione połączenie - otwiera Twój właściwy arkusz po nazwie
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open("NOWY PODZIAŁ OBOWIĄZKÓW") 
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
            
    # NOWOŚĆ: Śledzenie fizycznego wiersza (indeks pandas to 0, arkusz ma nagłówek, więc +2)
    if not df.empty:
        df['sheet_row'] = df.index + 2
    else:
        df['sheet_row'] = []
            
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
            
        # Zabezpieczenie: zachowujemy sheet_row przy nadpisywaniu kolejności kolumn
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

def save_data(worksheet, edited_df):
    # UWAGA: Pozostawione dla kompatybilności. Należy stopniowo podmieniać w kodzie 
    # wywołania tej funkcji na nową funkcję 'update_single_row_safe'.
    
    df_to_save = edited_df.copy()
    if 'sheet_row' in df_to_save.columns:
        df_to_save = df_to_save.drop(columns=['sheet_row'])
        
    with st.spinner('Synchronizacja z chmurą Google... ☁️'):
        worksheet.clear()
        worksheet.update(values=[df_to_save.columns.values.tolist()] + df_to_save.values.tolist(), range_name='A1')
    st.toast("Zmiany zapisane pomyślnie!", icon="✅")


# ==========================================
# NOWA FUNKCJA DO BEZPIECZNEGO ZAPISU (ELIMINACJA RACE CONDITIONS)
# ==========================================

def update_single_row_safe(sheet_name, gs_row_index, row_series):
    """Bezpieczna aktualizacja pojedynczego wiersza bez czyszczenia całego arkusza."""
    sh = init_connection()
    ws = sh.worksheet(sheet_name)
    
    # Kopiujemy dane i usuwamy techniczną kolumnę 'sheet_row', żeby nie wrzucić jej do Google Sheets
    dane_do_zapisu = row_series.copy()
    if 'sheet_row' in dane_do_zapisu:
        dane_do_zapisu = dane_do_zapisu.drop('sheet_row')
        
    row_list = dane_do_zapisu.tolist()
    
    # Przeliczanie długości listy na literę kolumny (np. 20 kolumn -> T)
    def get_col_letter(col_idx):
        string = ""
        while col_idx > 0:
            col_idx, remainder = divmod(col_idx - 1, 26)
            string = chr(65 + remainder) + string
        return string
        
    ostatnia_kolumna = get_col_letter(len(row_list))
    zakres = f"A{gs_row_index}:{ostatnia_kolumna}{gs_row_index}"
    
    ws.update(values=[row_list], range_name=zakres)
    return True

# ==========================================

def generuj_smart_id(df, kolumna_glowna, kolumna_dodatkowa, nazwa_kolumny_id="ID_Zlecenia"):
    licznik_elementow = {}
    if nazwa_kolumny_id not in df.columns:
        df[nazwa_kolumny_id] = ""
        
    for idx, row in df.iterrows():
        wartosc1 = str(row.get(kolumna_glowna, '')).strip().upper()
        wartosc2 = str(row.get(kolumna_dodatkowa, '')).strip().upper()
        
        # Zliczamy wystąpienia Głównej Wartości, by nadać kolejny poprawny numer (01, 02, 03)
        if wartosc1:
            if wartosc1 not in licznik_elementow: 
                licznik_elementow[wartosc1] = 1
            else: 
                licznik_elementow[wartosc1] += 1
                
        if not wartosc1 and not wartosc2: continue
        
        # ZABEZPIECZENIE: Generujemy automat TYLKO, gdy pole ID jest puste!
        current_id = str(row.get(nazwa_kolumny_id, "")).strip()
        if not current_id:
            czesc1 = re.sub(r'[^A-Z0-9]', '', wartosc1)[:4] if wartosc1 else "BRAK"
            czesc2 = re.sub(r'[^A-Z0-9]', '', wartosc2)[:4] if wartosc2 else "BRAK"
            numer = str(licznik_elementow.get(wartosc1, 1)).zfill(2)
            df.at[idx, nazwa_kolumny_id] = f"{czesc1}-{czesc2}-{numer}"
            
    return df

# ==========================================
# FUNKCJE CRUD (DODANE Z CORE.PY)
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
