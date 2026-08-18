import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_option_menu import option_menu
import os
import base64

# Import modułów aplikacji
import mod_command_center
import mod_harmonogram
import mod_eventy
import mod_zlecenia_poboczne
import mod_subrenty
import mod_yestech
import mod_finanse
import mod_bazy_danych
import mod_generator_pdf 
import mod_empties

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="SQM HUB", page_icon="⚾", layout="wide")

# 2. ŁADOWANIE LOKALNEGO CSS Z OBSŁUGĄ BASE64 DLA TŁA I CZCIONEK
def local_css(file_name):
    st.markdown("""<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playball&family=Bebas+Neue&family=Inter:wght@400;500;600;700;800&family=Shippori+Mincho:wght@700&display=swap" rel="stylesheet">""", unsafe_allow_html=True)

    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            css_content = f.read()
        
        if os.path.exists("fuji_bg.png"):
            with open("fuji_bg.png", "rb") as img_f:
                b64_fuji = base64.b64encode(img_f.read()).decode()
            css_content = css_content.replace("url('fuji_bg.png')", f"url('data:image/png;base64,{b64_fuji}')")
            
        if os.path.exists("lantern_bg.png"):
            with open("lantern_bg.png", "rb") as img_l:
                b64_lantern = base64.b64encode(img_l.read()).decode()
            css_content = css_content.replace("url('lantern_bg.png')", f"url('data:image/png;base64,{b64_lantern}')")

        if os.path.exists("washi_bg.png"):
            with open("washi_bg.png", "rb") as img_w:
                b64_washi = base64.b64encode(img_w.read()).decode()
            css_content = css_content.replace("url('washi_bg.png')", f"url('data:image/png;base64,{b64_washi}')")
        elif os.path.exists("washi_bg.jpg"):
            with open("washi_bg.jpg", "rb") as img_w:
                b64_washi = base64.b64encode(img_w.read()).decode()
            css_content = css_content.replace("url('washi_bg.jpg')", f"url('data:image/jpeg;base64,{b64_washi}')")
            
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

local_css("style.css")

# 3. POŁĄCZENIE Z GOOGLE SHEETS
@st.cache_resource
def init_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    return client.open("NOWY PODZIAŁ OBOWIĄZKÓW")

# 4. EKRAN LOGOWANIA
def login_screen():
    st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""<div class='login-box' style='background-color: rgba(5, 10, 21, 0.9); padding: 40px; border-radius: 8px; border: 2px dashed #BA4949; text-align: center;'>
<div style='font-size: 40px; margin-bottom: 10px; color: #C5A880;'>⚾</div>
<h2 style='color: #E2DCD3; letter-spacing: 2px; margin-bottom: 5px; font-weight: 600;'>SQM HUB</h2>
<p style='color: #8C8477; font-size: 11px; letter-spacing: 3px; margin-bottom: 30px;'>ヤスミ・ハブ</p>""", unsafe_allow_html=True)
        pwd = st.text_input("Hasło dostępu / パスワード", type="password")
        if st.button("WEJDŹ / 入る", use_container_width=True, type="primary"):
            if pwd == st.secrets.get("app_password", "sqm2026"):
                st.session_state["zalogowany"] = True
                st.rerun()
            else:
                st.error("Nieprawidłowe hasło.")
        st.markdown("</div>", unsafe_allow_html=True)

# 5. GŁÓWNA LOGIKA APLIKACJI
def main():
    if "zalogowany" not in st.session_state: st.session_state["zalogowany"] = False
    if not st.session_state["zalogowany"]:
        login_screen()
        return

    try: 
        sh = init_connection()
    except Exception as e:
        st.error(f"Błąd połączenia z bazą danych (Google Sheets): {e}")
        return

    # Pobieranie Base64 tekstury papieru
    b64_washi_inline = ""
    if os.path.exists("washi_bg.png"):
        with open("washi_bg.png", "rb") as f: b64_washi_inline = base64.b64encode(f.read()).decode()
    elif os.path.exists("washi_bg.jpg"):
        with open("washi_bg.jpg", "rb") as f: b64_washi_inline = base64.b64encode(f.read()).decode()

    # --- MENU BOCZNE (SIDEBAR) ---
    with st.sidebar:
        st.markdown("""<div class="sidebar-logo-container">
