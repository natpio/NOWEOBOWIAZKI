import streamlit as st
import gspread
import pandas as pd
import datetime
import re

# 1. KONFIGURACJA STRONY (Zawsze na górze)
st.set_page_config(page_title="SQM Transport Hub PRO", page_icon="🚚", layout="wide", initial_sidebar_state="expanded")

# 2. ŁADOWANIE ZEWNĘTRZNEGO PLIKU CSS
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Plik style.css nie został znaleziony. Aplikacja używa domyślnego wyglądu.")

load_css("style.css")

# 3. FUNKCJE BAZODANOWE I GENERATORY
@st.cache_resource
def init_connection():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open_by_key("1Vw72-HoJhhYMvI5FpcrmeFAhXfDF-mcjpSazyak9Tc4") 
    return sh

def load_data(sh, sheet_name):
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    if df.empty:
        headers = worksheet.row_values(1)
        if headers:
            df = pd.DataFrame(columns=headers)
            
    # Uniwersalne kolumny bezpieczeństwa (teraz z podziałem na CMR startowe i POD końcowe)
    wymagane_kolumny = ["CMR_Gotowe", "CMR_Podpisane_POD", "Faktura_Oplacona", "PP_Otrzymane", "Zakonczone_Arch"]
    for kol in wymagane_kolumny:
        if kol not in df.columns:
            df[kol] = ""
            
    # Kolumny dedykowane dla Eventów
    if sheet_name == "DB_Eventy":
        domyslne_kolumny_eventy = {
            "Typ_Transportu": "Zewnętrzny",
            "ID_Zlecenia": "",
            "Nazwa_Targow": "",
            "Project_Manager": "",
            "Faza_Procesu": "Inicjacja",
            "Typ_Pojazdu": "",
            "Przewoznik": "",
            "Data_Zlecenia_Tr": str(datetime.date.today()),
            "Status_Magazyn": "Brak gotowości",
            "Magazyn_Powod": "",
            "ETA_Wydania": "",
            "Wrzutka_PM": "NIE",
            "Koszt_Dodatkowy": 0,
            "Nr_Zlecenia_Zewn": "",
            "Nr_Faktury": "",
            "Data_Zakonczenia_Uslugi": "",
            "Data_Platnosci": ""
        }
        for kol, val in domyslne_kolumny_eventy.items():
            if kol not in df.columns:
                df[kol] = val
                
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
        
        if not wartosc1 and not wartosc2:
            continue
            
        if wartosc1 not in licznik_elementow:
            licznik_elementow[wartosc1] = 1
        else:
            licznik_elementow[wartosc1] += 1
            
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

