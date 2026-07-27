import streamlit as st
import gspread
import pandas as pd

# Konfiguracja strony
st.set_page_config(page_title="SQM Transport Hub", page_icon="🚚", layout="wide")
st.title("🚚 SQM Transport Hub - Dashboard")

# Funkcja nawiązująca połączenie z Google Sheets (z cache'owaniem dla szybkości)
@st.cache_resource
def init_connection():
    # Używamy danych z pliku secrets.toml
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    # Podmień na dokładną nazwę Twojego pliku w Google Sheets!
    sh = gc.open("SQM_Transport_Hub") 
    return sh

try:
    # Inicjalizacja połączenia
    sh = init_connection()
    
    # Próba pobrania danych z pierwszej zakładki
    worksheet = sh.worksheet("DB_Eventy")
    data = worksheet.get_all_records()
    
    # Zamiana na obiekt Pandas DataFrame dla łatwiejszego wyświetlania
    df = pd.DataFrame(data)
    
    st.success("✅ Połączenie z bazą Google Sheets zakończone sukcesem!")
    
    # Wyświetlenie interaktywnej tabeli (na razie w trybie tylko do odczytu)
    st.subheader("Bieżące Eventy (Widok Operacyjny)")
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"❌ Błąd połączenia: {e}")
    st.info("Sprawdź, czy udostępniłeś arkusz adresowi e-mail bota oraz czy nazwa arkusza w kodzie się zgadza.")
