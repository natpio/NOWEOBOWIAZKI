import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_option_menu import option_menu
import os

# Import modułów aplikacji
import mod_command_center
import mod_eventy
import mod_subrenty
import mod_yestech
import mod_finanse

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="SQM HUB", page_icon="✺", layout="wide")

# 2. ŁADOWANIE LOKALNEGO CSS
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style.css")

# 3. POŁĄCZENIE Z GOOGLE SHEETS
@st.cache_resource
def init_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    return client.open("NOWY PODZIAŁ OBOWIĄZKÓW")

# 4. EKRAN LOGOWANIA (Styl Zen/Japandi)
def login_screen():
    st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
            <div class='login-box'>
                <div style='font-size: 40px; margin-bottom: 10px; color: #C5A880;'>✺</div>
                <h2 style='color: #E2DCD3; letter-spacing: 2px; margin-bottom: 5px; font-weight: 600;'>SQM HUB</h2>
                <p style='color: #8C8477; font-size: 11px; letter-spacing: 3px; margin-bottom: 30px;'>ヤスミ・ハブ</p>
        """, unsafe_allow_html=True)
        
        pwd = st.text_input("Hasło dostępu / パスワード", type="password")
        
        # Oczekiwane hasło ze st.secrets (fallback na sqm2026)
        if st.button("WEJDŹ / 入る", use_container_width=True, type="primary"):
            if pwd == st.secrets.get("app_password", "sqm2026"):
                st.session_state["zalogowany"] = True
                st.rerun()
            else:
                st.error("Nieprawidłowe hasło.")
        st.markdown("</div>", unsafe_allow_html=True)

# 5. GŁÓWNA LOGIKA APLIKACJI
def main():
    if "zalogowany" not in st.session_state:
        st.session_state["zalogowany"] = False

    if not st.session_state["zalogowany"]:
        login_screen()
        return

    try:
        sh = init_connection()
    except Exception as e:
        st.error(f"Błąd połączenia z bazą danych (Google Sheets): {e}")
        return

    # --- MENU BOCZNE (SIDEBAR) ---
    with st.sidebar:
        # Nowe logo z japońskim podtytułem
        st.markdown('''
            <div class="sidebar-logo-text">
                <span style="font-size: 24px; margin-right: 5px;">✺</span> SQM <span>HUB</span>
            </div>
            <div class="sidebar-logo-sub">ヤスミ・ハブ</div>
        ''', unsafe_allow_html=True)
        
        wybrany_modul = option_menu(
            menu_title=None,
            options=[
                "COMMAND CENTER", 
                "EVENTY / TARGI", 
                "SUBRENTY", 
                "YESTECH EXPORT", 
                "FINANSE I RAPORTY"
            ],
            icons=["cpu", "truck", "box", "globe", "graph-up"],
            default_index=1,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#C5A880", "font-size": "14px"},
                "nav-link": {"color": "#8C8477", "font-size": "11px", "font-weight": "600", "letter-spacing": "1px", "text-align": "left", "margin":"4px 0", "border-radius": "4px"},
                "nav-link-selected": {"background-color": "rgba(197,168,128,0.05)", "color": "#C5A880", "border-left": "2px solid #C5A880"},
            }
        )
        
        st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)
        st.caption("👤 Piotr Dukiel | Logistics Mgr<br><span style='font-size: 9px; color: #5C554D;'>ロジスティクスマネージャー</span>", unsafe_allow_html=True)
        
        if st.button("🚪 WYLOGUJ\nログアウト", use_container_width=True):
            st.session_state["zalogowany"] = False
            st.rerun()

    # --- ROUTING MODUŁÓW ---
    if wybrany_modul == "COMMAND CENTER":
        mod_command_center.render(sh)
    elif wybrany_modul == "EVENTY / TARGI":
        mod_eventy.render(sh)
    elif wybrany_modul == "SUBRENTY":
        mod_subrenty.render(sh)
    elif wybrany_modul == "YESTECH EXPORT":
        mod_yestech.render(sh)
    elif wybrany_modul == "FINANSE I RAPORTY":
        mod_finanse.render(sh)

if __name__ == "__main__":
    main()
