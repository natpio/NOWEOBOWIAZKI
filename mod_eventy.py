import streamlit as st
import pandas as pd
import datetime
import os
from db import load_data, save_data, generuj_smart_id

def render(sh):
    st.markdown("<h2 style='color: #F8FAFC; margin-bottom: 20px;'>🚚 Moduł Operacyjny: Eventy & Flota</h2>", unsafe_allow_html=True)
    worksheet, df = load_data(sh, "DB_Eventy")
    
    df_aktywne = df[df.get("Zakonczone_Arch", pd.Series()) != "TAK"] if not df.empty else df
    
    braki_cmr = len(df_aktywne[df_aktywne.get("CMR_Gotowe", pd.Series()) == "NIE"]) if not df_aktywne.empty else 0
    braki_pod = len(df_aktywne[df_aktywne.get("CMR_Podpisane_POD", pd.Series()) == "NIE"]) if not df_aktywne.empty else 0
    braki_faktury = len(df_aktywne[df_aktywne.get("Faktura_Oplacona", pd.Series()) == "NIE"]) if not df_aktywne.empty else 0
    
    kpi3_color = "kpi-red" if braki_faktury > 0 else "kpi-green"
    
    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card kpi-blue">
                <div class="kpi-header">Do wystawienia CMR</div>
                <div class="kpi-value">{braki_cmr}</div>
                <div class="kpi-icon-bg">📝</div>
            </div>
            <div class="kpi-card kpi-gold">
                <div class="kpi-header">Brakujące zwroty POD</div>
                <div class="kpi-value">{braki_pod}</div>
                <div class="kpi-icon-bg">📄</div>
            </div>
            <div class="kpi-card {kpi3_color}">
                <div class="kpi-header">Nieopłacone faktury</div>
                <div class="kpi-value">{braki_faktury}</div>
                <div class="kpi-icon-bg">💰</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_podglad, tab_formularz, tab_archiwum = st.tabs([
        "🗂️ Aktywne Zlecenia", "➕ Utwórz Nowe Zlecenie", "📦 Archiwum Historyczne"
    ])

    with tab_podglad:
        if not df_aktywne.empty:
            
            if "wybrany_event_id" not in st.session_state:
                st.session_state["wybrany_event_id"] = None
            if "filtr_eventow" not in st.session_state:
                st.session_state["filtr_eventow"] = "Wszystkie"

            st.markdown("<p style='color: #94A3B8; font-size: 12px; font-weight: 700; letter-spacing: 1px; margin-bottom: 10px; text-transform: uppercase;'>⚡ Filtruj listę według braków operacyjnych:</p>", unsafe_allow_html=True)
            
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1:
                if st.button(f"🌍 Wszystkie", use_container_width=True, type="primary" if st.session_state["filtr_eventow"] == "Wszystkie" else "secondary"):
                    st.session_state["filtr_eventow"] = "Wszystkie"
                    st.session_state["wybrany_event_id"] = None
                    st.rerun()
            with f_col2:
                if st.button(f"📝 Brak CMR ({braki_cmr})", use_container_width=True, type="primary" if st.session_state["filtr_eventow"] == "BrakCMR" else "secondary"):
                    st.session_state["filtr_eventow"] = "BrakCMR"
                    st.session_state["wybrany_event_id"] = None
                    st.rerun()
            with f_col3:
                if st.button(f"📥 Brak POD ({braki_pod})", use_container_width=True, type="primary" if st.session_state["filtr_eventow"] == "BrakPOD" else "secondary"):
                    st.session_state["filtr_eventow"] = "BrakPOD"
                    st.session_state["wybrany_event_id"] = None
                    st.rerun()
            with f_col4:
                if st.button(f"💰 Nieopłacone ({braki_faktury})", use_container_width=True, type="primary" if st.session_state["filtr_eventow"] == "BrakFaktury" else "secondary"):
                    st.session_state["filtr_eventow"] = "BrakFaktury"
                    st.session_state["wybrany_event_id"] = None
                    st.rerun()
            
            df_widok = df_aktywne.copy()
            if st.session_state["filtr_eventow"] == "BrakCMR":
                df_widok = df_widok[df_widok.get("CMR_Gotowe", pd.Series()) == "NIE"]
            elif st.session_state["filtr_eventow"] == "BrakPOD":
                df_widok = df_widok[df_widok.get("CMR_Podpisane_POD", pd.Series()) == "NIE"]
            elif st.session_state["filtr_eventow"] == "BrakFaktury":
                df_widok = df_widok[df_widok.get("Faktura_Oplacona", pd.Series()) == "NIE"]

            st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 15px 0 25px 0;'>", unsafe_allow_html=True)
            
            col_lista, col_detale = st.columns([55, 45], gap="large")
            
            with col_lista:
                if df_widok.empty:
                    st.info("Brak zleceń spełniających wybrane kryteria filtra.")
                else:
                    for index, row in df_widok.iterrows():
                        faza = str(row.get('Faza_Procesu', '')).lower()
                        badge_class = "cr-badge"
                        if "inicjacja" in faza: badge_class += " inicjacja"
                        elif "planowanie" in faza: badge_class += " planowanie"
                        elif "załadunek" in faza or "częściowo" in str(row.get('Status_Magazyn', '')).lower(): badge_class += " zaladunek"
                        elif "trasa" in faza or "zamknięte" in faza: badge_class += " trasa"
                        else: badge_class += " domyslny"
                        
                        # --- GENEROWANIE ALERTÓW (TAGÓW) DLA LISTY ---
                        is_sqm_row = row.get('Typ_Transportu', '') == "Własny SQM"
                        braki_tagi_html = ""
                        
                        tag_style = "padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;"
                        if str(row.get('CMR_Gotowe', '')) == 'NIE':
                            braki_tagi_html += f"<span style='background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); {tag_style}'>🚨 WYSTAW CMR</span>"
                        if not is_sqm_row:
                            if str(row.get('CMR_Podpisane_POD', '')) == 'NIE':
                                braki_tagi_html += f"<span style='background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4); {tag_style}'>📄 BRAK POD</span>"
                            if str(row.get('Faktura_Oplacona', '')) == 'NIE':
                                braki_tagi_html += f"<span style='background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); {tag_style}'>💰 NIEOPŁACONE</span>"
                            if str(row.get('PP_Otrzymane', '')) == 'NIE':
                                braki_tagi_html += f"<span style='background: rgba(59, 130, 246, 0.2); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.4); {tag_style}'>💳 BRAK PP</span>"

                        c_karta, c_btn = st.columns([8, 2], vertical_alignment="center")
                        
                        with c_karta:
                            st.markdown(f"""
                            <div class="custom-row" style="margin-bottom: 5px; padding: 15px 20px; flex-direction: column;">
                                <div style="display: flex; width: 100%; justify-content: space-between;">
                                    <div class="cr-col" style="width: 40%;">
                                        <span class="cr-title" style="font-size: 15px;">{row.get('Nazwa_Targow', '-')}</span>
                                        <span style="font-size: 11px;">📍 {row.get('ID_Zlecenia', '-')}</span>
                                    </div>
                                    <div class="cr-col" style="width: 25%;">
                                        <span class="cr-text">🚛 {row.get('Typ_Pojazdu', '-')}</span>
                                        <span class="cr-text">👤 {row.get('Przewoznik', '-')}</span>
                                    </div>
                                    <div class="cr-col" style="width: 35%; align-items: flex-end;">
                                        <span class="cr-text" style="margin-bottom: 5px;">📅 {row.get('Data_Zlecenia_Tr', '-')}</span>
                                        <span class="{badge_class}">{row.get('Faza_Procesu', '-')}</span>
                                    </div>
                                </div>
                                <div style="margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap;">
                                    {braki_tagi_html}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with c_btn:
                            is_primary = st.session_state["wybrany_event_id"] == row['ID_Zlecenia']
                            btn_type = "primary" if is_primary else "secondary"
                            
                            if st.button("🔍 Szczegóły", key=f"det_{row['ID_Zlecenia']}", type=btn_type, use_container_width=True):
                                st.session_state["wybrany_event_id"] = row['ID_Zlecenia']
                                st.rerun()

            with col_detale:
                if st.session_state["wybrany_event_id"] and not df_widok[df_widok["ID_Zlecenia"] == st.session_state["wybrany_event_id"]].empty:
                    dane_eventu = df_widok[df_widok["ID_Zlecenia"] == st.session_state["wybrany_event_id"]].iloc[0]
                    is_sqm = dane_eventu.get('Typ_Transportu', '') == "Własny SQM"
                    
                    st.markdown("""
                        <div style="background: rgba(30, 41, 59, 0.5); padding: 25px; border-radius: 16px; border: 1px solid rgba(212, 175, 55, 0.3);">
                            <p style="color: #94A3B8; font-size: 11px; font-weight: 700; letter-spacing: 1px; margin-bottom: 5px; text-transform: uppercase;">Szczegóły Operacji</p>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"<h3 style='color: #F8FAFC; margin-top: 0;'>{dane_eventu['Nazwa_Targow']}</h3>", unsafe_allow_html=True)
                    st.caption(f"🆔 {dane_eventu['ID_Zlecenia']} | 👤 {dane_eventu['Przewoznik']}")
                    
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
                        <div style="width: 100%; height: 150px; background: rgba(0,0,0,0.2); border-radius: 8px; border: 1px dashed rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: center; margin: 15px 0;">
                            <span style="color: rgba(255,255,255,0.3); font-size: 13px;">Brak grafiki ({plik_img})</span>
                        </div>
                        """, unsafe_allow_html=True)

                    # --- WIZUALNA TABLICA "TO-DO" (ANALIZA BRAKÓW) ---
                    braki_zlecenia = []
                    if dane_eventu.get("CMR_Gotowe") == "NIE":
                        braki_zlecenia.append("📝 <b>Wystawić dokument CMR</b> dla kierowcy")
                    if not is_sqm:
                        if dane_eventu.get("CMR_Podpisane_POD") == "NIE":
                            braki_zlecenia.append("📄 <b>Odzyskać podpisane CMR (POD)</b> po dostawie")
                        if dane_eventu.get("Faktura_Oplacona") == "NIE":
                            braki_zlecenia.append("💰 <b>Opłacić fakturę</b> zewnętrznego przewoźnika")
                        if dane_eventu.get("PP_Otrzymane") == "NIE":
                            braki_zlecenia.append("💳 Zdobyć i wgrać <b>Potwierdzenie Przelewu (PP)</b>")
                        if str(dane_eventu.get("Nr_Faktury", "")).strip() in ["", "None"]:
                            braki_zlecenia.append("🔢 Wprowadzić <b>Numer Faktury Zewnętrznej</b>")

                    if braki_zlecenia:
                        lista_brakow = "".join([f"<li style='margin-bottom: 5px;'>{b}</li>" for b in braki_zlecenia])
                        st.markdown(f"""
                        <div style="background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.4); padding: 15px 20px; border-radius: 8px; margin: 15px 0;">
                            <h4 style="color: #ef4444; margin: 0 0 10px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">⚠️ Wymagane Akcje (Do załatwienia):</h4>
                            <ul style="color: #F8FAFC; font-size: 13px; margin: 0; padding-left: 20px;">
                                {lista_brakow}
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background: rgba(34, 197, 94, 0.05); border: 1px solid rgba(34, 197, 94, 0.3); padding: 12px 15px; border-radius: 8px; margin: 15px 0; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 18px;">✅</span>
                            <span style="color: #22c55e; font-size: 13px; font-weight: 600;">Wszystkie dokumenty i rozliczenia dla tego etapu są kompletne.</span>
                        </div>
                        """, unsafe_allow_html=True)

                    det_info, det_fin, det_arch = st.tabs(["📝 INFO & STATUS", "💼 DOK. & FINANSE", "🏁 ZAKOŃCZ"])
                    
                    with det_info:
                        st.markdown(f"""
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 10px;">
                            <div>
                                <div style="color: #64748B; font-size: 11px; text-transform: uppercase; font-weight: 700;">Typ Pojazdu</div>
                                <div style="color: #F8FAFC; font-weight: 600; font-size: 14px;">{dane_eventu.get('Typ_Pojazdu', '-')}</div>
                            </div>
                            <div>
                                <div style="color: #64748B; font-size: 11px; text-transform: uppercase; font-weight: 700;">Typ Transportu</div>
                                <div style="color: #F8FAFC; font-weight: 600; font-size: 14px;">{dane_eventu.get('Typ_Transportu', '-')}</div>
                            </div>
                            <div>
                                <div style="color: #64748B; font-size: 11px; text-transform: uppercase; font-weight: 700;">Nr Zlecenia Zewn.</div>
                                <div style="color: #F8FAFC; font-weight: 600; font-size: 14px;">{dane_eventu.get('Nr_Zlecenia_Zewn', '-')}</div>
                            </div>
                        </div>
                        <hr style="border-color: rgba(255,255,255,0.05); margin: 15px 0;">
                        """, unsafe_allow_html=True)
                        
                        with st.form(key=f"edit_status_{dane_eventu['ID_Zlecenia']}"):
                            st.markdown("<p style='color:#D4AF37; font-weight:700; margin-bottom:5px; font-size: 14px;'>🔄 Aktualizacja Statusu Operacyjnego</p>", unsafe_allow_html=True)
                            
                            c_stat1, c_stat2, c_stat3 = st.columns(3)
                            
                            fazy_lista = ["Inicjacja", "Planowanie", "Załadunek", "Trasa", "Zamknięte"]
                            akt_faza = dane_eventu.get("Faza_Procesu", "Inicjacja")
                            idx_fazy = fazy_lista.index(akt_faza) if akt_faza in fazy_lista else 0
                            
                            mag_lista = ["Brak gotowości", "Częściowo", "100% Gotowe"]
                            akt_mag = dane_eventu.get("Status_Magazyn", "Brak gotowości")
                            idx_mag = mag_lista.index(akt_mag) if akt_mag in mag_lista else 0

                            with c_stat1:
                                u_faza = st.selectbox("Faza Procesu", fazy_lista, index=idx_fazy)
                            with c_stat2:
                                u_status_mag = st.selectbox("Status Magazyn", mag_lista, index=idx_mag)
                            with c_stat3:
                                dp_trasa = dane_eventu.get("Data_Zlecenia_Tr", "")
                                try:
                                    dp_parsed = datetime.datetime.strptime(str(dp_trasa), "%Y-%m-%d").date() if dp_trasa and dp_trasa != "N/A" else datetime.date.today()
                                except:
                                    dp_parsed = datetime.date.today()
                                u_data_tr = st.date_input("Data Logistyczna", value=dp_parsed)

                            u_notatki = st.text_area("Notatki", value=dane_eventu.get('Notatki', ''))
                            
                            if st.form_submit_button("💾 Zapisz Zmiany"):
                                idx = df[df['ID_Zlecenia'] == dane_eventu['ID_Zlecenia']].index[0]
                                df.at[idx, 'Faza_Procesu'] = u_faza
                                df.at[idx, 'Status_Magazyn'] = u_status_mag
                                df.at[idx, 'Data_Zlecenia_Tr'] = str(u_data_tr)
                                df.at[idx, 'Notatki'] = u_notatki
                                save_data(worksheet, df)
                                st.success("Status operacyjny został zaktualizowany!")
                                st.rerun()
                        
                    with det_fin:
                        with st.form(key=f"update_fin_{dane_eventu['ID_Zlecenia']}"):
                            st.markdown("<p style='color:#D4AF37; font-weight:700; margin-bottom:5px; font-size: 14px;'>🗃️ Status Dokumentacji i Rozliczeń</p>", unsafe_allow_html=True)
                            
                            if is_sqm:
                                u_cmr = st.selectbox("CMR Gotowe (Wystawione)?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_eventu.get("CMR_Gotowe", "")) if dane_eventu.get("CMR_Gotowe", "") in ["", "NIE", "TAK"] else 0)
                                st.info("🚚 Pojazd własnej floty SQM. Pola kosztów, zewnętrznych faktur oraz statusu Potwierdzenia Przelewu są automatycznie wyłączone (N/A).")
                                
                                u_pod, u_pp, u_koszt, u_nr_fak, u_faktura_opl, u_data_platnosci = "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"
                            else:
                                col_d1, col_d2, col_d3 = st.columns(3)
                                with col_d1: u_cmr = st.selectbox("CMR Gotowe?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_eventu.get("CMR_Gotowe", "")) if dane_eventu.get("CMR_Gotowe", "") in ["", "NIE", "TAK"] else 0)
                                with col_d2: u_pod = st.selectbox("CMR POD?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_eventu.get("CMR_Podpisane_POD", "")) if dane_eventu.get("CMR_Podpisane_POD", "") in ["", "NIE", "TAK"] else 0)
                                with col_d3: u_pp = st.selectbox("Potw. Przelewu (PP)?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_eventu.get("PP_Otrzymane", "")) if dane_eventu.get("PP_Otrzymane", "") in ["", "NIE", "TAK"] else 0)
                                
                                st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 10px 0;'>", unsafe_allow_html=True)
                                st.markdown("<p style='color:#D4AF37; font-weight:700; margin-bottom:5px; font-size: 14px;'>💰 Koszty i Faktury</p>", unsafe_allow_html=True)
                                
                                col_f1, col_f2 = st.columns(2)
                                with col_f1: 
                                    koszt_str = str(dane_eventu.get("Koszt_Transportu_EUR", 0.0))
                                    koszt_val = float(koszt_str) if koszt_str.replace('.', '', 1).isdigit() else 0.0
                                    u_koszt = st.number_input("Koszt (EUR)", min_value=0.0, value=koszt_val, step=50.0)
                                    u_nr_fak = st.text_input("Nr Faktury Zewn.", value=dane_eventu.get("Nr_Faktury", ""))
                                with col_f2:
                                    u_faktura_opl = st.selectbox("Faktura Opłacona?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_eventu.get("Faktura_Oplacona", "")) if dane_eventu.get("Faktura_Oplacona", "") in ["", "NIE", "TAK"] else 0)
                                    dp_val = dane_eventu.get("Data_Platnosci", "")
                                    try:
                                        dp_val_parsed = datetime.datetime.strptime(str(dp_val), "%Y-%m-%d").date() if dp_val and dp_val != "N/A" else None
                                    except:
                                        dp_val_parsed = None
                                    u_data_platnosci = st.date_input("Termin Płatności", value=dp_val_parsed)

                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.form_submit_button("💾 Zapisz Aktualizacje"):
                                idx = df[df['ID_Zlecenia'] == dane_eventu['ID_Zlecenia']].index[0]
                                df.at[idx, 'CMR_Gotowe'] = u_cmr
                                df.at[idx, 'CMR_Podpisane_POD'] = u_pod
                                df.at[idx, 'PP_Otrzymane'] = u_pp
                                df.at[idx, 'Nr_Faktury'] = u_nr_fak
                                
                                if not is_sqm:
                                    df.at[idx, 'Koszt_Transportu_EUR'] = float(u_koszt)
                                    df.at[idx, 'Faktura_Oplacona'] = u_faktura_opl
                                    df.at[idx, 'Data_Platnosci'] = str(u_data_platnosci) if u_data_platnosci else ""
                                    
                                save_data(worksheet, df)
                                st.success("Pomyślnie zaktualizowano dokumentację i finanse!")
                                st.rerun()

                    with det_arch:
                        st.info("Kliknięcie poniższego przycisku zarchiwizuje transport. System usunie go z widoku aktywnych operacji.")
                        if st.button("🏁 ZAKOŃCZ I ARCHIWIZUJ ZLECENIE", type="primary", use_container_width=True):
                            idx = df[df['ID_Zlecenia'] == dane_eventu['ID_Zlecenia']].index[0]
                            
                            if df.at[idx, 'Typ_Transportu'] == "Własny SQM":
                                df.at[idx, 'Faktura_Oplacona'] = "N/A"
                                df.at[idx, 'PP_Otrzymane'] = "N/A"
                                df.at[idx, 'Data_Platnosci'] = "N/A"
                                df.at[idx, 'Koszt_Transportu_EUR'] = "N/A"
                                df.at[idx, 'CMR_Podpisane_POD'] = "N/A"
                                df.at[idx, 'Nr_Faktury'] = "N/A"
                                df.at[idx, 'Nr_Zlecenia_Zewn'] = "FLOTA WŁASNA"
                                
                            df.at[idx, 'Faza_Procesu'] = "Zamknięte"
                            df.at[idx, 'Zakonczone_Arch'] = "TAK"
                            
                            save_data(worksheet, df)
                            st.session_state["wybrany_event_id"] = None
                            st.success(f"Zlecenie {dane_eventu['Nazwa_Targow']} pomyślnie zamknięte i zarchiwizowane!")
                            st.rerun()
                            
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <div style="height: 100%; display: flex; align-items: center; justify-content: center; background: rgba(30, 41, 59, 0.2); border-radius: 16px; border: 1px dashed rgba(255,255,255,0.1); padding: 40px; text-align: center;">
                            <span style="color: #64748B; line-height: 1.6;">Wybierz zlecenie z listy po lewej stronie,<br>aby wyświetlić panel szczegółów oraz opcje edycji finansów i dokumentów.</span>
                        </div>
                    """, unsafe_allow_html=True)

        else:
            st.info("Brak aktywnych transportów w bazie danych.")

    with tab_formularz:
        st.markdown("<h4 style='color: #D4AF37; margin-top: 0;'>📝 Podstawowe Dane Operacyjne</h4>", unsafe_allow_html=True)
        
        typ_transportu = st.radio("Rodzaj transportu (zmienia układ interfejsu):", ["Zewnętrzny", "Własny SQM"], horizontal=True)
        
        with st.form("form_event_pro", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                nazwa_targow = st.text_input("Nazwa Targów / Eventu *")
                typ_pojazdu = st.text_input("Typ Pojazdu (np. FTL, SOLOWKA, BUS, VAN)")
            with f_col2:
                przewoznik = st.text_input("Przewoźnik / Kierowca * (Dla SQM wpisz nazwisko)")
                faza_procesu = st.selectbox("Faza Procesu", ["Inicjacja", "Planowanie", "Załadunek", "Trasa", "Zamknięte"])
                status_magazyn = st.selectbox("Status Magazyn", ["Brak gotowości", "Częściowo", "100% Gotowe"])

            notatki = st.text_area("Notatki Dodatkowe")
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color: #D4AF37;'>🛫 Status Logistyczny</h4>", unsafe_allow_html=True)
            cmr_gotowe = st.selectbox("Wystawione CMR przed wyjazdem?", ["NIE", "TAK"])
            
            if typ_transportu == "Zewnętrzny":
                st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                st.markdown("<h4 style='color: #D4AF37;'>🏁 Finanse i Dowód Dostawy (POD)</h4>", unsafe_allow_html=True)
                d_col1, d_col2, d_col3 = st.columns(3)
                with d_col1: cmr_podpisane = st.selectbox("Otrzymano podpisane CMR (POD)?", ["NIE", "TAK"])
                with d_col2: pp_otrzymane = st.selectbox("Potw. Przelewu (PP)?", ["", "NIE", "TAK"])
                with d_col3: faktura_opl = st.selectbox("Faktura Opłacona?", ["", "NIE", "TAK"])

                st.markdown("<br>", unsafe_allow_html=True)
                e_col1, e_col2, e_col3 = st.columns(3)
                with e_col1: koszt_transportu = st.number_input("Koszt Transportu (€)", min_value=0.0, value=0.0, step=50.0)
                with e_col2: nr_zlecenia_zewn = st.text_input("Nr Zlecenia Zewnętrznego")
                with e_col3: nr_faktury = st.text_input("Nr Faktury Przewoźnika")
            else:
                st.info("💡 Wybrano Flotę Własną SQM. Sekcja finansowa (faktury, zlecenia zewn., zwroty POD) została ukryta i przyjmie wartość N/A.")
                cmr_podpisane, pp_otrzymane, faktura_opl = "N/A", "N/A", "N/A"
                koszt_transportu, nr_zlecenia_zewn, nr_faktury = "N/A", "FLOTA WŁASNA", "N/A"

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
                        "Nr_Faktury": nr_faktury, "Data_Zakonczenia_Uslugi": "", "Data_Platnosci": "N/A" if typ_transportu == "Własny SQM" else "",
                        "Faktura_Oplacona": faktura_opl, "PP_Otrzymane": pp_otrzymane, "Zakonczone_Arch": "NIE"
                    }

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
