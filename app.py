import streamlit as st
import gspread
import pandas as pd

# Konfiguracja strony (musi być na samej górze)
st.set_page_config(page_title="SQM Transport Hub", page_icon="🚚", layout="wide")

# Funkcja nawiązująca połączenie z Google Sheets
@st.cache_resource
def init_connection():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open_by_key("1Vw72-HoJhhYMvI5FpcrmeFAhXfDF-mcjpSazyak9Tc4") 
    return sh

# Uniwersalna funkcja do pobierania danych i nagłówków z konkretnej zakładki
def load_data(sh, sheet_name):
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Jeśli arkusz ma tylko nagłówki (brak danych), pobieramy same nagłówki
    if df.empty:
        headers = worksheet.row_values(1)
        if headers:
            df = pd.DataFrame(columns=headers)
            
    return worksheet, df

# Uniwersalna funkcja zapisu
def save_data(worksheet, edited_df):
    with st.spinner('Zapisywanie zmian w Google Sheets...'):
        worksheet.clear()
        worksheet.update(values=[edited_df.columns.values.tolist()] + edited_df.values.tolist(), range_name='A1')
    st.success("✅ Dane zostały pomyślnie zaktualizowane!")

# Inicjalizacja połączenia
try:
    sh = init_connection()
except Exception as e:
    st.error(f"❌ Błąd autoryzacji: {e}")
    st.stop()

# --- MENU BOCZNE (NAWIGACJA) ---
st.sidebar.title("Moduły SQM")
wybrany_modul = st.sidebar.radio(
    "Przejdź do:",
    ["🚚 Eventy / Targi", "📦 Subrenty", "🌍 YESTECH Export", "💰 Finanse i Płatności"]
)

# --- LOGIKA MODUŁÓW ---

if wybrany_modul == "🚚 Eventy / Targi":
    st.title("🚚 Panel Operacyjny: Eventy i Targi")
    st.markdown("Zarządzanie flotą, wrzutkami i gotowością magazynu.")
    
    worksheet, df = load_data(sh, "DB_Eventy")
    
    st.markdown("### ⚙️ Wybierz etap do edycji:")
    widok = st.radio(
        "Wybierz widok:",
        ["1️⃣ Baza i Trasa", "2️⃣ Magazyn i Załadunek", "3️⃣ Dokumenty i Finanse", "👁️ Pokaż wszystko"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if widok == "1️⃣ Baza i Trasa":
        kolumny = ["ID_Zlecenia", "Nazwa_Targow", "Project_Manager", "Faza_Procesu", "Akcept_Alicji", "Typ_Pojazdu", "Przewoznik", "Data_Zlecenia_Tr"]
    elif widok == "2️⃣ Magazyn i Załadunek":
        kolumny = ["ID_Zlecenia", "Nazwa_Targow", "Status_Magazyn", "Magazyn_Powod", "ETA_Wydania", "Wrzutka_PM", "Koszt_Dodatkowy"]
    elif widok == "3️⃣ Dokumenty i Finanse":
        kolumny = ["ID_Zlecenia", "Nazwa_Targow", "CMR_Gotowe", "Nr_Zlecenia_Zewn", "Nr_Faktury", "Data_Zakonczenia_Uslugi", "Data_Platnosci", "Faktura_Oplacona", "PP_Otrzymane", "Zakonczone_Arch"]
    else:
        kolumny = df.columns.tolist()
        
    st.caption("💡 Zmiany wprowadzone w dowolnym widoku zapiszą się do całej bazy po kliknięciu zapisu.")
    
    edited_df = st.data_editor(df, column_order=kolumny, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    if st.button("💾 Zapisz zmiany - Eventy"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "📦 Subrenty":
    st.title("📦 Panel Operacyjny: Subrenty")
    st.markdown("Pilnowanie terminów zwrotów do partnerów i zewnętrznych dostawców.")
    
    worksheet, df = load_data(sh, "DB_Subrenty")
    
    st.markdown("### ⚙️ Wybierz etap do edycji:")
    widok = st.radio(
        "Wybierz widok:",
        ["1️⃣ Szczegóły i Status", "2️⃣ Logistyka", "3️⃣ Finanse i Zamknięcie", "👁️ Pokaż wszystko"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if widok == "1️⃣ Szczegóły i Status":
        kolumny = ["ID_Zlecenia", "Rodzaj_Zlecenia", "Dostawca", "Co_Jedzie", "Data_Zlecenia", "Deadline_Zwrotu", "Status_Subrentu"]
    elif widok == "2️⃣ Logistyka":
        kolumny = ["ID_Zlecenia", "Przewoznik_OUT", "List_Przewozowy", "CMR_Gotowe", "Nr_Zlecenia_Zewn", "Data_Zlecenia_Tr", "Data_Zakonczenia_Uslugi"]
    elif widok == "3️⃣ Finanse i Zamknięcie":
        kolumny = ["ID_Zlecenia", "Nr_Faktury", "Data_Platnosci", "Faktura_Oplacona", "PP_Otrzymane", "Zakonczone_Arch"]
    else:
        kolumny = df.columns.tolist()
        
    st.caption("💡 Zmiany wprowadzone w dowolnym widoku zapiszą się do całej bazy po kliknięciu zapisu.")

    edited_df = st.data_editor(df, column_order=kolumny, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    if st.button("💾 Zapisz zmiany - Subrenty"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "🌍 YESTECH Export":
    st.title("🌍 Panel Operacyjny: YESTECH Export")
    st.markdown("Lejek logistyczny dla działu handlowego.")
    
    worksheet, df = load_data(sh, "DB_Yestech")
    
    st.markdown("### ⚙️ Wybierz etap do edycji:")
    widok = st.radio(
        "Wybierz widok:",
        ["1️⃣ Sprzedaż i Wycena", "2️⃣ Transport i Trasa", "3️⃣ Rozliczenia i Dokumenty", "👁️ Pokaż wszystko"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if widok == "1️⃣ Sprzedaż i Wycena":
        kolumny = ["ID_Yestech", "Data_Zgloszenia", "Destynacja", "Gabaryt", "Status_Ofertowy", "Wycena_Dla_Basi", "Koszt_Rzeczywisty", "Marza_Info"]
    elif widok == "2️⃣ Transport i Trasa":
        kolumny = ["ID_Yestech", "Przewoznik", "Nr_Zlecenia_Zewn", "Data_Zlecenia_Tr", "Data_Zakonczenia_Uslugi"]
    elif widok == "3️⃣ Rozliczenia i Dokumenty":
        kolumny = ["ID_Yestech", "CMR_Gotowe", "Nr_Faktury", "Data_Platnosci", "Faktura_Oplacona", "PP_Otrzymane", "Zakonczone_Arch"]
    else:
        kolumny = df.columns.tolist()
        
    st.caption("💡 Zmiany wprowadzone w dowolnym widoku zapiszą się do całej bazy po kliknięciu zapisu.")

    edited_df = st.data_editor(df, column_order=kolumny, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    if st.button("💾 Zapisz zmiany - YESTECH"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "💰 Finanse i Płatności":
    st.title("💰 Moduł: Finanse i Płatności")
    st.info("Ten moduł jest w budowie. Tutaj pojawi się globalne zestawienie opóźnionych i nadchodzących płatności ze wszystkich trzech powyższych zakładek naraz.")
