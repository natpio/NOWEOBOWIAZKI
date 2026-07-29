import streamlit as st
import pandas as pd
import datetime
from db import load_data, save_data, generuj_smart_id

def render(sh):
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

    # Usunęliśmy zakładkę Zakończ (tab_zakoncz), wszystko robimy w podglądzie
    tab_podglad, tab_formularz, tab_archiwum = st.tabs([
        "📊 Aktywne", "➕ Dodaj Zlecenie", "📦 Archiwum"
    ])

    with tab_podglad:
        if not df_aktywne.empty:
            st.info("💡 Zaznacz pole '🏁 Zakończ' przy wierszu i kliknij zapisz, aby zamknąć zlecenie (system sam uzupełni N/A dla floty własnej).")
            
            # Tworzymy tymczasową kopię do wyświetlenia i dodajemy kolumnę Checkbox na start
            df_display = df_aktywne.copy()
            df_display.insert(0, "🏁 Zakończ", False)
            
            edited_df = st.data_editor(
                df_display, 
                use_container_width=True, 
                hide_index=True, 
                key="edit_eventy",
                column_config={
                    "🏁 Zakończ": st.column_config.CheckboxColumn(
                        "🏁 Zakończ",
                        help="Zaznacz, aby zakończyć i zarchiwizować to zlecenie",
                        default=False,
                    )
                }
            )
            
            if st.button("💾 Zapisz zmiany w tabeli", type="primary"):
                # 1. Wyłapujemy, które ID zostały zaznaczone do zamknięcia
                zakonczone_id = edited_df[edited_df["🏁 Zakończ"] == True]["ID_Zlecenia"].tolist()
                
                # 2. Usuwamy tymczasową kolumnę "🏁 Zakończ" przed złączeniem z główną bazą
                edited_df = edited_df.drop(columns=["🏁 Zakończ"])
                
                # 3. Aktualizujemy zwykłe zmiany wpisane w tabeli
                df.update(edited_df)
                
                # 4. Aplikujemy logikę ZAMYKANIA do zaznaczonych wierszy
                for z_id in zakonczone_id:
                    idx = df[df['ID_Zlecenia'] == z_id].index[0]
                    
                    if df.at[idx, 'Typ_Transportu'] == "Własny SQM":
                        df.at[idx, 'Data_Zlecenia_Tr'] = "N/A"
                        df.at[idx, 'Faktura_Oplacona'] = "N/A"
                        df.at[idx, 'PP_Otrzymane'] = "N/A"
                        df.at[idx, 'Data_Platnosci'] = "N/A"
                        df.at[idx, 'Koszt_Transportu_EUR'] = "N/A"
                        df.at[idx, 'CMR_Podpisane_POD'] = "N/A"
                        
                    df.at[idx, 'Faza_Procesu'] = "Zamknięte"
                    df.at[idx, 'Zakonczone_Arch'] = "TAK"

                # 5. Zapis i odświeżenie
                save_data(worksheet, df)
                st.success(f"Pomyślnie zaktualizowano! Zakończono {len(zakonczone_id)} zleceń.")
                st.rerun()
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
                koszt_transportu = "N/A"
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
                    
                    if typ_transportu == "Własny SQM":
                        nowy_wiersz["Data_Zlecenia_Tr"] = "N/A"
                        nowy_wiersz["Faktura_Oplacona"] = "N/A"
                        nowy_wiersz["PP_Otrzymane"] = "N/A"
                        nowy_wiersz["Data_Platnosci"] = "N/A"
                        nowy_wiersz["Koszt_Transportu_EUR"] = "N/A"
                        nowy_wiersz["CMR_Podpisane_POD"] = "N/A"

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
            st.info("Archiwum jest puste.")