<div style="font-size: 38px; color: #BA4949; margin-bottom: -15px; filter: drop-shadow(2px 2px 0px #050A15);">⚾</div>
<div class="sidebar-logo-text">SQM <span>HUB</span></div>
<div class="sidebar-logo-sub">Game Plan. Real Results.</div>
</div>""", unsafe_allow_html=True)
        
        opcje_menu = [
            "COMMAND CENTER", "HARMONOGRAM (GANTT)", "GENERATOR ZLECEŃ PRO", 
            "EVENTY / TARGI", "EMPTIES TOWER", "ZLECENIA POBOCZNE", "SUBRENTY", 
            "YESTECH EXPORT", "BAZY DANYCH / SŁOWNIKI", "FINANSE I RAPORTY"
        ]
        ikony_menu = ["cpu", "calendar-range", "file-earmark-pdf", "truck", "box-seam", "briefcase", "box", "globe", "database", "graph-up"]

        if "menu_option" not in st.session_state: st.session_state["menu_option"] = "COMMAND CENTER"
        st.session_state["menu_option"] = str(st.session_state["menu_option"]).upper()
        
        if st.session_state["menu_option"] not in opcje_menu:
            if "PRO" in st.session_state["menu_option"]: st.session_state["menu_option"] = "GENERATOR ZLECEŃ PRO"
            elif "POBOCZNE" in st.session_state["menu_option"]: st.session_state["menu_option"] = "ZLECENIA POBOCZNE"
            else: st.session_state["menu_option"] = "COMMAND CENTER"

        aktualny_indeks = opcje_menu.index(st.session_state["menu_option"])
        
        # PŁYWAJĄCE, W PEŁNI PRZEZROCZYSTE MENU KRAWĘDŹ W KRAWĘDŹ
        wybrany_modul = option_menu(
            menu_title=None,
            options=opcje_menu,
            icons=ikony_menu, 
            default_index=aktualny_indeks,
            styles={
                "container": {
                    "padding": "0!important", 
                    "margin": "0!important",
                    "background-color": "transparent !important", 
                    "width": "100%",
                    "border": "none"
                },
                "icon": {"color": "#C5A880", "font-size": "15px"},
                "nav-link": {
                    "color": "#E2DCD3", 
                    "font-size": "12px", 
                    "font-weight": "600", 
                    "font-family": "'Inter', sans-serif",
                    "letter-spacing": "0.5px", 
                    "text-align": "left", 
                    "margin": "0px", 
                    "padding": "12px 15px 12px 2.5rem",
                    "border-radius": "0px",
                    "transition": "all 0.2s ease"
                },
                "nav-link-selected": {
                    "background-color": "#F7F3EC", 
                    "background-image": f"url('data:image/png;base64,{b64_washi_inline}')" if b64_washi_inline else "none",
                    "background-blend-mode": "multiply",
                    "background-size": "cover",
                    "color": "#0A192F", 
                    "font-weight": "800",
                    "border-left": "6px solid #C5A880",
                    "border-radius": "0px",
                    "box-shadow": "none"
                },
            }
        )
        st.session_state["menu_option"] = wybrany_modul
        
        st.markdown(f"""<div class="sidebar-profile-card">
<div style="display: flex; align-items: center; gap: 15px;">
<div class="profile-avatar" style="background-image: url('data:image/png;base64,{b64_washi_inline}');">
<span style="color: #0A192F; font-weight: 800; font-size: 20px; font-family: 'Bebas Neue', sans-serif;">P</span>
</div>
<div>
<div style="color: #E2DCD3; font-family: 'Inter', sans-serif; font-weight: 700; font-size: 14px; letter-spacing: 0.5px;">Piotr Dukiel</div>
<div style="color: #C5A880; font-family: 'Inter', sans-serif; font-size: 10px; text-transform: uppercase; letter-spacing: 1px;">Logistics Manager</div>
<div style="color: #8C8477; font-size: 10px; font-style: italic; margin-top: 4px;">Let's hit it out of the park.<br><span style="color:#BA4949; font-weight:bold;">Szef!</span></div>
<div style="color: #BA4949; font-size: 14px; margin-top: 2px;">★ ★ ★</div>
</div>
</div>
</div>
<div class="refresh-graphic">
<div class="rg-title">REFRESH</div>
<div class="rg-subtitle">THE LINEUP</div>
<div class="rg-icon">🏏⚾🏏</div>
</div>
<div class="sidebar-buttons">""", unsafe_allow_html=True)

        if st.button("🔄 ODŚWIEŻ DANE / REFRESH", use_container_width=True): 
            st.cache_data.clear()
            st.rerun()

        if st.button("🚪 WYLOGUJ / ログアウト", use_container_width=True): 
            st.session_state["zalogowany"] = False
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ROUTING MODUŁÓW ---
    if wybrany_modul == "COMMAND CENTER": mod_command_center.render(sh)
    elif wybrany_modul == "HARMONOGRAM (GANTT)": mod_harmonogram.render(sh)
    elif wybrany_modul == "GENERATOR ZLECEŃ PRO": mod_generator_pdf.render(sh) 
    elif wybrany_modul == "EVENTY / TARGI": mod_eventy.render(sh)
    elif wybrany_modul == "EMPTIES TOWER": mod_empties.render(sh)
    elif wybrany_modul == "ZLECENIA POBOCZNE": mod_zlecenia_poboczne.render(sh)
    elif wybrany_modul == "SUBRENTY": mod_subrenty.render(sh)
    elif wybrany_modul == "YESTECH EXPORT": mod_yestech.render(sh)
    elif wybrany_modul == "BAZY DANYCH / SŁOWNIKI": mod_bazy_danych.render(sh)
    elif wybrany_modul == "FINANSE I RAPORTY": mod_finanse.render(sh)

if __name__ == "__main__":
    main()
