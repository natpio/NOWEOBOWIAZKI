import streamlit as st
import base64

# Importowanie funkcji i logiki z naszych modułów
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
# 3. WERYFIKACJA STANU LOGOWANIA (HASŁO)
# ==========================================
if "zalogowany" not in st.session_state:
    st.session_state["zalogowany"] = False

# Jeśli użytkownik NIE JEST zalogowany - POKAŻ EKRAN LOGOWANIA
if not st.session_state["zalogowany"]:
    # Pobieramy hasło z ustawień Secrets w Streamlit Cloud. 
    # Jeśli zapomnisz dodać, domyślnie wpuści na hasło 'sqm2026'
    POPRAWNE_HASLO = st.secrets.get("app_password", "sqm2026")
    
    # Ukrywamy całkowicie boczny panel na ekranie logowania
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none !important; }
            .login-box {
                background-color: rgba(10, 25, 47, 0.85);
                backdrop-filter: blur(10px);
                padding: 40px;
                border-radius: 12px;
                border: 1px solid rgba(212, 175, 55, 0.5);
                text-align: center;
                max-width: 450px;
                margin: 100px auto;
                box-shadow: 0 12px 40px rgba(0,0,0,0.3);
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Wyśrodkowany kontener logowania
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown('<h2 style="color: #FFFFFF !important;">🔒 Logowanie do systemu</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color: #94A3B8;">Wprowadź hasło dostępu</p>', unsafe_allow_html=True)
        
        haslo_wpisane = st.text_input("Hasło", type="password", placeholder="Wpisz hasło...", label_visibility="collapsed")
        
        if st.button("Zaloguj", type="primary", use_container_width=True):
            if haslo_wpisane == POPRAWNE_HASLO:
                st.session_state["zalogowany"] = True
                st.success("Zalogowano pomyślnie!")
                st.rerun()
            else:
                st.error("❌ Nieprawidłowe hasło. Spróbuj ponownie.")
                
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 4. GŁÓWNA APLIKACJA (TYLKO DLA ZALOGOWANYCH)
# ==========================================
else:
    try:
        sh = init_connection()
    except Exception as e:
        st.error(f"❌ Krytyczny błąd połączenia z bazą danych: {e}")
        st.stop()

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
                Wersja systemu: 12.0 (Password Auth)<br><br>
                Użytkownik: Piotr Dukiel | Logistics Manager
            </div>
        """, unsafe_allow_html=True)
        
        # Przycisk wylogowania w pasku bocznym
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 Wyloguj", use_container_width=True):
            st.session_state["zalogowany"] = False
            st.rerun()

    # Routing
    if wybrany_modul == "🚚 Eventy / Targi":
        mod_eventy.render(sh)
    elif wybrany_modul == "📦 Subrenty":
        mod_subrenty.render(sh)
    elif wybrany_modul == "🌍 YESTECH Export":
        mod_yestech.render(sh)
    elif wybrany_modul == "📊 Finanse i Raporty":
        mod_finanse.render(sh)
