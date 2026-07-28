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
    # Automatyczne tworzenie zakładki w Google Sheets, jeśli nie istnieje
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
            
    # Kolumny dedykowane dla Eventów - Uproszczone
    if sheet_name == "DB_Eventy":
        wymagane = ["CMR_Gotowe", "CMR_Podpisane_POD", "Faktura_Oplacona", "PP_Otrzymane", "Zakonczone_Arch"]
        for kol in wymagane:
            if kol not in df.columns:
                df[kol] = ""
                
        domyslne_kolumny = {
            "Typ_Transportu": "Zewnętrzny", "ID_Zlecenia": "", "Nazwa_Targow": "",
            "Faza_Procesu": "Inicjacja", "Typ_Pojazdu": "", "Przewoznik": "",
            "Data_Zlecenia_Tr": str(datetime.date.today()), "Status_Magazyn": "Brak gotowości",
            "Notatki": "", "Nr_Zlecenia_Zewn": "", "Nr_Faktury": "",
            "Data_Zakonczenia_Uslugi": "", "Data_Platnosci": ""
        }
        for kol, val in domyslne_kolumny.items():
            if kol not in df.columns:
                df[kol] = val

    # Kolumny dedykowane dla Subrentów
    elif sheet_name == "DB_Subrenty":
        domyslne_subrenty = {
            "ID_Subrentu": "", "Nazwa_Sprzetu": "", "Firma_Zewnetrzna": "",
            "Data_Odbioru": str(datetime.date.today()), "Data_Zwrotu": str(datetime.date.today()),
            "Status": "Zamówione", "Koszt": 0, "Notatki": "", "Zakonczone_Arch": "NIE"
        }
        for kol, val in domyslne_subrenty.items():
            if kol not in df.columns:
                df[kol] = val
                
    # Kolumny dla Książki Adresowej
    elif sheet_name == "DB_Katalog_Firm":
        if "Nazwa_Firmy" not in df.columns:
            df["Nazwa_Firmy"] = ""
                
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
    st.caption("Wersja systemu: 5.0.0 (Address Book & Subrents)")
    st.caption("Użytkownik: Logistics Manager")

# --- MODUŁY GŁÓWNE ---

