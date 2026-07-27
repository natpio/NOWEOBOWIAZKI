import streamlit as st
import gspread
import pandas as pd

# 1. KONFIGURACJA STRONY (Zawsze na górze)
st.set_page_config(page_title="SQM Transport Hub", page_icon="🚚", layout="wide", initial_sidebar_state="expanded")

# 2. ŁADOWANIE ZEWNĘTRZNEGO PLIKU CSS
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

try:
    load_css("style.css")
except FileNotFoundError:
    st.warning("Plik style.css nie został znaleziony. Aplikacja używa domyślnego wyglądu.")

# 3. FUNKCJE BAZODANOWE
@st.cache_resource
def init_connection():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open_by_key("1Vw72-HoJhhYMvI5FpcrmeFAhXfDF-mcjpSazyak9Tc4") 
    return sh

def load_data(sh, sheet_name):
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        headers = worksheet.row_values(1)
        if headers:
            df = pd.DataFrame(columns=headers)
    return worksheet, df

def save_data(worksheet, edited_df):
    with st.spinner('Synchronizacja z chmurą Google... ☁️'):
        worksheet.clear()
        worksheet.update(values=[edited_df.columns.values.tolist()] + edited_df.values.tolist(), range_name='A1')
    st.toast("Zmiany zapisane pomyślnie!", icon="✅")

try:
    sh = init_connection()
except Exception as e:
    st.error(f"❌ Krytyczny błąd połączenia z bazą: {e}")
    st.stop()

# 4. KONFIGURACJA KOLUMN (Dropdowns, Checkboxy, Formaty)
opcje_tak_nie = ["", "TAK", "NIE"]
wspolna_konfiguracja = {
    "CMR_Gotowe": st.column_config.SelectboxColumn("📄 CMR", options=opcje_tak_nie),
    "Faktura_Oplacona": st.column_config.SelectboxColumn("💰 Faktura Opłacona", options=opcje_tak_nie),
    "PP_Otrzymane": st.column_config.SelectboxColumn("🏦 PP Otrzymane", options=opcje_tak_nie),
    "Zakonczone_Arch": st.column_config.SelectboxColumn("📦 Archiwum", options=opcje_tak_nie),
}

