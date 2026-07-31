import streamlit as st
from streamlit_option_menu import option_menu

# Importowanie funkcji i logiki z naszych modułów
from db import init_connection
import mod_command_center
import mod_eventy
import mod_subrenty
import mod_yestech
import mod_finanse

# ==========================================
# 1. KONFIGURACJA STRONY
# ==========================================
st.set_page_config(
    page_title="SQM Transport Hub 2.0", 
    page_icon="💠", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. ŁADOWANIE NOWEGO CSS
# ==========================================
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Plik style.css nie został znaleziony.")

load_css("style.css")

# ==========================================
# 3. WERYFIKACJA STANU LOGOWANIA (HASŁO)
# ==========================================
if "zalogowany" not in st.session_state:
    st.session_state["zalogowany"] = False

if not st.session_state["zalogowany"]:
    POPRAWNE_HASLO = st.secrets.get("app_password", "sqm2026")
    
    # Ukrywamy boczny panel na ekranie logowania
    st.markdown("""<style>[data-testid="stSidebar"] { display: none !important; }</style>""", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div style="margin-top: 10vh;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown('<h2 style="color: #F8FAFC !important;">💠 SQM Hub Login</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color: #94A3B8; margin-bottom: 25px;">Autoryzacja dostępu do systemu zarządzania</p>', unsafe_allow_html=True)
        
        haslo_wpisane = st.text_input("Hasło", type="password", placeholder="Wpisz hasło...", label_visibility="collapsed")
        
        if st.button("Zaloguj", type="primary", use_container_width=True):
            if haslo_wpisane == POPRAWNE_HASLO:
                st.session_state["zalogowany"] = True
                st.rerun()
            else:
                st.error("❌ Odmowa dostępu. Nieprawidłowe hasło.")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 4. GŁÓWNA APLIKACJA
# ==========================================
else:
    try:
        sh = init_connection()
    except Exception as e:
        st.error(f"❌ Błąd połączenia z bazą danych: {e}")
        st.stop()

    with st.sidebar:
        st.markdown('<div class="sidebar-logo-text">💠 SQM <span>HUB</span></div>', unsafe_allow_html=True)
        
        # --- NOWE PROFESJONALNE MENU ---
        wybrany_modul = option_menu(
            menu_title=None,
            options=["Command Center", "Eventy / Targi", "Subrenty", "YESTECH Export", "Finanse i Raporty"],
            icons=["grid-1x2", "truck", "box-seam", "globe-americas", "graph-up"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#D4AF37", "font-size": "16px"},
                "nav-link": {"color": "#94A3B8", "font-size": "14px", "text-align": "left", "margin":"2px 0"},
                "nav-link-selected": {"background-color": "rgba(212,175,55,0.1)", "color": "#D4AF37", "border-left": "3px solid #D4AF37"},
            }
        )
        
        st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 30px 0;'>", unsafe_allow_html=True)
        st.caption("👤 Piotr Dukiel | Logistics Mgr")
        
        if st.button("🚪 Wyloguj", use_container_width=True):
            st.session_state["zalogowany"] = False
            st.rerun()

    # Routing do odpowiednich zakładek
    if wybrany_modul == "Command Center":
        st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 25px;'>🎛️ Command Center</h2>", unsafe_allow_html=True)
        mod_command_center.render(sh)
    elif wybrany_modul == "Eventy / Targi":
        mod_eventy.render(sh)
    elif wybrany_modul == "Subrenty":
        mod_subrenty.render(sh)
    elif wybrany_modul == "YESTECH Export":
        mod_yestech.render(sh)
    elif wybrany_modul == "Finanse i Raporty":
        mod_finanse.render(sh)
