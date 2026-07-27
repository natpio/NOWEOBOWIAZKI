import streamlit as st
import gspread
import pandas as pd

# 1. KONFIGURACJA STRONY (Zawsze na górze)
st.set_page_config(page_title="SQM Transport Hub", page_icon="🚚", layout="wide", initial_sidebar_state="expanded")

# 2. WSTRZYKNIĘCIE CUSTOM CSS (Poziom 999 UI/UX)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Ukrycie domyślnego paska i stopki Streamlit dla czystego wyglądu aplikacji */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Stylizacja głównego tytułu */
    h1 {
        font-weight: 700 !important;
        color: #1E293B !important;
        letter-spacing: -1px;
    }
    
    /* Pływający, elegancki przycisk zapisu */
    .stButton > button {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.5rem 2rem !important;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2), 0 2px 4px -1px rgba(37, 99, 235, 0.1) !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3), 0 4px 6px -2px rgba(37, 99, 235, 0.15) !important;
    }
    
    /* Subtelne podświetlenie zakładek bocznych */
    [data-testid="stSidebarNav"] {
        background-color: #F8FAFC;
    }
    </style>
""", unsafe_allow_html=True)

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
    st.image("https://cdn-icons-png.flaticon.com/512/2769/2769339.png", width=60) # Ikona logo
    st.title("SQM TMS")
    st.markdown("---")
    wybrany_modul = st.radio(
        "Nawigacja:",
        ["🚚 Eventy / Targi", "📦 Subrenty", "🌍 YESTECH Export", "📊 Finanse i Raporty"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("Wersja systemu: 2.0.0 PRO")
    st.caption("Użytkownik: PM / Logistics")

# --- MODUŁY GŁÓWNE ---

if wybrany_modul == "🚚 Eventy / Targi":
    st.title("🚚 Eventy & Flota")
    st.markdown("Zarządzanie flotą, wrzutkami i gotowością magazynu.")
    
    worksheet, df = load_data(sh, "DB_Eventy")
    
    # Kafelki KPI (Dashboard)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Liczba aut (Aktywne)", len(df[df.get("Zakonczone_Arch", pd.Series()) != "TAK"]))
    with col2:
        st.metric("Oczekujące CMR", len(df[df.get("CMR_Gotowe", pd.Series()) == "NIE"]))
    with col3:
        st.metric("Status Magazynu", "Live 🟢")
    
    st.divider()

    # Logiczne filtry kolumn jako subtelne pigułki (Radio buttons)
    widok = st.radio(
        "🔎 Obszar roboczy:",
        ["📍 Baza i Trasa", "🏗️ Magazyn i Załadunek", "📑 Dokumenty i Finanse", "👁️ Widok Pełny (Master)"],
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
        
    # Specyficzna konfiguracja kolumn dla Eventów
    konfiguracja_eventy = {
        **wspolna_konfiguracja,
        "Faza_Procesu": st.column_config.SelectboxColumn("Faza", options=["Inicjacja", "Flota", "Dokumenty", "Załadunek", "Trasa", "Zamknięte"]),
        "Status_Magazyn": st.column_config.SelectboxColumn("Magazyn", options=["100% Gotowe", "Częściowo", "Opóźnione", "Brak gotowości"]),
        "Akcept_Alicji": st.column_config.SelectboxColumn("Akcept", options=opcje_tak_nie),
        "Wrzutka_PM": st.column_config.SelectboxColumn("Wrzutka", options=opcje_tak_nie),
        "Koszt_Dodatkowy": st.column_config.NumberColumn("Koszt Dod. (PLN)", format="%d zł", min_value=0),
    }

    # Interaktywny edytor danych
    edited_df = st.data_editor(
        df, 
        column_order=kolumny,
        column_config=konfiguracja_eventy,
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True,
        height=500
    )
    
    st.write("") # Pusty odstęp
    if st.button("💾 Zapisz zmiany w bazie »", key="save_eventy"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "📦 Subrenty":
    st.title("📦 Hub Subrentów")
    st.markdown("Ścisła kontrola terminów zwrotów do partnerów i zewnętrznych dostawców.")
    
    worksheet, df = load_data(sh, "DB_Subrenty")
    
    st.divider()
    widok = st.radio(
        "🔎 Obszar roboczy:",
        ["📍 Szczegóły i Status", "🚚 Logistyka", "📑 Finanse i Zamknięcie", "👁️ Widok Pełny (Master)"],
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

    edited_df = st.data_editor(
        df, 
        column_order=kolumny,
        column_config=konfiguracja_subrenty,
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True,
        height=500
    )
    
    st.write("")
    if st.button("💾 Zapisz zmiany w bazie »", key="save_subrenty"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "🌍 YESTECH Export":
    st.title("🌍 YESTECH Global")
    st.markdown("Zarządzanie lejkiem logistycznym dla działu handlowego.")
    
    worksheet, df = load_data(sh, "DB_Yestech")
    
    st.divider()
    widok = st.radio(
        "🔎 Obszar roboczy:",
        ["📍 Sprzedaż i Wycena", "🚚 Transport i Trasa", "📑 Rozliczenia i Dokumenty", "👁️ Widok Pełny (Master)"],
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

    edited_df = st.data_editor(
        df, 
        column_order=kolumny,
        column_config=konfiguracja_yestech,
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True,
        height=500
    )
    
    st.write("")
    if st.button("💾 Zapisz zmiany w bazie »", key="save_yestech"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "📊 Finanse i Raporty":
    st.title("📊 Centrum Finansowe")
    st.info("Tutaj wdrożymy potężny skrypt skanujący wszystkie 3 bazy pod kątem zaległych płatności (wg daty i statusów PP_Otrzymane). Moduł przygotowywany w kolejnym etapie wdrożenia.")
