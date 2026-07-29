import streamlit as st
import gspread
import pandas as pd
import datetime
import re
import plotly.graph_objects as go
import base64
import os

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
        [data-testid="stSidebar"] {{
            background-image: url("data:image/png;base64,{sidebar_bg_base64}") !important;
            background-size: cover !important;
            background-position: bottom center !important;
        }}
        """
    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)

load_css("style.css")
set_backgrounds()

# ==========================================
# 3. FUNKCJE BAZODANOWE I GENERATORY
# ==========================================
@st.cache_resource
def init_connection():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open_by_key("1Vw72-HoJhhYMvI5FpcrmeFAhXfDF-mcjpSazyak9Tc4") 
    return sh

def load_data(sh, sheet_name):
    try:
        worksheet = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=sheet_name, rows=1000, cols=20)

    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    if df.empty:
        headers = worksheet.row_values(1)
        if headers:
            df = pd.DataFrame(columns=headers)
            
    if sheet_name == "DB_Eventy":
        wymagane = ["CMR_Gotowe", "CMR_Podpisane_POD", "Faktura_Oplacona", "PP_Otrzymane", "Zakonczone_Arch"]
        for kol in wymagane:
            if kol not in df.columns: df[kol] = ""
        domyslne_kolumny = {
            "Typ_Transportu": "Zewnętrzny", "ID_Zlecenia": "", "Nazwa_Targow": "",
            "Faza_Procesu": "Inicjacja", "Typ_Pojazdu": "", "Przewoznik": "",
            "Data_Zlecenia_Tr": str(datetime.date.today()), "Status_Magazyn": "Brak gotowości",
            "Notatki": "", "Koszt_Transportu_EUR": 0.0, "Nr_Zlecenia_Zewn": "", "Nr_Faktury": "",
            "Data_Zakonczenia_Uslugi": "", "Data_Platnosci": ""
        }
        for kol, val in domyslne_kolumny.items():
            if kol not in df.columns: df[kol] = val

    elif sheet_name == "DB_Subrenty":
        domyslne_subrenty = {
            "ID_Subrentu": "", "Nazwa_Sprzetu": "", "Firma_Zewnetrzna": "",
            "Data_Odbioru": str(datetime.date.today()), "Data_Zwrotu": str(datetime.date.today()),
            "Status": "Zamówione", "Koszt": 0.0, "Notatki": "", "Zakonczone_Arch": "NIE"
        }
        for kol, val in domyslne_subrenty.items():
            if kol not in df.columns: df[kol] = val
                
    elif sheet_name == "DB_Yestech":
        domyslne_yestech = {
            "ID_Yestech": "", "Data_Zgloszenia": str(datetime.date.today()),
            "Destynacja": "", "Gabaryt": "", "Status_Ofertowy": "1. Zapytanie",
            "Wycena_Dla_Basi": 0.0, "Koszt_Rzeczywisty": 0.0, "Marza_Info": "",
            "Przewoznik": "", "CMR_Gotowe": "", "Nr_Zlecenia_Zewn": "",
            "Nr_Faktury": "", "Data_Zlecenia_Tr": "", "Data_Zakonczenia_Uslugi": "",
            "Data_Platnosci": "", "Faktura_Oplacona": "", "PP_Otrzymane": "",
            "Zakonczone_Arch": "NIE"
        }
        for kol in domyslne_yestech.keys():
            if kol not in df.columns: df[kol] = domyslne_yestech[kol]
        df = df[list(domyslne_yestech.keys())]

    elif sheet_name == "DB_Katalog_Firm":
        if "Nazwa_Firmy" not in df.columns: df["Nazwa_Firmy"] = ""
                
    return worksheet, df

def save_data(worksheet, edited_df):
    with st.spinner('Synchronizacja z chmurą Google... ☁️'):
        worksheet.clear()
        worksheet.update(values=[edited_df.columns.values.tolist()] + edited_df.values.tolist(), range_name='A1')
    st.toast("Zmiany zapisane pomyślnie!", icon="✅")

def generuj_smart_id(df, kolumna_glowna, kolumna_dodatkowa, nazwa_kolumny_id="ID_Zlecenia"):
    licznik_elementow = {}
    if nazwa_kolumny_id not in df.columns:
        df[nazwa_kolumny_id] = ""
    for idx, row in df.iterrows():
        wartosc1 = str(row.get(kolumna_glowna, '')).strip().upper()
        wartosc2 = str(row.get(kolumna_dodatkowa, '')).strip().upper()
        if not wartosc1 and not wartosc2: continue
        if wartosc1 not in licznik_elementow: licznik_elementow[wartosc1] = 1
        else: licznik_elementow[wartosc1] += 1
        czesc1 = re.sub(r'[^A-Z0-9]', '', wartosc1)[:4] if wartosc1 else "BRAK"
        czesc2 = re.sub(r'[^A-Z0-9]', '', wartosc2)[:4] if wartosc2 else "BRAK"
        numer = str(licznik_elementow[wartosc1]).zfill(2)
        df.at[idx, nazwa_kolumny_id] = f"{czesc1}-{czesc2}-{numer}"
    return df

try:
    sh = init_connection()
except Exception as e:
    st.error(f"❌ Krytyczny błąd połączenia z bazą: {e}")
    st.stop()

# ==========================================
# 4. PASEK BOCZNY
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
            Wersja systemu: 9.5.0 (Global Vision UI)<br><br>
            Użytkownik: Piotr Dukiel | Logistics Manager
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 🚚 MODUŁ: EVENTY / TARGI
# ==========================================
if wybrany_modul == "🚚 Eventy / Targi":
    st.title("🚚 Eventy & Flota")
    worksheet, df = load_data(sh, "DB_Eventy")
    
    df_aktywne = df[df.get("Zakonczone_Arch", pd.Series()) != "TAK"] if not df.empty else df
    braki_pod = len(df_aktywne[df_aktywne.get("CMR_Podpisane_POD", pd.Series()) == "NIE"]) if not df_aktywne.empty else 0
    
    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card kpi-blue">
                <div class="kpi-header">Aktywne Transporty</div>
                <div class="kpi-value">{len(df_aktywne)}</div>
                <div class="kpi-icon-bg">🚚</div>
            </div>
            <div class="kpi-card kpi-gold">
                <div class="kpi-header">Oczekujące Zwroty POD</div>
                <div class="kpi-value">{braki_pod}</div>
                <div class="kpi-icon-bg">📄</div>
            </div>
            <div class="kpi-card kpi-green">
                <div class="kpi-header">Status Bazy Danych</div>
                <div class="kpi-value" style="font-size: 26px; padding-top: 5px;">Synchronizowana</div>
                <div class="kpi-icon-bg">✅</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_podglad, tab_formularz, tab_archiwum = st.tabs(["📊 Aktywne", "➕ Dodaj Zlecenie", "📦 Archiwum"])

    with tab_podglad:
        if not df_aktywne.empty:
            st.dataframe(df_aktywne, use_container_width=True, hide_index=True)
        else:
            st.info("Brak aktywnych transportów w bazie.")

    with tab_formularz:
        with st.form("form_event_pro", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                nazwa_targow = st.text_input("Nazwa Targów / Eventu *")
                typ_transportu = st.selectbox("Typ Transportu", ["Zewnętrzny", "Własny SQM"])
                typ_pojazdu = st.text_input("Typ Pojazdu (np. Solówka 12t, Bus)")
            with f_col2:
                przewoznik = st.text_input("Przewoźnik / Kierowca *")
                faza_procesu = st.selectbox("Faza Procesu", ["Inicjacja", "Flota", "Dokumenty", "Załadunek", "Trasa", "Zamknięte"])
                status_magazyn = st.selectbox("Status Magazyn", ["Brak gotowości", "Częściowo", "100% Gotowe"])

            notatki = st.text_area("Notatki Dodatkowe")
            
            st.markdown("### 🛫 Dokumenty Startowe")
            cmr_gotowe = st.selectbox("Wystawione CMR przed wyjazdem?", ["NIE", "TAK"])
            
            st.markdown("### 🏁 Rozliczenie i Dowód Dostawy (POD)")
            d_col1, d_col2, d_col3 = st.columns(3)
            with d_col1: cmr_podpisane = st.selectbox("Otrzymano podpisane CMR (POD)?", ["NIE", "TAK"])
            with d_col2: pp_otrzymane = st.selectbox("PP Otrzymane?", ["", "NIE", "TAK"])
            with d_col3: faktura_opl = st.selectbox("Faktura Opłacona?", ["", "NIE", "TAK"])

            if typ_transportu == "Zewnętrzny":
                e_col1, e_col2, e_col3 = st.columns(3)
                with e_col1: koszt_transportu = st.number_input("Koszt Transportu (€)", min_value=0.0, value=0.0, step=50.0)
                with e_col2: nr_zlecenia_zewn = st.text_input("Nr Zlecenia Zewnętrznego")
                with e_col3: nr_faktury = st.text_input("Nr Faktury Przewoźnika")
            else:
                koszt_transportu = 0.0
                nr_zlecenia_zewn = "FLOTA WŁASNA"
                nr_faktury = "N/A"

            if st.form_submit_button("🚀 Zapisz Zlecenie"):
                if not nazwa_targow or not przewoznik:
                    st.error("❌ Musisz uzupełnić nazwę targów oraz przewoźnika!")
                else:
                    nowy_wiersz = {
                        "ID_Zlecenia": "", "Nazwa_Targow": nazwa_targow, "Typ_Transportu": typ_transportu,
                        "Faza_Procesu": faza_procesu, "Typ_Pojazdu": typ_pojazdu, "Przewoznik": przewoznik,
                        "Data_Zlecenia_Tr": str(datetime.date.today()), "Status_Magazyn": status_magazyn,
                        "Notatki": notatki, "Koszt_Transportu_EUR": koszt_transportu, "CMR_Gotowe": cmr_gotowe, 
                        "CMR_Podpisane_POD": cmr_podpisane, "Nr_Zlecenia_Zewn": nr_zlecenia_zewn, 
                        "Nr_Faktury": nr_faktury, "Data_Zakonczenia_Uslugi": "", "Data_Platnosci": "",
                        "Faktura_Oplacona": faktura_opl, "PP_Otrzymane": pp_otrzymane, "Zakonczone_Arch": "NIE"
                    }
                    df = pd.concat([df, pd.DataFrame([nowy_wiersz])], ignore_index=True)
                    df = generuj_smart_id(df, "Nazwa_Targow", "Przewoznik", "ID_Zlecenia")
                    save_data(worksheet, df)
                    st.success("🎉 Dodano zlecenie!")
                    st.rerun()

    with tab_archiwum:
        df_arch = df[df.get("Zakonczone_Arch", pd.Series()) == "TAK"] if not df.empty else pd.DataFrame()
        if not df_arch.empty:
            st.dataframe(df_arch, use_container_width=True, hide_index=True)

# ==========================================
# 📦 MODUŁ: SUBRENTY
# ==========================================
elif wybrany_modul == "📦 Subrenty":
    st.title("📦 Hub Wypożyczeń (Subrenty)")
    
    worksheet_sub, df_sub = load_data(sh, "DB_Subrenty")
    worksheet_firmy, df_firmy = load_data(sh, "DB_Katalog_Firm")
    
    katalog_firm = df_firmy["Nazwa_Firmy"].dropna().unique().tolist() if not df_firmy.empty else []
    df_aktywne_sub = df_sub[df_sub.get("Zakonczone_Arch", pd.Series()) != "TAK"] if not df_sub.empty else df_sub
    
    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card kpi-blue">
                <div class="kpi-header">Aktywne Wypożyczenia</div>
                <div class="kpi-value">{len(df_aktywne_sub)}</div>
                <div class="kpi-icon-bg">📦</div>
            </div>
            <div class="kpi-card kpi-gold">
                <div class="kpi-header">Firmy Zewnętrzne (Baza)</div>
                <div class="kpi-value">{len(katalog_firm)}</div>
                <div class="kpi-icon-bg">🏢</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_podglad, tab_formularz, tab_archiwum = st.tabs(["📊 Aktywne Wypożyczenia", "➕ Dodaj Subrent", "📦 Archiwum"])

    with tab_podglad:
        if not df_aktywne_sub.empty: st.dataframe(df_aktywne_sub, use_container_width=True, hide_index=True)

    with tab_formularz:
        with st.form("form_subrent", clear_on_submit=True):
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                nazwa_sprzetu = st.text_input("Nazwa Sprzętu / Cel Wypożyczenia *")
                wybor_firmy = st.selectbox("Wybierz z książki adresowej *", ["-- Dodaj nową firmę --"] + sorted(katalog_firm))
                nowa_firma = st.text_input("Nowa firma (jeśli brak na liście wyżej)")
            with s_col2:
                status_sub = st.selectbox("Status", ["Zamówione", "Odebrane", "Zwrócone", "Rozliczone"])
                koszt = st.number_input("Koszt całkowity (€)", min_value=0.0, value=0.0, step=50.0)

            d_col1, d_col2 = st.columns(2)
            with d_col1: data_od = st.date_input("Data Odbioru")
            with d_col2: data_do = st.date_input("Data Zwrotu")
                
            notatki_sub = st.text_area("Dodatkowe Notatki")

            if st.form_submit_button("💾 Zapisz Subrent"):
                firma_docelowa = nowa_firma.strip() if wybor_firmy == "-- Dodaj nową firmę --" else wybor_firmy
                if not nazwa_sprzetu or not firma_docelowa:
                    st.error("❌ Musisz uzupełnić nazwę sprzętu oraz wskazać firmę zewnętrzną!")
                else:
                    if firma_docelowa not in katalog_firm:
                        df_firmy = pd.concat([df_firmy, pd.DataFrame([{"Nazwa_Firmy": firma_docelowa}])], ignore_index=True)
                        save_data(worksheet_firmy, df_firmy)
                        
                    czy_arch = "TAK" if status_sub in ["Zwrócone", "Rozliczone"] else "NIE"
                    nowy_wiersz = {
                        "ID_Subrentu": "", "Nazwa_Sprzetu": nazwa_sprzetu, "Firma_Zewnetrzna": firma_docelowa,
                        "Data_Odbioru": str(data_od), "Data_Zwrotu": str(data_do),
                        "Status": status_sub, "Koszt": koszt, "Notatki": notatki_sub, "Zakonczone_Arch": czy_arch
                    }
                    df_sub = pd.concat([df_sub, pd.DataFrame([nowy_wiersz])], ignore_index=True)
                    df_sub = generuj_smart_id(df_sub, "Firma_Zewnetrzna", "Nazwa_Sprzetu", "ID_Subrentu")
                    save_data(worksheet_sub, df_sub)
                    st.success(f"🎉 Zapisano subrent!")
                    st.rerun()

    with tab_archiwum:
        df_arch_sub = df_sub[df_sub.get("Zakonczone_Arch", pd.Series()) == "TAK"] if not df_sub.empty else pd.DataFrame()
        if not df_arch_sub.empty: st.dataframe(df_arch_sub, use_container_width=True, hide_index=True)

# ==========================================
# 🌍 MODUŁ: YESTECH EXPORT
# ==========================================
elif wybrany_modul == "🌍 YESTECH Export":
    st.title("🌍 YESTECH Global (Lejek Eksportowy)")
    
    worksheet_yt, df_yt = load_data(sh, "DB_Yestech")
    df_aktywne_yt = df_yt[df_yt.get("Zakonczone_Arch", pd.Series()) != "TAK"] if not df_yt.empty else df_yt
    oczekujace = len(df_aktywne_yt[df_aktywne_yt.get("Status_Ofertowy", pd.Series()) == "1. Zapytanie"]) if not df_aktywne_yt.empty else 0
    
    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card kpi-blue">
                <div class="kpi-header">Aktywne Projekty (W toku)</div>
                <div class="kpi-value">{len(df_aktywne_yt)}</div>
                <div class="kpi-icon-bg">🌍</div>
            </div>
            <div class="kpi-card kpi-gold">
                <div class="kpi-header">Oczekujące na wycenę</div>
                <div class="kpi-value">{oczekujace}</div>
                <div class="kpi-icon-bg">⏳</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_podglad, tab_formularz, tab_archiwum = st.tabs(["📊 Lejek (Podgląd)", "➕ Zgłoś / Aktualizuj Temat", "📦 Archiwum"])

    with tab_podglad:
        if not df_aktywne_yt.empty: st.dataframe(df_aktywne_yt, use_container_width=True, hide_index=True)

    with tab_formularz:
        with st.form("form_yestech", clear_on_submit=True):
            y_col1, y_col2 = st.columns(2)
            with y_col1:
                destynacja = st.text_input("Destynacja *")
                gabaryt = st.text_input("Gabaryt (np. 2 palety, 150kg)")
                przewoznik = st.text_input("Przewoźnik")
            with y_col2:
                status_ofertowy = st.selectbox("Status Ofertowy", ["1. Zapytanie", "2. Wycenione", "3. Akceptacja", "4. Zlecone", "5. Zakończone"])
                data_zgloszenia = st.date_input("Data Zgłoszenia", value=datetime.date.today())
                data_zlecenia_tr = st.date_input("Data Zlecenia Transportu", value=None)

            st.markdown("### 💰 Finanse (€)")
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1: wycena_dla_basi = st.number_input("Wycena dla Basi (€)", min_value=0.0, value=0.0, step=50.0)
            with f_col2: koszt_rzeczywisty = st.number_input("Koszt Rzeczywisty (€)", min_value=0.0, value=0.0, step=50.0)
            with f_col3: marza_info = st.text_input("Marża / Info dodatkowe")

            st.markdown("### 📄 Dokumenty i Daty")
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                nr_zlecenia_zewn = st.text_input("Nr Zlecenia Zewnętrznego")
                nr_faktury = st.text_input("Nr Faktury")
                cmr_gotowe = st.selectbox("CMR Gotowe?", ["", "NIE", "TAK"])
            with d_col2:
                faktura_opl = st.selectbox("Faktura Opłacona?", ["", "NIE", "TAK"])
                pp_otrzymane = st.selectbox("PP Otrzymane?", ["", "NIE", "TAK"])
                data_zakonczenia = st.date_input("Data Zakończenia Usługi (obliczy płatność +30 dni)", value=None)

            zakonczone_arch = st.selectbox("Zakończone / Przenieś do archiwum?", ["NIE", "TAK"])

            if st.form_submit_button("💾 Aktualizuj Lejek YESTECH"):
                if not destynacja:
                    st.error("❌ Musisz podać destynację!")
                else:
                    data_platnosci = str(data_zakonczenia + datetime.timedelta(days=30)) if data_zakonczenia else ""
                    nowy_wiersz = {
                        "ID_Yestech": "", "Data_Zgloszenia": str(data_zgloszenia) if data_zgloszenia else "",
                        "Destynacja": destynacja, "Gabaryt": gabaryt, "Status_Ofertowy": status_ofertowy,
                        "Wycena_Dla_Basi": wycena_dla_basi, "Koszt_Rzeczywisty": koszt_rzeczywisty, "Marza_Info": marza_info,
                        "Przewoznik": przewoznik, "CMR_Gotowe": cmr_gotowe, "Nr_Zlecenia_Zewn": nr_zlecenia_zewn,
                        "Nr_Faktury": nr_faktury, "Data_Zlecenia_Tr": str(data_zlecenia_tr) if data_zlecenia_tr else "",
                        "Data_Zakonczenia_Uslugi": str(data_zakonczenia) if data_zakonczenia else "", 
                        "Data_Platnosci": data_platnosci, "Faktura_Oplacona": faktura_opl, 
                        "PP_Otrzymane": pp_otrzymane, "Zakonczone_Arch": zakonczone_arch
                    }
                    df_yt = pd.concat([df_yt, pd.DataFrame([nowy_wiersz])], ignore_index=True)
                    df_yt = df_yt[list(nowy_wiersz.keys())] 
                    df_yt = generuj_smart_id(df_yt, "Destynacja", "Przewoznik", "ID_Yestech")
                    save_data(worksheet_yt, df_yt)
                    st.success("🎉 Projekt zapisany!")
                    st.rerun()

    with tab_archiwum:
        df_arch_yt = df_yt[df_yt.get("Zakonczone_Arch", pd.Series()) == "TAK"] if not df_yt.empty else pd.DataFrame()
        if not df_arch_yt.empty: st.dataframe(df_arch_yt, use_container_width=True, hide_index=True)

# ==========================================
# 📊 MODUŁ: FINANSE I RAPORTY
# ==========================================
elif wybrany_modul == "📊 Finanse i Raporty":
    
    col_title, col_currency = st.columns([5, 1])
    with col_title: st.markdown('<h2 style="margin: 0; padding-top: 10px;">📊 Centrum Finansowe</h2>', unsafe_allow_html=True)
    with col_currency: st.selectbox("Waluta", ["Waluta: EUR €"], label_visibility="collapsed")
    st.markdown("<br>", unsafe_allow_html=True)
    
    _, df_ev = load_data(sh, "DB_Eventy")
    _, df_yt = load_data(sh, "DB_Yestech")
    _, df_sub = load_data(sh, "DB_Subrenty")
    dzisiaj = pd.Timestamp.today().normalize()
    
    spoznione_ev, spoznione_yt = pd.DataFrame(), pd.DataFrame()
    if not df_ev.empty and "Data_Platnosci" in df_ev.columns:
        df_ev['Data_DT'] = pd.to_datetime(df_ev['Data_Platnosci'], errors='coerce')
        spoznione_ev = df_ev[(df_ev['Data_DT'] < dzisiaj) & (df_ev['Faktura_Oplacona'] != "TAK")]
    if not df_yt.empty and "Data_Platnosci" in df_yt.columns:
        df_yt['Data_DT'] = pd.to_datetime(df_yt['Data_Platnosci'], errors='coerce')
        spoznione_yt = df_yt[(df_yt['Data_DT'] < dzisiaj) & (df_yt['Faktura_Oplacona'] != "TAK")]
        
    spoznione_count = len(spoznione_ev) + len(spoznione_yt)
    
    braki_ev = pd.DataFrame()
    if not df_ev.empty and "Zakonczone_Arch" in df_ev.columns:
        braki_ev = df_ev[(df_ev['Zakonczone_Arch'] == 'TAK') & ((df_ev['CMR_Podpisane_POD'] == 'NIE') | (df_ev['Nr_Faktury'] == ''))]
    braki_count = len(braki_ev)

    tab_alerty, tab_koszty, tab_rentownosc = st.tabs(["🚨 Alerty i Braki", "💶 Wydatki per Przewoźnik", "📈 Rentowność YESTECH"])

    with tab_alerty:
        t_spozn = "Brak przeterminowanych płatności!" if spoznione_count == 0 else f"Wykryto {spoznione_count} spóźnień!"
        c_spozn = "text-green" if spoznione_count == 0 else "text-red"
        
        t_braki = "Brak blokad rozliczeń!" if braki_count == 0 else f"Wykryto {braki_count} blokad!"
        c_braki = "text-gray" if braki_count == 0 else "text-yellow"

        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card kpi-red">
                <div class="kpi-header">Przeterminowane płatności</div>
                <div class="kpi-value">{spoznione_count}</div>
                <div class="kpi-subtext {c_spozn}">{t_spozn}</div>
                <div class="kpi-btn">Pokaż szczegóły</div>
                <div class="kpi-icon-bg">💰</div>
            </div>
            <div class="kpi-card kpi-yellow">
                <div class="kpi-header">Blokady Rozliczeń (Brak POD/Faktury)</div>
                <div class="kpi-value">{braki_count}</div>
                <div class="kpi-subtext {c_braki}">{t_braki}</div>
                <div class="kpi-btn">Pokaż szczegóły</div>
                <div class="kpi-icon-bg">📄</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">Monthly Financial Flow</div>', unsafe_allow_html=True)
        miesiace = ['01.2026', '02.2026', '03.2026', '04.2026', '05.2026', '06.2026']
        przychody = [600, 850, 750, 680, 700, 750]
        koszty = [200, 250, 220, 180, 240, 150]
        zysk = [400, 600, 530, 500, 460, 600]

        fig = go.Figure()
        fig.add_trace(go.Bar(x=miesiace, y=przychody, name='Przychody', marker_color='#3B82F6', width=0.25))
        fig.add_trace(go.Bar(x=miesiace, y=koszty, name='Koszty', marker_color='#10B981', width=0.25))
        fig.add_trace(go.Scatter(x=miesiace, y=zysk, name='Zysk', mode='lines+markers', line=dict(color='#8B5CF6', width=2)))

        fig.update_layout(
            plot_bgcolor='rgba(255,255,255,0.7)',
            paper_bgcolor='rgba(255,255,255,0.5)',
            font=dict(color='#0A192F'),
            margin=dict(l=0, r=0, t=10, b=0),
            height=250,
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, linecolor='#CBD5E1', tickfont=dict(color='#0A192F')),
            yaxis=dict(showgrid=True, gridcolor='#E2E8F0', zerolinecolor='#CBD5E1', tickfont=dict(color='#0A192F')),
            barmode='group'
        )
        st.markdown('<div style="background: rgba(255,255,255,0.85); backdrop-filter: blur(10px); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.5);">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div><br>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">Ostatnie Płatności i Blokady</div>', unsafe_allow_html=True)
        if spoznione_count == 0 and braki_count == 0:
            st.markdown("""
            <table style="width:100%; border-collapse: collapse; background: rgba(255,255,255,0.85); backdrop-filter: blur(5px); border: 1px solid #E2E8F0; border-bottom: none; border-radius: 8px 8px 0 0;">
                <tr style="color: #0A192F; font-size: 13px; border-bottom: 2px solid rgba(10, 25, 47, 0.2); text-align: left;">
                    <th style="padding: 12px;">ID Płatności</th>
                    <th style="padding: 12px;">Klient</th>
                    <th style="padding: 12px;">Kwota</th>
                    <th style="padding: 12px;">Status</th>
                    <th style="padding: 12px;">Powód Blokady</th>
                </tr>
            </table>
            <div class="empty-table-msg">Brak aktywnych pozycji</div>
            """, unsafe_allow_html=True)
        else:
            if not spoznione_ev.empty: st.dataframe(spoznione_ev[['ID_Zlecenia', 'Przewoznik', 'Koszt_Transportu_EUR', 'Data_Platnosci']], use_container_width=True)
            if not braki_ev.empty: st.dataframe(braki_ev[['ID_Zlecenia', 'Przewoznik', 'CMR_Podpisane_POD', 'Nr_Faktury']], use_container_width=True)

    with tab_koszty:
        st.subheader("Zestawienie kosztów u partnerów zewnętrznych")
        k_col1, k_col2 = st.columns(2)
        with k_col1:
            st.markdown("**🚚 Transport (Eventy)**")
            if not df_ev.empty and "Koszt_Transportu_EUR" in df_ev.columns:
                df_ev['Koszt_Transportu_EUR'] = pd.to_numeric(df_ev['Koszt_Transportu_EUR'], errors='coerce').fillna(0)
                koszty_ev = df_ev.groupby("Przewoznik")["Koszt_Transportu_EUR"].sum().reset_index()
                koszty_ev = koszty_ev[koszty_ev["Koszt_Transportu_EUR"] > 0].sort_values(by="Koszt_Transportu_EUR", ascending=False)
                if not koszty_ev.empty: st.dataframe(koszty_ev, use_container_width=True, hide_index=True)
                else: st.info("Brak zarejestrowanych kosztów w Eventach.")
        with k_col2:
            st.markdown("**📦 Sprzęt (Subrenty)**")
            if not df_sub.empty and "Koszt" in df_sub.columns:
                df_sub['Koszt'] = pd.to_numeric(df_sub['Koszt'], errors='coerce').fillna(0)
                koszty_sub = df_sub.groupby("Firma_Zewnetrzna")["Koszt"].sum().reset_index()
                koszty_sub = koszty_sub[koszty_sub["Koszt"] > 0].sort_values(by="Koszt", ascending=False)
                if not koszty_sub.empty: st.dataframe(koszty_sub, use_container_width=True, hide_index=True)
                else: st.info("Brak zarejestrowanych kosztów w Subrentach.")

    with tab_rentownosc:
        st.subheader("Wycena vs. Rzeczywistość (Eksport Basi)")
        if not df_yt.empty and "Wycena_Dla_Basi" in df_yt.columns and "Koszt_Rzeczywisty" in df_yt.columns:
            df_yt['Wycena_Dla_Basi'] = pd.to_numeric(df_yt['Wycena_Dla_Basi'], errors='coerce').fillna(0)
            df_yt['Koszt_Rzeczywisty'] = pd.to_numeric(df_yt['Koszt_Rzeczywisty'], errors='coerce').fillna(0)
            df_yt['Bilans (Zysk/Strata) €'] = df_yt['Wycena_Dla_Basi'] - df_yt['Koszt_Rzeczywisty']
            
            rentownosc = df_yt[['ID_Yestech', 'Destynacja', 'Wycena_Dla_Basi', 'Koszt_Rzeczywisty', 'Bilans (Zysk/Strata) €']]
            def color_bilans(val):
                if val > 0: return 'color: #10B981; font-weight: bold'
                elif val < 0: return 'color: #EF4444; font-weight: bold'
                return ''
            st.dataframe(rentownosc.style.map(color_bilans, subset=['Bilans (Zysk/Strata) €']), use_container_width=True, hide_index=True)
            suma_zysk = rentownosc['Bilans (Zysk/Strata) €'].sum()
            
            st.markdown(f"""
            <div class="kpi-card kpi-gold" style="width: 50%; margin-top: 20px;">
                <div class="kpi-header">Łączny bilans na projektach YESTECH</div>
                <div class="kpi-value">{suma_zysk:.2f} €</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Brak danych w bazie YESTECH.")
