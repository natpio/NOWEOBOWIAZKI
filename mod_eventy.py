import streamlit as st
import pandas as pd
import datetime
import os
from db import load_data, save_data, generuj_smart_id

def render(sh):
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 20px;'>🚚 Moduł Operacyjny: Eventy & Flota</h2>", unsafe_allow_html=True)
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
                <div class="kpi-header">Status Systemu</div>
                <div class="kpi-value" style="font-size: 26px; padding-top: 5px;">Synchronizowany</div>
                <div class="kpi-icon-bg">✅</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_podglad, tab_formularz, tab_archiwum = st.tabs([
        "🗂️ Aktywne Zlecenia", "➕ Utwórz Nowe Zlecenie", "📦 Archiwum Historyczne"
    ])

    with tab_podglad:
        if not df_aktywne.empty:
            st.markdown("<p style='color: #94A3B8; font-size: 14px; margin-bottom: 20px;'>Kliknij 'Szczegóły' przy zleceniu, aby otworzyć panel boczny z pełnymi danymi i akcjami.</p>", unsafe_allow_html=True)
            
            # Pamięć sesji dla wybranego zlecenia
            if "wybrany_event_id" not in st.session_state:
                st.session_state["wybrany_event_id"] = None

            # DZIELIMY EKRAN: 60% lewa strona (lista), 40% prawa strona (szczegóły)
            col_lista, col_detale = st.columns([6, 4], gap="large")
            
            with col_lista:
                for index, row in df_aktywne.iterrows():
                    faza = str(row.get('Faza_Procesu', '')).lower()
                    badge_class = "cr-badge"
                    if "inicjacja" in faza: badge_class += " inicjacja"
                    elif "planowanie" in faza: badge_class += " planowanie"
                    elif "załadunek" in faza or "częściowo" in str(row.get('Status_Magazyn', '')).lower(): badge_class += " zaladunek"
                    elif "trasa" in faza or "zamknięte" in faza: badge_class += " trasa"
                    else: badge_class += " domyslny"
                    
                    c_karta, c_btn = st.columns([8, 2], vertical_alignment="center")
                    
                    with c_karta:
                        st.markdown(f"""
                        <div class="custom-row" style="margin-bottom: 5px;">
                            <div class="cr-col" style="width: 35%;">
                                <span class="cr-title">{row.get('Nazwa_Targow', '-')}</span>
                                <span>📍 {row.get('ID_Zlecenia', '-')}</span>
                            </div>
                            <div class="cr-col" style="width: 25%;">
                                <span class="cr-text">🚛 {row.get('Typ_Pojazdu', '-')}</span>
                                <span class="cr-text">👤 {row.get('Przewoznik', '-')}</span>
                            </div>
                            <div class="cr-col" style="width: 25%;">
                                <span class="cr-text">📅 {row.get('Data_Zlecenia_Tr', '-')}</span>
                            </div>
                            <div class="cr-col" style="width: 15%; align-items: flex-end;">
                                <span class="{badge_class}">{row.get('Faza_Procesu', '-')}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    with c_btn:
                        # Jeśli ID zgadza się z wybranym, oznaczamy przycisk jako Primary (aktywny)
                        is_primary = st.session_state["wybrany_event_id"] == row['ID_Zlecenia']
                        btn_type = "primary" if is_primary else "secondary"
                        
                        if st.button("🔍 Szczegóły", key=f"det_{row['ID_Zlecenia']}", type=btn_type, use_container_width=True):
                            st.session_state["wybrany_event_id"] = row['ID_Zlecenia']
                            st.rerun()

            with col_detale:
                if st.session_state["wybrany_event_id"]:
                    # Pobieranie danych wybranego eventu
                    dane_eventu = df_aktywne[df_aktywne["ID_Zlecenia"] == st.session_state["wybrany_event_id"]].iloc[0]
                    
                    st.markdown("""
                        <div style="background: rgba(30, 41, 59, 0.5); padding: 25px; border-radius: 16px; border: 1px solid rgba(212, 175, 55, 0.3);">
                            <p style="color: #94A3B8; font-size: 11px; font-weight: 700; letter-spacing: 1px; margin-bottom: 5px; text-transform: uppercase;">Event Details</p>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"<h3 style='color: #F8FAFC; margin-top: 0;'>{dane_eventu['Nazwa_Targow']}</h3>", unsafe_allow_html=True)
                    st.caption(f"🆔 {dane_eventu['ID_Zlecenia']} | 👤 {dane_eventu['Przewoznik']}")
                    
                    # LOGIKA WYŚWIETLANIA OBRAZKA NA BAZIE TYPU POJAZDU
                    typ_pojazdu_lower = str(dane_eventu['Typ_Pojazdu']).lower()
                    if "ftl" in typ_pojazdu_lower: plik_img = "ftl.png"
                    elif "bus" in typ_pojazdu_lower: plik_img = "bus.png"
                    elif "van" in typ_pojazdu_lower: plik_img = "van.png"
                    elif "sol" in typ_pojazdu_lower: plik_img = "solowka.png"
                    else: plik_img = "default.png"
                    
                    if os.path.exists(plik_img):
                        st.image(plik_img, use_container_width=True)
                    else:
                        st.markdown(f"""
                        <div style="width: 100%; height: 120px; background: rgba(0,0,0,0.2); border-radius: 8px; border: 1px dashed rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: center; margin: 15px 0;">
                            <span style="color: rgba(255,255,255,0.3); font-size: 13px;">Brak pliku: {plik_img}</span>
                        </div>
                        """, unsafe_allow_html=True)

                    # ZAKŁADKI W DETALACH
                    det_info, det_dok, det_fin = st.tabs(["INFO & STATUS", "DOKUMENTY", "ZAMKNIJ EVENT"])
                    
                    with det_info:
                        st.markdown(f"""
                        **Pojazd:** {dane_eventu.get('Typ_Pojazdu', '-')}  
                        **Data Transportu:** {dane_eventu.get('Data_Zlecenia_Tr', '-')}  
                        **Faza Procesu:** {dane_eventu.get('Faza_Procesu', '-')}  
                        **Status Magazynu:** {dane_eventu.get('Status_Magazyn', '-')}  
                        **Typ:** {dane_eventu.get('Typ_Transportu', '-')}  
                        <hr style="border-color: rgba(255,255,255,0.1); margin: 10px 0;">
                        **Notatki:** {dane_eventu.get('Notatki', 'Brak notatek.')}
                        """, unsafe_allow_html=True)
                        
                    with det_dok:
                        # Mini-formularz do szybkiej aktualizacji dokumentów bez zamykania eventu
                        with st.form(key=f"update_{dane_eventu['ID_Zlecenia']}"):
                            u_cmr = st.selectbox("CMR Gotowe?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_eventu.get("CMR_Gotowe", "")) if dane_eventu.get("CMR_Gotowe", "") in ["", "NIE", "TAK"] else 0)
                            u_pod = st.selectbox("CMR Podpisane (POD)?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_eventu.get("CMR_Podpisane_POD", "")) if dane_eventu.get("CMR_Podpisane_POD", "") in ["", "NIE", "TAK"] else 0)
                            u_nr_fak = st.text_input("Numer Faktury Zewn.", value=dane_eventu.get("Nr_Faktury", ""))
                            
                            if st.form_submit_button("💾 Zapisz Dokumenty"):
                                idx = df[df['ID_Zlecenia'] == dane_eventu['ID_Zlecenia']].index[0]
                                df.at[idx, 'CMR_Gotowe'] = u_cmr
                                df.at[idx, 'CMR_Podpisane_POD'] = u_pod
                                df.at[idx, 'Nr_Faktury'] = u_nr_fak
                                save_data(worksheet, df)
                                st.success("Zaktualizowano dokumenty!")
                                st.rerun()

                    with det_fin:
                        st.info("Kliknięcie poniższego przycisku zarchiwizuje transport. System sam uzupełni pola (N/A) dla floty SQM.")
                        if st.button("🏁 ZAKOŃCZ I ARCHIWIZUJ", type="primary", use_container_width=True):
                            idx = df[df['ID_Zlecenia'] == dane_eventu['ID_Zlecenia']].index[0]
                            
                            if df.at[idx, 'Typ_Transportu'] == "Własny SQM":
                                df.at[idx, 'Data_Zlecenia_Tr'] = "N/A"
                                df.at[idx, 'Faktura_Oplacona'] = "N/A"
                                df.at[idx, 'PP_Otrzymane'] = "N/A"
                                df.at[idx, 'Data_Platnosci'] = "N/A"
                                df.at[idx, 'Koszt_Transportu_EUR'] = "N/A"
                                df.at[idx, 'CMR_Podpisane_POD'] = "N/A"
                                
                            df.at[idx, 'Faza_Procesu'] = "Zamknięte"
                            df.at[idx, 'Zakonczone_Arch'] = "TAK"
                            
                            save_data(worksheet, df)
                            st.session_state["wybrany_event_id"] = None # Czyścimy wybór po zamknięciu
                            st.success(f"Zlecenie {dane_eventu['Nazwa_Targow']} pomyślnie zarchiwizowane!")
                            st.rerun()
                            
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <div style="height: 100%; display: flex; align-items: center; justify-content: center; background: rgba(30, 41, 59, 0.2); border-radius: 16px; border: 1px dashed rgba(255,255,255,0.1); padding: 40px; text-align: center;">
                            <span style="color: #64748B;">Wybierz zlecenie z listy po lewej stronie, <br>aby wyświetlić panel szczegółów (Master-Detail View).</span>
                        </div>
                    """, unsafe_allow_html=True)

        else:
            st.info("Brak aktywnych transportów w bazie danych.")

    with tab_formularz:
        with st.form("form_event_pro", clear_on_submit=True):
            st.markdown("<h4 style='color: #D4AF37; margin-top: 0;'>📝 Podstawowe Dane Operacyjne</h4>", unsafe_allow_html=True)
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                nazwa_targow = st.text_input("Nazwa Targów / Eventu *")
                typ_transportu = st.selectbox("Typ Transportu", ["Zewnętrzny", "Własny SQM"])
                typ_pojazdu = st.text_input("Typ Pojazdu (np. FTL, SOLOWKA, BUS, VAN)")
            with f_col2:
                przewoznik = st.text_input("Przewoźnik / Kierowca *")
                faza_procesu = st.selectbox("Faza Procesu", ["Inicjacja", "Planowanie", "Załadunek", "Trasa", "Zamknięte"])
                status_magazyn = st.selectbox("Status Magazyn", ["Brak gotowości", "Częściowo", "100% Gotowe"])

            notatki = st.text_area("Notatki Dodatkowe")
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color: #D4AF37;'>🛫 Status Logistyczny</h4>", unsafe_allow_html=True)
            cmr_gotowe = st.selectbox("Wystawione CMR przed wyjazdem?", ["NIE", "TAK"])
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
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
