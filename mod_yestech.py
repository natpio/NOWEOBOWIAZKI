import streamlit as st
import pandas as pd
import datetime
from db import load_data, save_data, generuj_smart_id

def render(sh):
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

            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1: wycena_dla_basi = st.number_input("Wycena dla Basi (€)", min_value=0.0, value=0.0, step=50.0)
            with f_col2: koszt_rzeczywisty = st.number_input("Koszt Rzeczywisty (€)", min_value=0.0, value=0.0, step=50.0)
            with f_col3: marza_info = st.text_input("Marża / Info dodatkowe")

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
