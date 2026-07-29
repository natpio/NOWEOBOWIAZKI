import streamlit as st
import pandas as pd
import datetime
from db import load_data, save_data, generuj_smart_id

def render(sh):
    # Nowoczesny, mroczny nagłówek modułu
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 20px;'>🚚 Moduł Operacyjny: Eventy & Flota</h2>", unsafe_allow_html=True)
    
    worksheet, df = load_data(sh, "DB_Eventy")
    
    df_aktywne = df[df.get("Zakonczone_Arch", pd.Series()) != "TAK"] if not df.empty else df
    braki_pod = len(df_aktywne[df_aktywne.get("CMR_Podpisane_POD", pd.Series()) == "NIE"]) if not df_aktywne.empty else 0
    
    # Karty KPI - Automatycznie zaciągną efekt szkła z pliku style.css
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
                <div class="kpi-value" style="font-size: 26px; padding-top: 5px;">Online</div>
                <div class="kpi-icon-bg">✅</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_podglad, tab_formularz, tab_archiwum = st.tabs([
        "📊 Aktywne Operacje", "➕ Nowe Zlecenie Transportowe", "📦 Archiwum Historyczne"
    ])

    with tab_podglad:
        if not df_aktywne.empty:
            st.markdown("<p style='color: #94A3B8; font-size: 14px;'>Zaznacz pole <b>'🏁 Zakończ'</b> przy wierszu i zapisz, aby zarchiwizować zlecenie. System automatycznie wyczyści komórki finansowe (N/A) dla floty SQM.</p>", unsafe_allow_html=True)
            
            # Tymczasowa kolumna "🏁 Zakończ" na czas edycji
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
            
            if st.button("💾 Zatwierdź Zmiany w Bazie", type="primary"):
                # Wyciągamy ID zaznaczone do zamknięcia
                zakonczone_id = edited_df[edited_df["🏁 Zakończ"] == True]["ID_Zlecenia"].tolist()
                
                # Usuwamy techniczną kolumnę z widoku
                edited_df = edited_df.drop(columns=["🏁 Zakończ"])
                
                # Aktualizujemy ewentualne inne poprawki zrobione w locie
                df.update(edited_df)
                
                # Uruchamiamy logikę zamykania i czyszczenia finansów dla floty
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

                # Zapis i reload
                save_data(worksheet, df)
                st.success(f"Pomyślnie zaktualizowano! Zakończono {len(zakonczone_id)} zleceń.")
                st.rerun()
        else:
            st.info("Brak aktywnych transportów w bazie danych.")

    with tab_formularz:
        with st.form("form_event_pro", clear_on_submit=True):
            st.markdown("<h4 style='color: #D4AF37; margin-top: 0;'>📝 Podstawowe Dane Operacyjne</h4>", unsafe_allow_html=True)
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
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color: #D4AF37;'>🛫 Status Logistyczny</h4>", unsafe_allow_html=True)
            cmr_gotowe = st.selectbox("Wystawione CMR przed wyjazdem?", ["NIE", "TAK"])
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color: #D4AF37;'>🏁 Finanse i Dowód Dostawy (POD)</h4>", unsafe_allow_html=True)
            d_col1, d_col2, d_col3 = st.columns(3)
            with d_col1: cmr_podpisane = st.selectbox("Otrzymano podpisane CMR (POD)?", ["NIE", "TAK"])
            with d_col2: pp_otrzymane = st.selectbox("PP Otrzymane?", ["", "NIE", "TAK"])
            with d_col3: faktura_opl = st.selectbox("Faktura Opłacona?", ["", "NIE", "TAK"])

            st.markdown("<br>", unsafe_allow_html=True)
            
            if typ_transportu == "Zewnętrzny":
                e_col1, e_col2, e_col3 = st.columns(3)
                with e_col1: koszt_transportu = st.number_input("Koszt Transportu (€)", min_value=0.0, value=0.0, step=50.0)
                with e_col2: nr_zlecenia_zewn = st.text_input("Nr Zlecenia Zewnętrznego")
                with e_col3: nr_faktury = st.text_input("Nr Faktury Przewoźnika")
            else:
                koszt_transportu = "N/A"
                nr_zlecenia_zewn = "FLOTA WŁASNA"
                nr_faktury = "N/A"

            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("🚀 Zainicjuj Zlecenie Systemowe"):
                if not nazwa_targow or not przewoznik:
                    st.error("❌ Błąd krytyczny: Uzupełnij nazwę targów oraz przewoźnika!")
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
                    st.success("🎉 Zlecenie zapisane w bazie chmurowej!")
                    st.rerun()

    with tab_archiwum:
        df_arch = df[df.get("Zakonczone_Arch", pd.Series()) == "TAK"] if not df.empty else pd.DataFrame()
        if not df_arch.empty: 
            st.dataframe(df_arch, use_container_width=True, hide_index=True)
        else:
            st.info("Brak zarchiwizowanych transportów.")