# --- MENU BOCZNE ---
with st.sidebar:
    st.title("SQM TMS")
    st.markdown("---")
    wybrany_modul = st.radio(
        "Nawigacja:",
        ["🚚 Eventy / Targi", "📦 Subrenty", "🌍 YESTECH Export", "📊 Finanse i Raporty"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("Wersja systemu: 4.3.0 (Start & End POD)")
    st.caption("Użytkownik: PM / Logistics")

# --- MODUŁY GŁÓWNE ---

if wybrany_modul == "🚚 Eventy / Targi":
    st.title("🚚 Eventy & Flota (Panel Zarządzania)")
    
    worksheet, df = load_data(sh, "DB_Eventy")
    
    # Kafelki KPI
    df_aktywne = df[df.get("Zakonczone_Arch", pd.Series()) != "TAK"] if not df.empty else df
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Aktywne Transporty", len(df_aktywne))
    with col2:
        braki_pod = len(df_aktywne[df_aktywne.get("CMR_Podpisane_POD", pd.Series()) == "NIE"]) if not df_aktywne.empty else 0
        st.metric("Oczekujące Zwroty POD", braki_pod)
    with col3:
        st.metric("Status Bazy", "Synchronizowana 🟢")
    
    st.divider()

    # Zakładki operacyjne
    tab_podglad, tab_formularz, tab_archiwum = st.tabs([
        "📊 Aktywne Transporty (Podgląd)", 
        "➕ Dodaj / Edytuj Zlecenie (Formularz)", 
        "📦 Archiwum Historyczne"
    ])

    with tab_podglad:
        st.subheader("Bieżące zlecenia w realizacji")
        if not df_aktywne.empty:
            st.dataframe(df_aktywne, use_container_width=True, hide_index=True)
        else:
            st.info("Brak aktywnych transportów w bazie.")

    with tab_formularz:
        st.subheader("Inteligentny Formularz Transportowy")
        st.caption("Wypełnij poniższe pola. Reguły biznesowe automatycznie dostosują wymagane dokumenty w zależności od typu transportu.")
        
        with st.form("form_event_pro", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                nazwa_targow = st.text_input("Nazwa Targów / Eventu *")
                typ_transportu = st.selectbox("Typ Transportu", ["Zewnętrzny", "Własny SQM"])
                project_manager = st.text_input("Project Manager (PM)")
                typ_pojazdu = st.text_input("Typ Pojazdu (np. Solówka 12t, Bus)")
            with f_col2:
                przewoznik = st.text_input("Przewoźnik / Kierowca *")
                faza_procesu = st.selectbox("Faza Procesu", ["Inicjacja", "Flota", "Dokumenty", "Załadunek", "Trasa", "Zamknięte"])
                status_magazyn = st.selectbox("Status Magazyn", ["Brak gotowości", "Częściowo", "100% Gotowe"])

            st.markdown("---")
            st.markdown("### 🛫 Dokumenty Startowe i Koszty")
            
            d_start_1, d_start_2 = st.columns(2)
            with d_start_1:
                cmr_gotowe = st.selectbox("Wystawione CMR przed wyjazdem?", ["NIE", "TAK"], help="Czy kierowca otrzymał dokument przewozowy na start?")
            with d_start_2:
                koszt_dodatkowy = st.number_input("Koszt Dodatkowy (PLN)", min_value=0, value=0, format="%d")

            st.markdown("---")
            st.markdown("### 🏁 Rozliczenie i Dowód Dostawy (POD)")
            
            d_col1, d_col2, d_col3 = st.columns(3)
            with d_col1:
                cmr_podpisane = st.selectbox("Otrzymano podpisane CMR (POD po usłudze)?", ["NIE", "TAK"], help="Czy przewoźnik odesłał podpisany dowód dostawy?")
            with d_col2:
                pp_otrzymane = st.selectbox("PP Otrzymane?", ["", "NIE", "TAK"])
            with d_col3:
                faktura_opl = st.selectbox("Faktura Opłacona?", ["", "NIE", "TAK"])

            # DYNAMICZNA LOGIKA BIZNESOWA DLA PÓL SPECYFICZNYCH
            if typ_transportu == "Zewnętrzny":
                st.markdown("#### Wymagania dla Przewoźnika Zewnętrznego:")
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    nr_zlecenia_zewn = st.text_input("Nr Zlecenia Zewnętrznego")
                with e_col2:
                    nr_faktury = st.text_input("Nr Faktury Kosztowej Przewoźnika *")
            else:
                st.info("ℹ️ **Flota Własna SQM:** Pola faktur kosztowych zewnętrznych przewoźników oraz numerów zleceń zewnętrznych zostały pominięte zgodnie z procedurą wewnętrzną.")
                nr_zlecenia_zewn = "FLOTA WŁASNA"
                nr_faktury = "N/A"

            zatwierdzono_form = st.form_submit_button("🚀 Zapisz Nowe Zlecenie do Bazy")
            
            if zatwierdzono_form:
                if not nazwa_targow or not przewoznik:
                    st.error("❌ Musisz uzupełnić nazwę targów oraz przewoźnika/kierowcę!")
                else:
                    nowy_wiersz = {
                        "ID_Zlecenia": "", 
                        "Nazwa_Targow": nazwa_targow,
                        "Typ_Transportu": typ_transportu,
                        "Project_Manager": project_manager,
                        "Faza_Procesu": faza_procesu,
                        "Typ_Pojazdu": typ_pojazdu,
                        "Przewoznik": przewoznik,
                        "Data_Zlecenia_Tr": str(datetime.date.today()),
                        "Status_Magazyn": status_magazyn,
                        "Magazyn_Powod": "",
                        "ETA_Wydania": "",
                        "Wrzutka_PM": "TAK",
                        "Koszt_Dodatkowy": koszt_dodatkowy,
                        "CMR_Gotowe": cmr_gotowe, 
                        "CMR_Podpisane_POD": cmr_podpisane,
                        "Nr_Zlecenia_Zewn": nr_zlecenia_zewn,
                        "Nr_Faktury": nr_faktury,
                        "Data_Zakonczenia_Uslugi": "",
                        "Data_Platnosci": "",
                        "Faktura_Oplacona": faktura_opl,
                        "PP_Otrzymane": pp_otrzymane,
                        "Zakonczone_Arch": "NIE"
                    }
                    
                    df = pd.concat([df, pd.DataFrame([nowy_wiersz])], ignore_index=True)
                    df = generuj_smart_id(df, kolumna_glowna="Nazwa_Targow", kolumna_dodatkowa="Przewoznik", nazwa_kolumny_id="ID_Zlecenia")
                    save_data(worksheet, df)
                    st.success("🎉 Zlecenie zostało pomyślnie dodane i zsynchronizowane z chmurą!")
                    st.rerun()

    with tab_archiwum:
        st.subheader("Archiwum zrealizowanych transportów")
        df_arch = df[df.get("Zakonczone_Arch", pd.Series()) == "TAK"] if not df.empty else pd.DataFrame()
        if not df_arch.empty:
            st.dataframe(df_arch, use_container_width=True, hide_index=True)
        else:
            st.info("Brak zarchiwizowanych zleceń.")

elif wybrany_modul == "📦 Subrenty":
    st.title("📦 Hub Subrentów")
    worksheet, df = load_data(sh, "DB_Subrenty")
    st.info("Moduł subrentów zewnętrznych partnerów.")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

elif wybrany_modul == "🌍 YESTECH Export":
    st.title("🌍 YESTECH Global")
    worksheet, df = load_data(sh, "DB_Yestech")
    st.info("Moduł lejka logistycznego handlowego.")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

elif wybrany_modul == "📊 Finanse i Raporty":
    st.title("📊 Centrum Finansowe")
    st.info("Moduł globalnego zestawienia płatności w przygotowaniu.")
