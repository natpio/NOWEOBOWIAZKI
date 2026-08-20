import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
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

# 4. FUNKCJA POMOCNICZA DO OBRAZÓW BASE64
def get_base64_image(file_name):
    if os.path.exists(file_name):
        with open(file_name, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        mime = "image/jpeg" if file_name.lower().endswith(('.jpg', '.jpeg')) else "image/png"
        return f"data:{mime};base64,{b64}"
    return "none"

# 5. NOWY, DEDYKOWANY EKRAN LOGOWANIA
def login_screen():
    b64_logo_banner = get_base64_image("logowanie.png") 
    
    st.markdown(f"""
    <style>
    /* 1. Całkowite ukrycie elementów nawigacji przed zalogowaniem */
    [data-testid="stSidebar"] {{ display: none !important; }}
    [data-testid="collapsedControl"] {{ display: none !important; }}
    
    /* 2. Formatowanie kontenera z nową grafiką tła */
    .login-hero {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-top: 10vh;
        margin-bottom: 2rem;
    }}
    
    .login-banner-img {{
        width: 100%;
        max-width: 850px;
        filter: drop-shadow(0px 20px 30px rgba(0,0,0,0.8));
        transition: transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1), filter 0.4s;
    }}
    
    .login-banner-img:hover {{
        transform: scale(1.02);
        filter: drop-shadow(0px 25px 40px rgba(0,0,0,0.95));
    }}
    
    /* 3. Stylowanie pola na hasło */
    div[data-testid="stTextInput"] label {{
        color: #C5A880 !important;
        font-family: 'Bebas Neue', sans-serif !important;
        letter-spacing: 3px;
        font-size: 22px !important;
        text-align: center;
        display: block;
        margin-bottom: 12px;
        text-shadow: 1px 1px 5px rgba(0,0,0,0.8);
    }}
    
    div[data-testid="stTextInput"] input {{
        background-color: rgba(5, 10, 21, 0.8) !important;
        border: 2px solid rgba(197, 168, 128, 0.3) !important;
        color: #FDFBF7 !important;
        text-align: center;
        font-size: 28px !important;
        letter-spacing: 12px;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: inset 0 5px 15px rgba(0,0,0,0.8);
        transition: all 0.3s ease;
    }}
    
    div[data-testid="stTextInput"] input:focus {{
        border-color: #BA4949 !important;
        box-shadow: 0 0 20px rgba(186, 73, 73, 0.5), inset 0 5px 15px rgba(0,0,0,0.8) !important;
    }}
    
    /* 4. Stylowanie gigantycznego przycisku ENTER */
    div[data-testid="stButton"] > button {{
        background: linear-gradient(to bottom, #8B2635, #5A1620) !important;
        border: 1px solid #BA4949 !important;
        color: #FDFBF7 !important;
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 28px !important;
        letter-spacing: 4px !important;
        border-radius: 12px !important;
        height: 75px !important;
        width: 100% !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.8) !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
        margin-top: 15px;
    }}
    
    div[data-testid="stButton"] > button:hover {{
        background: linear-gradient(to bottom, #BA4949, #8B2635) !important;
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 15px 35px rgba(186, 73, 73, 0.6) !important;
        color: #ffffff !important;
        border-color: #E2DCD3 !important;
    }}
    
    /* Personalizacja komunikatów błędów (Złe hasło) */
    div[data-testid="stNotification"] {{
        background-color: rgba(186, 73, 73, 0.1) !important;
        border: 1px solid #BA4949 !important;
        color: #FDFBF7 !important;
        border-radius: 8px !important;
        backdrop-filter: blur(5px);
    }}
    </style>
    
    <div class="login-hero">
        <img src="{b64_logo_banner}" class="login-banner-img">
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        pwd = st.text_input("AUTHORIZATION REQUIRED / 認証が必要", type="password")
        
        if st.button("ENTER HUB / 入る", use_container_width=True):
            if pwd == st.secrets.get("app_password", "sqm2026"):
                st.session_state["zalogowany"] = True
                st.rerun()
            else:
                st.error("ACCESS DENIED / アクセス拒否")

# 6. GŁÓWNA LOGIKA APLIKACJI
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

    b64_washi_inline = get_base64_image("washi_bg.png") if os.path.exists("washi_bg.png") else get_base64_image("washi_bg.jpg")
    b64_baseball_gear = get_base64_image("image_14a961.png")
    
    # Ładowanie grafik menu
    b64_cmd = get_base64_image("command.jpg")
    b64_gantt = get_base64_image("harmonogram.jpg")
    b64_gen = get_base64_image("GENERATOR.jpg")
    b64_evt = get_base64_image("eventy.jpg")
    b64_emp = get_base64_image("empties.jpg")
    b64_pob = get_base64_image("zlecenia poboczne.jpg")
    b64_sub = get_base64_image("subrenty.jpg")
    b64_yes = get_base64_image("yestech.jpg")
    b64_baz = get_base64_image("bazy danych.jpg")
    b64_fin = get_base64_image("finanse.jpg")
    
    # Ładowanie przycisków akcji
    b64_btn_refresh = get_base64_image("image_983cc3.png")
    b64_btn_logout = get_base64_image("image_983fe1.png")

    # --- MENU BOCZNE (SIDEBAR) ---
    with st.sidebar:
        # ELEMENT 1: LOGO (Markdown)
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

        if "menu_option" not in st.session_state: st.session_state["menu_option"] = "COMMAND CENTER"
        st.session_state["menu_option"] = str(st.session_state["menu_option"]).upper()
        
        if st.session_state["menu_option"] not in opcje_menu:
            if "PRO" in st.session_state["menu_option"]: st.session_state["menu_option"] = "GENERATOR ZLECEŃ PRO"
            elif "POBOCZNE" in st.session_state["menu_option"]: st.session_state["menu_option"] = "ZLECENIA POBOCZNE"
            else: st.session_state["menu_option"] = "COMMAND CENTER"

        # Dynamika podświetlenia aktywnego elementu (przesunięcie +3, bo 1 to Logo, 2 to styl CSS)
        active_idx = opcje_menu.index(st.session_state["menu_option"]) + 3

        # --- CSS MAGIA (Podmiana przycisków na grafiki) ---
        st.markdown(f"""
        <style>
        /* Styl bazowy dla wszystkich przycisków na pasku bocznym */
        [data-testid="stSidebar"] div[data-testid="stButton"] > button {{
            color: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            height: 82px !important; /* ZWIĘKSZONA WYSOKOŚĆ ABY PRZYCISKI MOGŁY BYĆ SZERSZE */
            width: 100% !important;
            background-size: contain !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            transition: transform 0.2s cubic-bezier(0.25, 0.8, 0.25, 1), filter 0.2s;
            margin-bottom: -8px !important; /* ZBLIŻENIE DO SIEBIE, ŻEBY PASEK NIE BYŁ ZA DŁUGI */
            padding: 0 !important;
        }}
        
        /* Ukrycie standardowego tekstu we wszystkich przyciskach */
        [data-testid="stSidebar"] div[data-testid="stButton"] > button p {{
            display: none !important;
        }}
        
        /* Efekt hover dla wszystkich przycisków */
        [data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {{
            transform: scale(1.03);
            filter: brightness(1.15);
        }}
        
        /* Wyróżnienie aktywnego przycisku z menu */
        [data-testid="stSidebar"] div.element-container:nth-of-type({active_idx}) button {{
            filter: brightness(1.25) drop-shadow(0px 0px 12px rgba(197, 168, 128, 0.6)) !important;
            transform: scale(1.04) !important;
            z-index: 10;
            position: relative;
        }}

        /* Przypisanie konkretnych grafik do konkretnych pozycji (od 3 do 12) */
        [data-testid="stSidebar"] div.element-container:nth-of-type(3) button {{ background-image: url('{b64_cmd}') !important; }}
        [data-testid="stSidebar"] div.element-container:nth-of-type(4) button {{ background-image: url('{b64_gantt}') !important; }}
        [data-testid="stSidebar"] div.element-container:nth-of-type(5) button {{ background-image: url('{b64_gen}') !important; }}
        [data-testid="stSidebar"] div.element-container:nth-of-type(6) button {{ background-image: url('{b64_evt}') !important; }}
        [data-testid="stSidebar"] div.element-container:nth-of-type(7) button {{ background-image: url('{b64_emp}') !important; }}
        [data-testid="stSidebar"] div.element-container:nth-of-type(8) button {{ background-image: url('{b64_pob}') !important; }}
        [data-testid="stSidebar"] div.element-container:nth-of-type(9) button {{ background-image: url('{b64_sub}') !important; }}
        [data-testid="stSidebar"] div.element-container:nth-of-type(10) button {{ background-image: url('{b64_yes}') !important; }}
        [data-testid="stSidebar"] div.element-container:nth-of-type(11) button {{ background-image: url('{b64_baz}') !important; }}
        [data-testid="stSidebar"] div.element-container:nth-of-type(12) button {{ background-image: url('{b64_fin}') !important; }}
        
        /* Przyciski Odśwież (14) i Wyloguj (15) po przesunięciu profilu */
        [data-testid="stSidebar"] div.element-container:nth-of-type(14) button {{ background-image: url('{b64_btn_refresh}') !important; margin-top: 10px !important; }}
        [data-testid="stSidebar"] div.element-container:nth-of-type(15) button {{ background-image: url('{b64_btn_logout}') !important; }}
        </style>
        """, unsafe_allow_html=True)

        # ELEMENTY 3-12: Rysowanie przycisków MENU
        if st.button("COMMAND CENTER", use_container_width=True): 
            st.session_state["menu_option"] = "COMMAND CENTER"
            st.rerun()
        if st.button("HARMONOGRAM (GANTT)", use_container_width=True): 
            st.session_state["menu_option"] = "HARMONOGRAM (GANTT)"
            st.rerun()
        if st.button("GENERATOR ZLECEŃ PRO", use_container_width=True): 
            st.session_state["menu_option"] = "GENERATOR ZLECEŃ PRO"
            st.rerun()
        if st.button("EVENTY / TARGI", use_container_width=True): 
            st.session_state["menu_option"] = "EVENTY / TARGI"
            st.rerun()
        if st.button("EMPTIES TOWER", use_container_width=True): 
            st.session_state["menu_option"] = "EMPTIES TOWER"
            st.rerun()
        if st.button("ZLECENIA POBOCZNE", use_container_width=True): 
            st.session_state["menu_option"] = "ZLECENIA POBOCZNE"
            st.rerun()
        if st.button("SUBRENTY", use_container_width=True): 
            st.session_state["menu_option"] = "SUBRENTY"
            st.rerun()
        if st.button("YESTECH EXPORT", use_container_width=True): 
            st.session_state["menu_option"] = "YESTECH EXPORT"
            st.rerun()
        if st.button("BAZY DANYCH / SŁOWNIKI", use_container_width=True): 
            st.session_state["menu_option"] = "BAZY DANYCH / SŁOWNIKI"
            st.rerun()
        if st.button("FINANSE I RAPORTY", use_container_width=True): 
            st.session_state["menu_option"] = "FINANSE I RAPORTY"
            st.rerun()

        # ELEMENT 13: Karta profilu + grafika (Markdown)
        st.markdown(f"""<div class="sidebar-profile-card">
<div style="display: flex; align-items: center; gap: 15px;">
<div class="profile-avatar" style="background-image: url('{b64_washi_inline}');">
<span style="color: #0A192F; font-weight: 800; font-size: 20px; font-family: 'Bebas Neue', sans-serif;">P</span>
</div>
<div>
<div style="color: #E2DCD3; font-family: 'Inter', sans-serif; font-weight: 700; font-size: 14px; letter-spacing: 0.5px;">Piotr Dukiel</div>
<div style="color: #C5A880; font-family: 'Inter', sans-serif; font-size: 10px; text-transform: uppercase; letter-spacing: 1px;">Logistics Manager</div>
<div style="color: #8C8477; font-size: 10px; font-style: italic; margin-top: 4px;">Let's hit it out of the park.<br><span style="color:#BA4949; font-weight:bold;">Chicago Cubs</span></div>
<div style="color: #BA4949; font-size: 14px; margin-top: 2px;">★ ★ ★ ★</div>
</div>
</div>
</div>
<div class="refresh-graphic" style="text-align: center; margin-top: 30px;">
<div class="rg-title">REFRESH</div>
<div class="rg-subtitle">THE LINEUP</div>
<img src="{b64_baseball_gear}" style="width: 75%; max-width: 160px; margin-top: 15px; margin-bottom: 5px; filter: drop-shadow(2px 5px 8px rgba(0,0,0,0.5));">
</div>
""", unsafe_allow_html=True)

        # ELEMENTY 14-15: Przyciski operacyjne
        if st.button("ODŚWIEŻ DANE / REFRESH", use_container_width=True): 
            st.cache_data.clear()
            st.rerun()

        if st.button("WYLOGUJ / ログアウト", use_container_width=True): 
            st.session_state["zalogowany"] = False
            st.rerun()

    # --- ROUTING MODUŁÓW ---
    wybrany_modul = st.session_state["menu_option"]
    
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