if wybrany_modul == "🚚 Eventy / Targi":
    st.title("🚚 Eventy & Flota (Panel Zarządzania)")
    
    worksheet, df = load_data(sh, "DB_Eventy")
    
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

    tab_podglad, tab_formularz, tab_archiwum = st.tabs([
        "📊 Aktywne Transporty (Podgląd)", "➕ Dodaj Zlecenie (Formularz)", "📦 Archiwum"
    ])

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
            with d_col1:
                cmr_podpisane = st.selectbox("Otrzymano podpisane CMR (POD)?", ["NIE", "TAK"])
            with d_col2:
                pp_otrzymane = st.selectbox("PP Otrzymane?", ["", "NIE", "TAK"])
            with d_col3:
                faktura_opl = st.selectbox("Faktura Opłacona?", ["", "NIE", "TAK"])

            if typ_transportu == "Zewnętrzny":
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    nr_zlecenia_zewn = st.text_input("Nr Zlecenia Zewnętrznego")
                with e_col2:
                    nr_faktury = st.text_input("Nr Faktury Kosztowej Przewoźnika *")
            else:
                nr_zlecenia_zewn = "FLOTA WŁASNA"
                nr_faktury = "N/A"

            if st.form_submit_button("🚀 Zapisz Zlecenie"):
                if not nazwa_targow or not przewoznik:
                    st.error("❌ Musisz uzupełnić nazwę targów oraz przewoźnika/kierowcę!")
                else:
                    nowy_wiersz = {
                        "ID_Zlecenia": "", "Nazwa_Targow": nazwa_targow, "Typ_Transportu": typ_transportu,
                        "Faza_Procesu": faza_procesu, "Typ_Pojazdu": typ_pojazdu, "Przewoznik": przewoznik,
                        "Data_Zlecenia_Tr": str(datetime.date.today()), "Status_Magazyn": status_magazyn,
                        "Notatki": notatki, "CMR_Gotowe": cmr_gotowe, "CMR_Podpisane_POD": cmr_podpisane,
                        "Nr_Zlecenia_Zewn": nr_zlecenia_zewn, "Nr_Faktury": nr_faktury,
                        "Data_Zakonczenia_Uslugi": "", "Data_Platnosci": "",
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
        else:
            st.info("Brak zarchiwizowanych zleceń.")

elif wybrany_modul == "📦 Subrenty":
    st.title("📦 Hub Wypożyczeń (Subrenty)")
    
    # Inicjalizacja bazy Subrentów i Książki Adresowej
    worksheet_sub, df_sub = load_data(sh, "DB_Subrenty")
    worksheet_firmy, df_firmy = load_data(sh, "DB_Katalog_Firm")
    
    katalog_firm = df_firmy["Nazwa_Firmy"].dropna().unique().tolist() if not df_firmy.empty else []

    df_aktywne_sub = df_sub[df_sub.get("Zakonczone_Arch", pd.Series()) != "TAK"] if not df_sub.empty else df_sub
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Aktywne Wypożyczenia", len(df_aktywne_sub))
    with col2:
        st.metric("Firmy w bazie (Książka)", len(katalog_firm))
        
    st.divider()

    tab_podglad, tab_formularz, tab_archiwum = st.tabs([
        "📊 Aktywne Wypożyczenia (Podgląd)", "➕ Dodaj Subrent (Formularz)", "📦 Archiwum"
    ])

    with tab_podglad:
        if not df_aktywne_sub.empty:
            st.dataframe(df_aktywne_sub, use_container_width=True, hide_index=True)
        else:
            st.info("Brak aktywnych wypożyczeń sprzętu.")

    with tab_formularz:
        st.subheader("Formularz Rejestracji Sprzętu")
        
        with st.form("form_subrent", clear_on_submit=True):
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                nazwa_sprzetu = st.text_input("Nazwa Sprzętu / Cel Wypożyczenia *")
                wybor_firmy = st.selectbox("Wybierz z książki adresowej *", ["-- Dodaj nową firmę (wpisz poniżej) --"] + sorted(katalog_firm))
                nowa_firma = st.text_input("Nowa firma (wypełnij, jeśli brak na liście wyżej)")
            with s_col2:
                status_sub = st.selectbox("Status", ["Zamówione", "Odebrane", "Zwrócone", "Rozliczone"])
                koszt = st.number_input("Koszt całkowity (PLN)", min_value=0, value=0, format="%d")

            d_col1, d_col2 = st.columns(2)
            with d_col1:
                data_od = st.date_input("Data Odbioru")
            with d_col2:
                data_do = st.date_input("Data Zwrotu")
                
            notatki_sub = st.text_area("Dodatkowe Notatki")

            if st.form_submit_button("💾 Zapisz Subrent"):
                # Logika weryfikująca, skąd bierzemy firmę
                firma_docelowa = nowa_firma.strip() if wybor_firmy == "-- Dodaj nową firmę (wpisz poniżej) --" else wybor_firmy
                
                if not nazwa_sprzetu or not firma_docelowa:
                    st.error("❌ Musisz uzupełnić nazwę sprzętu oraz wskazać firmę zewnętrzną!")
                else:
                    # Aktualizacja książki adresowej, jeśli firma jest nowa
                    if firma_docelowa not in katalog_firm:
                        df_firmy = pd.concat([df_firmy, pd.DataFrame([{"Nazwa_Firmy": firma_docelowa}])], ignore_index=True)
                        save_data(worksheet_firmy, df_firmy)
                        
                    # Zapis Subrentu
                    czy_arch = "TAK" if status_sub in ["Zwrócone", "Rozliczone"] else "NIE"
                    nowy_wiersz = {
                        "ID_Subrentu": "", "Nazwa_Sprzetu": nazwa_sprzetu, "Firma_Zewnetrzna": firma_docelowa,
                        "Data_Odbioru": str(data_od), "Data_Zwrotu": str(data_do),
                        "Status": status_sub, "Koszt": koszt, "Notatki": notatki_sub, "Zakonczone_Arch": czy_arch
                    }
                    df_sub = pd.concat([df_sub, pd.DataFrame([nowy_wiersz])], ignore_index=True)
                    df_sub = generuj_smart_id(df_sub, "Firma_Zewnetrzna", "Nazwa_Sprzetu", "ID_Subrentu")
                    save_data(worksheet_sub, df_sub)
                    
                    st.success(f"🎉 Zapisano subrent na sprzęt z firmy {firma_docelowa}!")
                    st.rerun()

    with tab_archiwum:
        df_arch_sub = df_sub[df_sub.get("Zakonczone_Arch", pd.Series()) == "TAK"] if not df_sub.empty else pd.DataFrame()
        if not df_arch_sub.empty:
            st.dataframe(df_arch_sub, use_container_width=True, hide_index=True)
        else:
            st.info("Brak zarchiwizowanych wypożyczeń.")

elif wybrany_modul == "🌍 YESTECH Export":
    st.title("🌍 YESTECH Global")
    worksheet, df = load_data(sh, "DB_Yestech")
    st.info("Moduł lejka logistycznego handlowego.")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

elif wybrany_modul == "📊 Finanse i Raporty":
    st.title("📊 Centrum Finansowe")
    st.info("Moduł globalnego zestawienia płatności w przygotowaniu.")
