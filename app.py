import streamlit as st
import base64

# Importowanie funkcji i logiki z naszych nowych modułów
from db import init_connection
import mod_eventy
import mod_subrenty
import mod_yestech
import mod_finanse

# ==========================================
# 1. KONFIGURACJA STRONY
# ==========================================
st.set_page_config(page_title="SQM Transport Hub PRO", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 2. ŁADOWANIE CSS ORAZ TŁA (BASE64)
# ==========================================
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Plik style.css nie został znaleziony. Upewnij się, że jest w tym samym folderze.")

@st.cache_data
def get_base64_image(file_name):
    try:
        with open(file_name, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

def set_backgrounds():
    main_bg_base64 = get_base64_image("tlo obowiazki.png")
    sidebar_bg_base64 = get_base64_image("tlo pasek.png")
    
    css = "<style>\n"
    if main_bg_base64:
        css += f"""
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/png;base64,{main_bg_base64}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-attachment: fixed !important;
        }}
        """
    if sidebar_bg_base64:
        css += f"""
        [data-testid="stSidebar"] > div:first-child {{
            background-image: url("data:image/png;base64,{sidebar_bg_base64}") !important;
            background-size: cover !important;
            background-position: bottom center !important;
            background-repeat: no-repeat !important;
            background-color: transparent !important;
        }}
        [data-testid="stSidebar"] {{
            background-color: transparent !important;
        }}
        """
    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)

load_css("style.css")
set_backgrounds()

# ==========================================
# 3. POŁĄCZENIE Z BAZĄ DANYCH
# ==========================================
try:
    sh = init_connection()
except Exception as e:
    st.error(f"❌ Krytyczny błąd połączenia z bazą danych: {e}")
    st.stop()

# ==========================================
# 4. PASEK BOCZNY - SYSTEM NAWIGACJI
# ==========================================
with st.sidebar:
    st.markdown("""
        <div class="sidebar-logo-text">
            🌍 <span>SQM TMS</span>
        </div>
    """, unsafe_allow_html=True)
    
    wybrany_modul = st.radio(
        "Nawigacja:",
        ["🚚 Eventy / Targi", "📦 Subrenty", "🌍 YESTECH Export", "📊 Finanse i Raporty"],
        label_visibility="collapsed"
    )
    
    st.markdown("""
        <div class="sidebar-footer">
            Wersja systemu: 11.0 (Modular Architecture)<br><br>
            Użytkownik: Piotr Dukiel | Logistics Manager
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 5. ROUTING - WŁĄCZANIE ODPOWIEDNIEGO MODUŁU
# ==========================================
if wybrany_modul == "🚚 Eventy / Targi":
    mod_eventy.render(sh)
elif wybrany_modul == "📦 Subrenty":
    mod_subrenty.render(sh)
elif wybrany_modul == "🌍 YESTECH Export":
    mod_yestech.render(sh)
elif wybrany_modul == "📊 Finanse i Raporty":
    mod_finanse.render(sh)