# --- MENU BOCZNE ---
with st.sidebar:
    st.title("SQM TMS")
    st.markdown("---")
    wybrany_modul = st.radio(
        "Nawigacja:",
        ["🚚 Eventy / Targi", "📦 Subrenty", "🌍 YESTECH Export", "📊 Finanse i Raporty"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("Wersja systemu: 3.0.0 (Enterprise UI)")

# --- MODUŁY GŁÓWNE ---

if wybrany_modul == "🚚 Eventy / Targi":
    st.title("Eventy & Flota")
    
    worksheet, df = load_data(sh, "DB_Eventy")
    
    # Kafelki KPI (Dashboard)
    col1, col2, col3 = st.columns(3)
    with col1:
        aktywne = len(df[df.get("Zakonczone_Arch", pd.Series()) != "TAK"]) if not df.empty else 0
        st.metric("Liczba aut (Aktywne)", aktywne)
    with col2:
        braki_cmr = len(df[df.get("CMR_Gotowe", pd.Series()) == "NIE"]) if not df.empty else 0
        st.metric("Oczekujące CMR", braki_cmr)
    with col3:
        st.metric("Status Serwera", "Online 🟢")
    
    st.divider()

    widok = st.radio(
        "🔎 Obszar roboczy:",
        ["📍 Baza i Trasa", "🏗️ Magazyn i Załadunek", "📑 Dokumenty i Finanse", "👁️ Widok Pełny"],
        horizontal=True
    )
    
    if widok == "📍 Baza i Trasa":
        kolumny = ["ID_Zlecenia", "Nazwa_Targow", "Project_Manager", "Faza_Procesu", "Akcept_Alicji", "Typ_Pojazdu", "Przewoznik", "Data_Zlecenia_Tr"]
    elif widok == "🏗️ Magazyn i Załadunek":
        kolumny = ["ID_Zlecenia", "Nazwa_Targow", "Status_Magazyn", "Magazyn_Powod", "ETA_Wydania", "Wrzutka_PM", "Koszt_Dodatkowy"]
    elif widok == "📑 Dokumenty i Finanse":
        kolumny = ["ID_Zlecenia", "Nazwa_Targow", "CMR_Gotowe", "Nr_Zlecenia_Zewn", "Nr_Faktury", "Data_Zakonczenia_Uslugi", "Data_Platnosci", "Faktura_Oplacona", "PP_Otrzymane", "Zakonczone_Arch"]
    else:
        kolumny = df.columns.tolist()
        
    konfiguracja_eventy = {
        **wspolna_konfiguracja,
        "Faza_Procesu": st.column_config.SelectboxColumn("Faza", options=["Inicjacja", "Flota", "Dokumenty", "Załadunek", "Trasa", "Zamknięte"]),
        "Status_Magazyn": st.column_config.SelectboxColumn("Magazyn", options=["100% Gotowe", "Częściowo", "Opóźnione", "Brak gotowości"]),
        "Akcept_Alicji": st.column_config.SelectboxColumn("Akcept", options=opcje_tak_nie),
        "Wrzutka_PM": st.column_config.SelectboxColumn("Wrzutka", options=opcje_tak_nie),
        "Koszt_Dodatkowy": st.column_config.NumberColumn("Koszt Dod. (PLN)", format="%d zł", min_value=0),
    }

    edited_df = st.data_editor(
        df, 
        column_order=kolumny,
        column_config=konfiguracja_eventy,
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True,
        height=450
    )
    
    st.write("")
    if st.button("💾 Zapisz zmiany w bazie »", key="save_eventy"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "📦 Subrenty":
    st.title("Hub Subrentów")
    worksheet, df = load_data(sh, "DB_Subrenty")
    
    col1, col2 = st.columns(2)
    with col1:
        aktywne_sub = len(df[df.get("Zakonczone_Arch", pd.Series()) != "TAK"]) if not df.empty else 0
        st.metric("Oczekujące Zwroty", aktywne_sub)
    with col2:
        braki_cmr_sub = len(df[df.get("CMR_Gotowe", pd.Series()) == "NIE"]) if not df.empty else 0
        st.metric("Brakujące Listy Przewozowe", braki_cmr_sub)

    st.divider()
    widok = st.radio(
        "🔎 Obszar roboczy:",
        ["📍 Szczegóły i Status", "🚚 Logistyka", "📑 Finanse i Zamknięcie", "👁️ Widok Pełny"],
        horizontal=True
    )
    
    if widok == "📍 Szczegóły i Status":
        kolumny = ["ID_Zlecenia", "Rodzaj_Zlecenia", "Dostawca", "Co_Jedzie", "Data_Zlecenia", "Deadline_Zwrotu", "Status_Subrentu"]
    elif widok == "🚚 Logistyka":
        kolumny = ["ID_Zlecenia", "Przewoznik_OUT", "List_Przewozowy", "CMR_Gotowe", "Nr_Zlecenia_Zewn", "Data_Zlecenia_Tr", "Data_Zakonczenia_Uslugi"]
    elif widok == "📑 Finanse i Zamknięcie":
        kolumny = ["ID_Zlecenia", "Nr_Faktury", "Data_Platnosci", "Faktura_Oplacona", "PP_Otrzymane", "Zakonczone_Arch"]
    else:
        kolumny = df.columns.tolist()
        
    konfiguracja_subrenty = {
        **wspolna_konfiguracja,
        "Rodzaj_Zlecenia": st.column_config.SelectboxColumn("Rodzaj", options=["Odbiór Pustych", "Subrent", "Zwrot Subrentu", "Dostawa Zaopatrzenia"]),
        "Status_Subrentu": st.column_config.SelectboxColumn("Status", options=["Oczekuje", "Na Magazynie", "Wysłane", "Zakończone"]),
    }

    edited_df = st.data_editor(df, column_order=kolumny, column_config=konfiguracja_subrenty, num_rows="dynamic", use_container_width=True, hide_index=True, height=450)
    
    st.write("")
    if st.button("💾 Zapisz zmiany w bazie »", key="save_subrenty"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "🌍 YESTECH Export":
    st.title("YESTECH Global")
    worksheet, df = load_data(sh, "DB_Yestech")
    
    col1, col2 = st.columns(2)
    with col1:
        aktywne_yes = len(df[df.get("Zakonczone_Arch", pd.Series()) != "TAK"]) if not df.empty else 0
        st.metric("Otwarte Transporty (Lejek)", aktywne_yes)
    with col2:
        braki_cmr_yes = len(df[df.get("CMR_Gotowe", pd.Series()) == "NIE"]) if not df.empty else 0
        st.metric("Oczekujące CMR", braki_cmr_yes)

    st.divider()
    widok = st.radio(
        "🔎 Obszar roboczy:",
        ["📍 Sprzedaż i Wycena", "🚚 Transport i Trasa", "📑 Rozliczenia i Dokumenty", "👁️ Widok Pełny"],
        horizontal=True
    )
    
    if widok == "📍 Sprzedaż i Wycena":
        kolumny = ["ID_Yestech", "Data_Zgloszenia", "Destynacja", "Gabaryt", "Status_Ofertowy", "Wycena_Dla_Basi", "Koszt_Rzeczywisty", "Marza_Info"]
    elif widok == "🚚 Transport i Trasa":
        kolumny = ["ID_Yestech", "Przewoznik", "Nr_Zlecenia_Zewn", "Data_Zlecenia_Tr", "Data_Zakonczenia_Uslugi"]
    elif widok == "📑 Rozliczenia i Dokumenty":
        kolumny = ["ID_Yestech", "CMR_Gotowe", "Nr_Faktury", "Data_Platnosci", "Faktura_Oplacona", "PP_Otrzymane", "Zakonczone_Arch"]
    else:
        kolumny = df.columns.tolist()
        
    konfiguracja_yestech = {
        **wspolna_konfiguracja,
        "Status_Ofertowy": st.column_config.SelectboxColumn("Status", options=["Nowe Zapytanie", "Czeka na akcept", "Akcept - szukam auta", "W drodze", "Zakończone"]),
        "Wycena_Dla_Basi": st.column_config.NumberColumn("Wycena", format="%d zł", min_value=0),
        "Koszt_Rzeczywisty": st.column_config.NumberColumn("Koszt", format="%d zł", min_value=0),
        "Marza_Info": st.column_config.NumberColumn("Marża", format="%d zł"),
    }

    edited_df = st.data_editor(df, column_order=kolumny, column_config=konfiguracja_yestech, num_rows="dynamic", use_container_width=True, hide_index=True, height=450)
    
    st.write("")
    if st.button("💾 Zapisz zmiany w bazie »", key="save_yestech"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "📊 Finanse i Raporty":
    st.title("Centrum Finansowe")
    st.info("Gotowe pod wdrożenie modułu skanującego zaległości.")
