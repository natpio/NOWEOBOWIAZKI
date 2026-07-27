import streamlit as st
import gspread
import pandas as pd

# Konfiguracja strony
st.set_page_config(page_title="SQM Transport Hub", page_icon="🚚", layout="wide")
st.title("🚚 SQM Transport Hub - Panel Operacyjny")

# Funkcja nawiązująca połączenie z Google Sheets
@st.cache_resource
def init_connection():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    # Łączenie bezpośrednio po ID arkusza
    sh = gc.open_by_key("1Vw72-HoJhhYMvI5FpcrmeFAhXfDF-mcjpSazyak9Tc4") 
    return sh

try:
    sh = init_connection()
    worksheet = sh.worksheet("DB_Eventy") # Pamiętaj o utworzeniu takiej zakładki
    
    # Pobieranie danych z Google Sheets
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Jeśli arkusz jest zupełnie pusty, system potrzebuje pustej tabeli do pokazania
    if df.empty:
        df = pd.DataFrame(columns=["ID_Zlecenia", "Nazwa_Targow", "Project_Manager", "Typ_Pojazdu", "Zakonczone_Arch"])
    
    st.success("✅ Połączenie z bazą aktywne. Możesz edytować dane bezpośrednio w tabeli.")
    
    # Tworzenie interaktywnego edytora (num_rows="dynamic" pozwala dodawać nowe wiersze na dole)
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        use_container_width=True,
        hide_index=True
    )
    
    # Przycisk wymuszający fizyczny zapis do Google Sheets
    if st.button("💾 Zapisz zmiany w bazie"):
        with st.spinner('Zapisywanie zmian...'):
            # Najbezpieczniejsza metoda nadpisania danych: czyszczenie i wklejenie na nowo
            worksheet.clear()
            # Łączymy nagłówki kolumn z danymi i wysyłamy do arkusza
            worksheet.update(values=[edited_df.columns.values.tolist()] + edited_df.values.tolist(), range_name='A1')
        st.success("✅ Dane zostały zaktualizowane w Google Sheets!")

except Exception as e:
    st.error(f"❌ Błąd połączenia lub zapisu: {e}")
    st.info("Upewnij się, że w Google Sheets istnieje zakładka o nazwie 'DB_Eventy' oraz że udostępniłeś plik kontu serwisowemu.")
