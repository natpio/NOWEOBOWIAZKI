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
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    if st.button("💾 Zapisz zmiany - Eventy"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "📦 Subrenty":
    st.title("📦 Panel Operacyjny: Subrenty")
    st.markdown("Pilnowanie terminów zwrotów do Bartosza Krauze i zewnętrznych dostawców.")
    
    worksheet, df = load_data(sh, "DB_Subrenty")
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    if st.button("💾 Zapisz zmiany - Subrenty"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "🌍 YESTECH Export":
    st.title("🌍 Panel Operacyjny: YESTECH Export")
    st.markdown("Lejek logistyczny dla działu handlowego (Basia).")
    
    worksheet, df = load_data(sh, "DB_Yestech")
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    if st.button("💾 Zapisz zmiany - YESTECH"):
        save_data(worksheet, edited_df)

elif wybrany_modul == "💰 Finanse i Płatności":
    st.title("💰 Moduł: Finanse i Płatności")
    st.info("Ten moduł jest w budowie. Tutaj pojawi się globalne zestawienie opóźnionych i nadchodzących płatności ze wszystkich trzech powyższych zakładek naraz.")
