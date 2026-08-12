import streamlit as st
import pandas as pd
import datetime
import os
import base64
import db
from db import load_data, generuj_smart_id
from mod_generator_pdf import generate_cmr_excel

def get_full_address(place_name, df_miejsca):
    """Funkcja pomocnicza do pobierania pełnego adresu z bazy na potrzeby CMR."""
    if place_name == "INNE (wpisz ręcznie)": 
        return ""
    if place_name == "Magazyn SQM Komorniki":
        return "SQM Prosta Spółka Akcyjna ;\nul. Poznańska 165, 62-052 Komorniki,\nNIP: 7792361182"
    if df_miejsca is not None and not df_miejsca.empty:
        row = df_miejsca[df_miejsca['Nazwa do listy'] == place_name]
        if not row.empty:
            r = row.iloc[0]
            return f"{r.get('Nazwa pełna / Firma', place_name)}\n{r.get('Ulica i numer', '')}\n{r.get('Kod pocztowy', '')} {r.get('Miasto', '')}, {r.get('Kraj', '')}"
    return place_name

def render(sh):
    st.markdown("""
        <h2 style='color: #E2DCD3; margin-bottom: 0px; font-weight: 400; font-size: 24px;'>Moduł Operacyjny: Eventy & Flota</h2>
        <div style='color: #8C8477; font-size: 11px; letter-spacing: 2px; margin-bottom: 25px;'>オペレーションモジュール: イベント & フリート</div>
    """, unsafe_allow_html=True)
    
    worksheet, df = load_data(sh, "DB_Eventy")
    
    # POBRANIE SŁOWNIKA MIEJSC
    df_miejsca = db.fetch_data("Miejsca")
    lista_miejsc_baza = df_miejsca['Nazwa do listy'].dropna().tolist() if not df_miejsca.empty else []
    opcje_lokalizacji = ["Magazyn SQM Komorniki"] + lista_miejsc_baza + ["INNE (wpisz ręcznie)"]
    
    if df.empty and not worksheet.row_values(1):
        headers = ["Typ_Transportu", "ID_Zlecenia", "Nazwa_Targow", "Faza_Procesu", "Typ_Pojazdu", "Przewoznik", 
                   "Data_Zlecenia_Tr", "Status_Magazyn", "Notatki", "Koszt_Transportu_EUR", "Nr_Zlecenia_Zewn", 
                   "Nr_Faktury", "Data_Zakonczenia_Uslugi", "Data_Platnosci", "Miejsce_Przeznaczenia", "Waga", 
                   "Nr_Rejestracyjny", "Kierowca", "Nr_CMR", "CMR_Gotowe", "CMR_Podpisane_POD", "Faktura_Oplacona", 
                   "PP_Otrzymane", "Zakonczone_Arch"]
        worksheet.append_row(headers)
        st.cache_data.clear()
        worksheet, df = load_data(sh, "DB_Eventy")
    
    df_aktywne = df[df.get("Zakonczone_Arch", pd.Series()) != "TAK"].copy() if not df.empty else df.copy()
    
    def wymaga_cmr(row_data):
        if str(row_data.get('CMR_Gotowe', '')) == 'NIE':
            typ_transp = str(row_data.get('Typ_Transportu', ''))
            typ_pojazdu = str(row_data.get('Typ_Pojazdu', '')).lower()
            if typ_transp == "Własny SQM" and ("bus" in typ_pojazdu or "van" in typ_pojazdu):
                return False 
            return True
        return False

    braki_cmr = sum(df_aktywne.apply(wymaga_cmr, axis=1)) if not df_aktywne.empty else 0
    braki_pod = len(df_aktywne[df_aktywne.get("CMR_Podpisane_POD", pd.Series()) == "NIE"]) if not df_aktywne.empty else 0
    braki_faktury = len(df_aktywne[df_aktywne.get("Faktura_Oplacona", pd.Series()) == "NIE"]) if not df_aktywne.empty else 0
    
    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-header">Do wystawienia CMR</div>
                <div class="kpi-sub-jp">CMRの発行待ち</div>
                <div class="kpi-value">{braki_cmr}</div>
                <div class="kpi-icon-bg">📝</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">Brakujące zwroty POD</div>
                <div class="kpi-sub-jp">POD返却待ち</div>
                <div class="kpi-value">{braki_pod}</div>
                <div class="kpi-icon-bg">📄</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">Nieopłacone faktury</div>
                <div class="kpi-sub-jp">未払い請求書</div>
                <div class="kpi-value">{braki_faktury}</div>
                <div class="kpi-icon-bg">💰</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_podglad, tab_formularz, tab_archiwum = st.tabs([
        "🗂️ Aktywne Zlecenia", "➕ Utwórz Nowe Zlecenie", "📦 Archiwum (Cold Storage)"
    ])

    with tab_podglad:
        if not df_aktywne.empty:
            
            if "wybrany_event_id" not in st.session_state:
                st.session_state["wybrany_event_id"] = None
            if "filtr_eventow" not in st.session_state:
                st.session_state["filtr_eventow"] = "Wszystkie"

            st.markdown("<p style='color: #94A3B8; font-size: 12px; font-weight: 700; letter-spacing: 1px; margin-bottom: 5px; text-transform: uppercase;'>⚡ Wyszukaj i filtruj zlecenia:</p>", unsafe_allow_html=True)
            
            wyszukiwarka = st.text_input(
                "Wyszukiwarka", 
                placeholder="🔍 Wpisz nazwę targów, przewoźnika, ID zlecenia, fakturę (rozdzielaj przecinkiem)...",
                label_visibility="collapsed"
            )
            st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            active_filter = st.session_state["filtr_eventow"]
            
            def get_filter_style(is_active):
                if is_active:
                    return "background: linear-gradient(135deg, rgba(197, 168, 128, 0.35) 0%, rgba(197, 168, 128, 0.15) 100%); border: 1px solid #C5A880; box-shadow: 0 4px 15px rgba(0,0,0,0.3);"
                else:
                    return "background: rgba(28, 26, 24, 0.75); border: 1px solid rgba(197, 168, 128, 0.15); box-shadow: 0 2px 8px rgba(0,0,0,0.2);"

            with f_col1:
                st.markdown(f"""
                <div style="{get_filter_style(active_filter == 'Wszystkie')} border-radius: 8px; padding: 12px 15px; text-align: center; height: 75px; display: flex; flex-direction: column; justify-content: center; backdrop-filter: blur(10px);">
                    <div style="color: #E2DCD3; font-size: 12px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Wszystkie</div>
                    <div style="color: #8C8477; font-size: 11px; margin-top: 3px; font-family: 'Noto Serif JP', serif;">すべて</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Filtruj Wszystkie", use_container_width=True, key="btn_f_all"):
                    st.session_state["filtr_eventow"] = "Wszystkie"
                    st.session_state["wybrany_event_id"] = None
                    st.rerun()

            with f_col2:
                st.markdown(f"""
                <div style="{get_filter_style(active_filter == 'BrakCMR')} border-radius: 8px; padding: 12px 15px; text-align: center; height: 75px; display: flex; flex-direction: column; justify-content: center; backdrop-filter: blur(10px);">
                    <div style="color: #E2DCD3; font-size: 12px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Brak CMR ({braki_cmr})</div>
                    <div style="color: #8C8477; font-size: 11px; margin-top: 3px; font-family: 'Noto Serif JP', serif;">CMRなし</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Filtruj Brak CMR", use_container_width=True, key="btn_f_cmr"):
                    st.session_state["filtr_eventow"] = "BrakCMR"
                    st.session_state["wybrany_event_id"] = None
                    st.rerun()

            with f_col3:
                st.markdown(f"""
                <div style="{get_filter_style(active_filter == 'BrakPOD')} border-radius: 8px; padding: 12px 15px; text-align: center; height: 75px; display: flex; flex-direction: column; justify-content: center; backdrop-filter: blur(10px);">
                    <div style="color: #E2DCD3; font-size: 12px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Brak POD ({braki_pod})</div>
                    <div style="color: #8C8477; font-size: 11px; margin-top: 3px; font-family: 'Noto Serif JP', serif;">POD受領待ち</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Filtruj Brak POD", use_container_width=True, key="btn_f_pod"):
                    st.session_state["filtr_eventow"] = "BrakPOD"
                    st.session_state["wybrany_event_id"] = None
                    st.rerun()

            with f_col4:
                st.markdown(f"""
                <div style="{get_filter_style(active_filter == 'BrakFaktury')} border-radius: 8px; padding: 12px 15px; text-align: center; height: 75px; display: flex; flex-direction: column; justify-content: center; backdrop-filter: blur(10px);">
                    <div style="color: #E2DCD3; font-size: 12px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Nieopłacone ({braki_faktury})</div>
                    <div style="color: #8C8477; font-size: 11px; margin-top: 3px; font-family: 'Noto Serif JP', serif;">未払い請求書</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Filtruj Nieopłacone", use_container_width=True, key="btn_f_fak"):
                    st.session_state["filtr_eventow"] = "BrakFaktury"
                    st.session_state["wybrany_event_id"] = None
                    st.rerun()
            
            df_widok = df_aktywne.copy()
            
            if st.session_state["filtr_eventow"] == "BrakCMR":
                df_widok = df_widok[df_widok.apply(wymaga_cmr, axis=1)]
            elif st.session_state["filtr_eventow"] == "BrakPOD":
                df_widok = df_widok[df_widok.get("CMR_Podpisane_POD", pd.Series()) == "NIE"]
            elif st.session_state["filtr_eventow"] == "BrakFaktury":
                df_widok = df_widok[df_widok.get("Faktura_Oplacona", pd.Series()) == "NIE"]

            if wyszukiwarka and not df_widok.empty:
                frazy = [f.strip().lower() for f in wyszukiwarka.split(",") if f.strip()]
                for fraza in frazy:
                    if not df_widok.empty:
                        maska = df_widok.astype(str).apply(lambda x: ' '.join(x).lower(), axis=1).str.contains(fraza, regex=False)
                        df_widok = df_widok[maska]

            if not df_widok.empty and 'Data_Zlecenia_Tr' in df_widok.columns:
                df_widok['_temp_date'] = pd.to_datetime(df_widok['Data_Zlecenia_Tr'], errors='coerce')
                df_widok = df_widok.sort_values(by='_temp_date', ascending=True, na_position='last')
                df_widok = df_widok.drop(columns=['_temp_date'])

            st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 20px 0 25px 0;'>", unsafe_allow_html=True)
            
            col_lista, col_detale = st.columns([65, 35], gap="large")
            
            with col_lista:
                if df_widok.empty:
                    if wyszukiwarka:
                        st.warning(f"Brak zleceń pasujących do frazy: **{wyszukiwarka}** w wybranym filtrze.")
                    else:
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
                        
                        is_sqm_row = row.get('Typ_Transportu', '') == "Własny SQM"
                        braki_tagi_html = ""
                        
                        if wymaga_cmr(row):
                            braki_tagi_html += f"<span class='tag-zen-red'>🚨 WYSTAW CMR</span>"
                        
                        if not is_sqm_row:
                            if str(row.get('CMR_Podpisane_POD', '')) == 'NIE':
                                braki_tagi_html += f"<span class='tag-zen-orange'>📄 BRAK POD</span>"
                            if str(row.get('Faktura_Oplacona', '')) == 'NIE':
                                braki_tagi_html += f"<span class='tag-zen-red'>💰 NIEOPŁACONE</span>"
                            if str(row.get('PP_Otrzymane', '')) == 'NIE':
                                braki_tagi_html += f"<span class='tag-zen-blue'>💳 BRAK PP</span>"

                        if braki_tagi_html:
                            tags_div = f'<div style="margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap;">{braki_tagi_html}</div>'
                        else:
                            tags_div = ""

                        data_zal_lista = str(row.get('Data_Zlecenia_Tr', '')).strip()
                        if data_zal_lista in ['', 'None', 'nan', 'NaT']:
                            data_zal_lista = 'Brak danych'
                            
                        notatki_str = str(row.get('Notatki', ''))
                        data_roz_lista = "Brak danych"
                        if "[Rozładunki:" in notatki_str:
                            try: data_roz_lista = notatki_str.split("[Rozładunki:")[1].split("]")[0].strip()
                            except: pass

                        c_karta, c_btn = st.columns([8, 2], vertical_alignment="center")
                        
                        with c_karta:
                            html_karta = f"""
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
            <span class="cr-text" style="margin-bottom: 2px; font-size: 12px;">📅 Załadunek: <b style="color: #C5A880;">{data_zal_lista}</b></span>
            <span class="cr-text" style="margin-bottom: 6px; font-size: 12px;">🏁 Rozładunek: <b style="color: #83A5DB;">{data_roz_lista}</b></span>
            <span class="{badge_class}">{row.get('Faza_Procesu', '-')}</span>
        </div>
    </div>
    {tags_div}
</div>
"""
                            st.markdown(html_karta, unsafe_allow_html=True)
                            
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
                        <div style="background: rgba(28, 26, 24, 0.85); padding: 25px; border-radius: 8px; border: 1px solid rgba(197, 168, 128, 0.3);">
                            <p style="color: #8C8477; font-size: 11px; font-weight: 700; letter-spacing: 1px; margin-bottom: 5px; text-transform: uppercase;">Szczegóły Operacji</p>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"<h3 style='color: #E2DCD3; margin-top: 0;'>{dane_eventu['Nazwa_Targow']}</h3>", unsafe_allow_html=True)
                    
                    c_id, c_cmr, c_dup = st.columns([4, 3, 3])
                    with c_id:
                        st.caption(f"🆔 {dane_eventu['ID_Zlecenia']}<br>👤 {dane_eventu['Przewoznik']}", unsafe_allow_html=True)
                        
                    with c_cmr:
                        if is_sqm:
                            waga_val = str(dane_eventu.get("Waga", "0"))
                            waga_int = int(float(waga_val)) if waga_val.replace('.','',1).isdigit() else 0
                            
                            nr_cmr_zapisany = str(dane_eventu.get("Nr_CMR", ""))
                            
                            if not nr_cmr_zapisany or nr_cmr_zapisany.strip() in ["", "nan", "None"]:
                                if st.button("📝 Wygeneruj Nr CMR", use_container_width=True):
                                    with st.spinner("Pobieranie numeru CMR z puli..."):
                                        nowy_nr = db.get_next_cmr_number()
                                        idx = df_widok[df_widok['ID_Zlecenia'] == dane_eventu['ID_Zlecenia']].index[0]
                                        
                                        df_do_zapisu = df.copy()
                                        df_do_zapisu.at[idx, 'Nr_CMR'] = nowy_nr
                                        gs_row = int(df_do_zapisu.at[idx, 'sheet_row'])
                                        db.update_single_row_safe("DB_Eventy", gs_row, df_do_zapisu.loc[idx])
                                        st.rerun()
                            else:
                                try:
                                    resolved_dest = get_full_address(dane_eventu.get("Miejsce_Przeznaczenia", dane_eventu['Nazwa_Targow']), df_miejsca)
                                    dane_cmr = {
                                        "odbiorca": "SQM Prosta Spółka Akcyjna ;\nul. Poznańska 165, 62-052 Komorniki,\nNIP: 7792361182",
                                        "miejsce_przeznaczenia": resolved_dest,
                                        "data_zal": str(dane_eventu.get("Data_Zlecenia_Tr", "")),
                                        "miasto_zal": "Komorniki, PL",
                                        "opis_ladunku": "MULTIMEDIA / Exhibition Equipment",
                                        "waga": waga_int,
                                        "nr_cmr": nr_cmr_zapisany,
                                        "auto": str(dane_eventu.get("Nr_Rejestracyjny", "")),
                                        "kierowca": str(dane_eventu.get("Kierowca", "")),
                                        "przewoznik": str(dane_eventu.get("Przewoznik", ""))
                                    }
                                    cmr_bytes = generate_cmr_excel(dane_cmr)
                                    
                                    st.caption("💡 Zapisz formularz edycji na dole, aby przycisk pobrał nowe dane.")
                                    st.download_button(
                                        label=f"📥 Pobierz ZAKTUALIZOWANY CMR ({nr_cmr_zapisany})",
                                        data=cmr_bytes,
                                        file_name=f"CMR_{dane_eventu['ID_Zlecenia']}_{nr_cmr_zapisany}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        use_container_width=True
                                    )
                                except Exception as e:
                                    st.error("Szablon CMR niedostępny.")
                        else:
                            st.info("💡 Zewn. transport. Wygeneruj CMR w Module PRO.")

                    with c_dup:
                        if st.button("📋 Klonuj", key=f"clone_{dane_eventu['ID_Zlecenia']}", use_container_width=True):
                            nowy_wiersz = dane_eventu.copy().to_dict()
                            nowy_wiersz['ID_Zlecenia'] = "" 
                            nowy_wiersz['Faza_Procesu'] = "Inicjacja"
                            nowy_wiersz['Status_Magazyn'] = "Brak gotowości"
                            nowy_wiersz['CMR_Gotowe'] = "NIE"
                            nowy_wiersz['Nr_CMR'] = "" # Klon nie kopiuje numeru CMR
                            
                            is_sqm_clone = (nowy_wiersz['Typ_Transportu'] == "Własny SQM")
                            nowy_wiersz['CMR_Podpisane_POD'] = "N/A" if is_sqm_clone else "NIE"
                            nowy_wiersz['Faktura_Oplacona'] = "N/A" if is_sqm_clone else "NIE"
                            nowy_wiersz['PP_Otrzymane'] = "N/A" if is_sqm_clone else "NIE"
                            nowy_wiersz['Nr_Faktury'] = "N/A" if is_sqm_clone else ""
                            nowy_wiersz['Data_Platnosci'] = "N/A" if is_sqm_clone else ""
                            nowy_wiersz['Zakonczone_Arch'] = "NIE"
                            nowy_wiersz['Notatki'] = "Klon zlecenia " + str(dane_eventu['ID_Zlecenia']) + " - " + str(nowy_wiersz.get('Notatki', ''))
                            
                            if 'sheet_row' in nowy_wiersz:
                                del nowy_wiersz['sheet_row']
                                
                            df_temp = pd.concat([df, pd.DataFrame([nowy_wiersz])], ignore_index=True)
                            df_temp = generuj_smart_id(df_temp, "Nazwa_Targow", "Przewoznik", "ID_Zlecenia")
                            nowy_wiersz_z_id = df_temp.iloc[-1]
                            
                            kolumny = [k for k in df.columns if k != 'sheet_row']
                            wiersz_lista = [nowy_wiersz_z_id.get(k, "") for k in kolumny]
                            
                            db.append_data("DB_Eventy", wiersz_lista)
                            st.session_state["wybrany_event_id"] = None 
                            st.success("✅ Skopiowano zlecenie (Bezpieczny zapis)!")
                            st.rerun()

                    typ_pojazdu_lower = str(dane_eventu['Typ_Pojazdu']).lower()
                    if "ftl" in typ_pojazdu_lower: plik_img = "ftl.png"
                    elif "bus" in typ_pojazdu_lower: plik_img = "bus.png"
                    elif "van" in typ_pojazdu_lower: plik_img = "van.png"
                    elif "sol" in typ_pojazdu_lower: plik_img = "solowka.png"
                    else: plik_img = "default.png"
                    
                    if os.path.exists(plik_img):
                        with open(plik_img, "rb") as f:
                            b64_img = base64.b64encode(f.read()).decode()
                        st.markdown(f"""
                        <div style="width: 100%; background: rgba(0,0,0,0.3); border-radius: 8px; overflow: hidden; margin: 15px 0; border: 1px solid rgba(197, 168, 128, 0.2);">
                            <img src="data:image/png;base64,{b64_img}" style="width: 100%; height: auto; display: block; object-fit: cover;">
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="width: 100%; height: 120px; background: rgba(0,0,0,0.2); border-radius: 8px; border: 1px dashed rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: center; margin: 15px 0;">
                            <span style="color: rgba(255,255,255,0.3); font-size: 13px;">Brak grafiki ({plik_img})</span>
                        </div>
                        """, unsafe_allow_html=True)

                    braki_zlecenia = []
                    if wymaga_cmr(dane_eventu):
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
                        <div style="background: rgba(186, 73, 73, 0.05); border: 1px solid rgba(186, 73, 73, 0.3); padding: 15px 20px; border-radius: 8px; margin: 15px 0;">
                            <h4 style="color: #BA4949; margin: 0 0 10px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">⚠️ Wymagane Akcje:</h4>
                            <ul style="color: #E2DCD3; font-size: 13px; margin: 0; padding-left: 20px;">
                                {lista_brakow}
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background: rgba(119, 163, 133, 0.05); border: 1px solid rgba(119, 163, 133, 0.3); padding: 12px 15px; border-radius: 8px; margin: 15px 0; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 18px;">✅</span>
                            <span style="color: #77A385; font-size: 13px; font-weight: 600;">Wszystkie dokumenty i rozliczenia są kompletne.</span>
                        </div>
                        """, unsafe_allow_html=True)

                    det_info, det_har, det_fin, det_arch = st.tabs(["📝 EDYCJA", "⏱️ HARMONOGRAM", "💼 FINANSE", "🏁 ZAKOŃCZ"])
                    
                    with det_info:
                        with st.form(key=f"edit_all_{dane_eventu['ID_Zlecenia']}"):
                            st.markdown("<p style='color:#C5A880; font-weight:700; margin-bottom:5px; font-size: 14px;'>🔄 Edycja Danych Podstawowych</p>", unsafe_allow_html=True)
                            
                            c_ed1, c_ed2 = st.columns(2)
                            with c_ed1:
                                u_id_zlecenia = st.text_input("ID Zlecenia (Wewn. / PRO)", value=str(dane_eventu.get('ID_Zlecenia', '')))
                                u_nazwa = st.text_input("Nazwa Targów / Eventu", value=str(dane_eventu.get('Nazwa_Targow', '')))
                                
                                # ---- ADRES DOCELOWY (EDIT) Z LISTY ROZWIJANEJ ----
                                akt_miejsce = str(dane_eventu.get('Miejsce_Przeznaczenia', ''))
                                if akt_miejsce in opcje_lokalizacji:
                                    idx_m = opcje_lokalizacji.index(akt_miejsce)
                                    init_m_man = ""
                                else:
                                    idx_m = opcje_lokalizacji.index("INNE (wpisz ręcznie)") if "INNE (wpisz ręcznie)" in opcje_lokalizacji else 0
                                    init_m_man = akt_miejsce
                                    
                                u_miejsce_sel = st.selectbox("Miejsce docelowe (do CMR)", opcje_lokalizacji, index=idx_m)
                                u_miejsce_man = st.text_area("Adres docelowy (ręcznie)", value=init_m_man) if u_miejsce_sel == "INNE (wpisz ręcznie)" else ""
                                final_miejsce_edit = u_miejsce_man if u_miejsce_sel == "INNE (wpisz ręcznie)" else u_miejsce_sel

                                u_przewoznik = st.text_input("Przewoźnik / Firma Transportowa", value=str(dane_eventu.get('Przewoznik', '')))
                                u_typ_transp = st.selectbox("Typ Transportu", ["Zewnętrzny", "Własny SQM"], index=0 if str(dane_eventu.get('Typ_Transportu', '')) == "Zewnętrzny" else 1)
                                
                                fazy_lista = ["Inicjacja", "Planowanie", "Załadunek", "Trasa", "Zamknięte"]
                                akt_faza = dane_eventu.get("Faza_Procesu", "Inicjacja")
                                idx_fazy = fazy_lista.index(akt_faza) if akt_faza in fazy_lista else 0
                                u_faza = st.selectbox("Faza Procesu", fazy_lista, index=idx_fazy)
                                
                            with c_ed2:
                                u_typ_pojazd = st.text_input("Typ Pojazdu", value=str(dane_eventu.get('Typ_Pojazdu', '')))
                                u_nr_rejestracyjny = st.text_input("Nr Rejestracyjny (do CMR)", value=str(dane_eventu.get('Nr_Rejestracyjny', '')))
                                u_kierowca = st.text_input("Imię Kierowcy (do CMR)", value=str(dane_eventu.get('Kierowca', '')))
                                
                                waga_akt = str(dane_eventu.get('Waga', '0'))
                                u_waga = st.number_input("Waga (kg)", min_value=0, value=int(float(waga_akt)) if waga_akt.replace('.', '', 1).isdigit() else 0, step=100)
                                
                                dp_trasa = str(dane_eventu.get("Data_Zlecenia_Tr", "")).strip()
                                try: dp_parsed = datetime.datetime.strptime(dp_trasa, "%Y-%m-%d").date() if dp_trasa not in ["", "None", "nan", "NaT", "N/A", "no info"] else None
                                except: dp_parsed = None
                                u_data_tr = st.date_input("Data Załadunku", value=dp_parsed)
                                
                                st.markdown("<p style='font-size: 12px; color: #8C8477; margin-bottom: 2px;'>Daty rozładunku na targach:</p>", unsafe_allow_html=True)
                                r_ed1, r_ed2 = st.columns(2)
                                u_data_roz_1 = r_ed1.date_input("Rozładunek 1:", value=None)
                                u_data_roz_2 = r_ed2.date_input("Rozładunek 2 (Opcjonalnie):", value=None)
                                
                                mag_lista = ["Brak gotowości", "Częściowo", "100% Gotowe"]
                                akt_mag = dane_eventu.get("Status_Magazyn", "Brak gotowości")
                                idx_mag = mag_lista.index(akt_mag) if akt_mag in mag_lista else 0
                                u_status_mag = st.selectbox("Status Magazyn", mag_lista, index=idx_mag)

                            u_notatki = st.text_area("Notatki", value=str(dane_eventu.get('Notatki', '')))
                            
                            if st.form_submit_button("💾 Zapisz Zmiany"):
                                idx = df[df['ID_Zlecenia'] == dane_eventu['ID_Zlecenia']].index[0]
                                
                                df.at[idx, 'ID_Zlecenia'] = u_id_zlecenia
                                df.at[idx, 'Nazwa_Targow'] = u_nazwa
                                df.at[idx, 'Miejsce_Przeznaczenia'] = final_miejsce_edit
                                df.at[idx, 'Przewoznik'] = u_przewoznik
                                df.at[idx, 'Typ_Transportu'] = u_typ_transp
                                df.at[idx, 'Typ_Pojazdu'] = u_typ_pojazd
                                df.at[idx, 'Nr_Rejestracyjny'] = u_nr_rejestracyjny
                                df.at[idx, 'Kierowca'] = u_kierowca
                                df.at[idx, 'Waga'] = u_waga
                                
                                if u_typ_transp == "Zewnętrzny":
                                    df.at[idx, 'Nr_Zlecenia_Zewn'] = u_id_zlecenia
                                else:
                                    df.at[idx, 'Nr_Zlecenia_Zewn'] = "FLOTA WŁASNA"
                                
                                df.at[idx, 'Faza_Procesu'] = u_faza
                                df.at[idx, 'Status_Magazyn'] = u_status_mag
                                df.at[idx, 'Data_Zlecenia_Tr'] = str(u_data_tr) if u_data_tr else ""
                                
                                rozładunki_str = str(u_data_roz_1) if u_data_roz_1 else ""
                                if u_data_roz_2:
                                    rozładunki_str += f", {u_data_roz_2}"
                                if rozładunki_str:
                                    df.at[idx, 'Notatki'] = f"[Rozładunki: {rozładunki_str}] {u_notatki}"
                                else:
                                    df.at[idx, 'Notatki'] = u_notatki
                                
                                gs_row = int(df.at[idx, 'sheet_row'])
                                db.update_single_row_safe("DB_Eventy", gs_row, df.loc[idx])
                                
                                st.session_state["wybrany_event_id"] = u_id_zlecenia 
                                st.success("Pomyślnie zaktualizowano dane!")
                                st.rerun()

                    with det_har:
                        worksheet_sloty, df_sloty = load_data(sh, "DB_Sloty")
                        sloty_eventu = df_sloty[df_sloty['ID_Zlecenia'] == dane_eventu['ID_Zlecenia']] if not df_sloty.empty else pd.DataFrame()
                        
                        st.markdown("<p style='color:#C5A880; font-weight:700; margin-bottom:15px; font-size: 14px;'>📍 Zarezerwowane Okna Czasowe</p>", unsafe_allow_html=True)
                        
                        if not sloty_eventu.empty:
                            for idx, slot in sloty_eventu.iterrows():
                                st.markdown(f"""
                                <div style="background: rgba(255,255,255,0.02); border-left: 3px solid #C5A880; padding: 10px 15px; border-radius: 4px; margin-bottom: 10px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <div>
                                            <strong style="color: #E2DCD3; font-size: 14px;">{slot.get('Typ_Operacji', '-')}</strong>
                                            <span style="color: #8C8477; font-size: 12px; margin-left: 10px;">📅 {slot.get('Data_Slota', '-')} | ⏰ {slot.get('Godzina_Od', '-')} - {slot.get('Godzina_Do', '-')}</span>
                                        </div>
                                        <div style="background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px; font-size: 11px; color: #C5A880;">
                                            Brama: {slot.get('Brama_Rampa', 'Brak') or 'Brak'}
                                        </div>
                                    </div>
                                    <div style="color: #8C8477; font-size: 12px; margin-top: 5px;">{slot.get('Notatki', '')}</div>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("Brak przypisanych slotów dla tego transportu.")

                        st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 15px 0;'>", unsafe_allow_html=True)
                        
                        with st.form(key=f"form_add_slot_{dane_eventu['ID_Zlecenia']}", clear_on_submit=True):
                            st.markdown("<p style='color:#C5A880; font-weight:700; margin-bottom:5px; font-size: 14px;'>➕ Dodaj Nowy Slot</p>", unsafe_allow_html=True)
                            
                            s_col1, s_col2 = st.columns(2)
                            with s_col1:
                                s_typ = st.selectbox("Typ Operacji", ["Montaż", "Odbiór Empties", "Demontaż", "Załadunek (Magazyn)", "Rozładunek (Magazyn)", "Inne"])
                                s_data = st.date_input("Data", value=None)
                            with s_col2:
                                ss_col1, ss_col2 = st.columns(2)
                                with ss_col1: s_od = st.time_input("Godz. Od", value=None)
                                with ss_col2: s_do = st.time_input("Godz. Do", value=None)
                                s_brama = st.text_input("Brama / Rampa (Gate)")
                                
                            s_notatki = st.text_input("Dodatkowe Notatki")
                            
                            if st.form_submit_button("💾 Zapisz Slot"):
                                nowy_slot = [
                                    dane_eventu['ID_Zlecenia'],
                                    s_typ,
                                    str(s_data) if s_data else "",
                                    s_od.strftime("%H:%M") if s_od else "",
                                    s_do.strftime("%H:%M") if s_do else "",
                                    s_brama,
                                    s_notatki
                                ]
                                db.append_data("DB_Sloty", nowy_slot)
                                st.success("Dodano nowy slot!")
                                st.rerun()
                        
                    with det_fin:
                        with st.form(key=f"update_fin_{dane_eventu['ID_Zlecenia']}"):
                            st.markdown("<p style='color:#C5A880; font-weight:700; margin-bottom:5px; font-size: 14px;'>🗃️ Status Dokumentacji i Rozliczeń</p>", unsafe_allow_html=True)
                            
                            if is_sqm:
                                u_cmr = st.selectbox("CMR Gotowe?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_eventu.get("CMR_Gotowe", "")) if dane_eventu.get("CMR_Gotowe", "") in ["", "NIE", "TAK"] else 0)
                                st.info("🚚 Pojazd własnej floty SQM. Pola finansowe są automatycznie ustawione na N/A.")
                                u_pod, u_pp, u_koszt, u_nr_fak, u_faktura_opl, u_data_platnosci = "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"
                            else:
                                col_d1, col_d2, col_d3 = st.columns(3)
                                with col_d1: u_cmr = st.selectbox("CMR Gotowe?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_eventu.get("CMR_Gotowe", "")) if dane_eventu.get("CMR_Gotowe", "") in ["", "NIE", "TAK"] else 0)
                                with col_d2: u_pod = st.selectbox("CMR POD?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_eventu.get("CMR_Podpisane_POD", "")) if dane_eventu.get("CMR_Podpisane_POD", "") in ["", "NIE", "TAK"] else 0)
                                with col_d3: u_pp = st.selectbox("Potw. Przelewu (PP)?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_eventu.get("PP_Otrzymane", "")) if dane_eventu.get("PP_Otrzymane", "") in ["", "NIE", "TAK"] else 0)
                                
                                st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 10px 0;'>", unsafe_allow_html=True)
                                st.markdown("<p style='color:#C5A880; font-weight:700; margin-bottom:5px; font-size: 14px;'>💰 Koszty i Faktury</p>", unsafe_allow_html=True)
                                
                                col_f1, col_f2 = st.columns(2)
                                with col_f1: 
                                    koszt_str = str(dane_eventu.get("Koszt_Transportu_EUR", 0.0))
                                    koszt_val = float(koszt_str) if koszt_str.replace('.', '', 1).isdigit() else 0.0
                                    u_koszt = st.number_input("Koszt (EUR)", min_value=0.0, value=koszt_val, step=50.0)
                                    
                                    st.info(f"Numer referencyjny na zewnątrz: {dane_eventu.get('Nr_Zlecenia_Zewn', '')}")
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
                                    
                                gs_row = int(df.at[idx, 'sheet_row'])
                                db.update_single_row_safe("DB_Eventy", gs_row, df.loc[idx])
                                
                                st.success("Zaktualizowano finanse!")
                                st.rerun()

                    with det_arch:
                        st.info("Zarchiwizowanie transportu usunie go z widoku aktywnych operacji i przeniesie do Cold Storage.")
                        if st.button("🏁 ZAKOŃCZ I ARCHIWIZUJ", type="primary", use_container_width=True):
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
                            
                            wiersz_do_archiwum = df.loc[idx].copy()
                            gs_row = int(wiersz_do_archiwum['sheet_row'])
                            if 'sheet_row' in wiersz_do_archiwum:
                                wiersz_do_archiwum = wiersz_do_archiwum.drop('sheet_row')
                                
                            db.archive_row_safe("DB_Eventy", "DB_Eventy ARCHIWUM", gs_row, wiersz_do_archiwum.tolist())
                            
                            st.session_state["wybrany_event_id"] = None
                            st.success(f"Zlecenie zamknięte i przeniesione do fizycznego archiwum Cold Storage!")
                            st.rerun()
                            
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <div style="height: 100%; display: flex; align-items: center; justify-content: center; background: rgba(28, 26, 24, 0.5); border-radius: 8px; border: 1px dashed rgba(255,255,255,0.1); padding: 40px; text-align: center;">
                            <span style="color: #8C8477; line-height: 1.6;">Wybierz zlecenie z listy po lewej stronie,<br>aby wyświetlić panel szczegółów i edycję.</span>
                        </div>
                    """, unsafe_allow_html=True)

        else:
            st.info("Brak aktywnych transportów w bazie danych.")

    with tab_formularz:
        with st.expander("➕ Brak miejsca na liście? Dodaj nową lokalizację do Słownika"):
            with st.form("form_nowe_miejsce_evt", clear_on_submit=True):
                nowa_nazwa_lista = st.text_input("Nazwa skrócona (do listy wyboru):*", placeholder="np. BERLIN, DE - Messe Berlin")
                nowa_firma = st.text_input("Pełna nazwa / Firma:")
                nowa_ulica = st.text_input("Ulica i numer:")
                nowy_kod = st.text_input("Kod pocztowy:")
                nowe_miasto = st.text_input("Miasto:")
                
                k1, k2 = st.columns(2)
                nowy_kraj = k1.text_input("Kraj:", value="Polska")
                nowy_skrot = k2.text_input("Skrót Kraju (do CMR):", value="PL")
                
                if st.form_submit_button("💾 Zapisz lokalizację w bazie"):
                    if nowa_nazwa_lista.strip():
                        kolumny_miejsca = df_miejsca.columns.tolist() if not df_miejsca.empty else ["Nazwa do listy", "Nazwa pełna / Firma", "Ulica i numer", "Kod pocztowy", "Miasto", "Kraj", "Skrót Kraju"]
                        slownik_nowego = {
                            "Nazwa do listy": nowa_nazwa_lista.strip(), 
                            "Nazwa pełna / Firma": nowa_firma.strip(), 
                            "Ulica i numer": nowa_ulica.strip(), 
                            "Kod pocztowy": nowy_kod.strip(), 
                            "Miasto": nowe_miasto.strip(), 
                            "Kraj": nowy_kraj.strip(),
                            "Skrót Kraju": nowy_skrot.strip()
                        }
                        nowy_wiersz = [slownik_nowego.get(kol, "") for kol in kolumny_miejsca]
                        if db.append_data("Miejsca", nowy_wiersz):
                            st.success(f"✅ Dodano pomyślnie: {nowa_nazwa_lista}")
                            st.cache_data.clear()
                            st.rerun()

        st.markdown("<h4 style='color: #C5A880; margin-top: 0;'>📝 Podstawowe Dane Operacyjne</h4>", unsafe_allow_html=True)
        
        typ_transportu = st.radio("Rodzaj transportu:", ["Zewnętrzny", "Własny SQM"], horizontal=True)
        
        with st.form("form_event_pro", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                id_zlecenia_custom = st.text_input("Własne ID Zlecenia (Opcjonalnie)", placeholder="Zostaw puste by wygenerować automatycznie")
                nazwa_targow = st.text_input("Nazwa Targów / Eventu *")
                
                # ---- ADRES DOCELOWY (NOWE ZLECENIE) Z LISTY ROZWIJANEJ ----
                u_miejsce_sel_c = st.selectbox("Miejsce docelowe (Odbiorca na CMR)", opcje_lokalizacji)
                u_miejsce_man_c = st.text_area("Adres Docelowy (ręcznie)") if u_miejsce_sel_c == "INNE (wpisz ręcznie)" else ""
                
                typ_pojazdu = st.text_input("Typ Pojazdu (np. FTL, SOLOWKA, BUS, VAN)")
                data_zaladunku_nowa = st.date_input("Data Załadunku", value=None)
                
                st.markdown("<p style='font-size: 12px; color: #8C8477; margin-top: 5px; margin-bottom: 2px;'>Daty rozładunku na obiekcie (wiele dni):</p>", unsafe_allow_html=True)
                r_form1, r_form2 = st.columns(2)
                data_rozladunku_1 = r_form1.date_input("Rozładunek 1:", value=None)
                data_rozladunku_2 = r_form2.date_input("Rozładunek 2 (Opcjonalnie):", value=None)
                
            with f_col2:
                przewoznik = st.text_input("Przewoźnik / Firma Transportowa *")
                kierowca = st.text_input("Imię i Nazwisko Kierowcy (do CMR)")
                nr_rejestracyjny = st.text_input("Nr Rejestracyjny Pojazdu (do CMR)")
                waga = st.number_input("Waga (kg)", min_value=0, step=100)
                
                faza_procesu = st.selectbox("Faza Procesu", ["Inicjacja", "Planowanie", "Załadunek", "Trasa", "Zamknięte"])
                status_magazyn = st.selectbox("Status Magazyn", ["Brak gotowości", "Częściowo", "100% Gotowe"])

            notatki = st.text_area("Notatki Dodatkowe")
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color: #C5A880;'>🛫 Status Logistyczny</h4>", unsafe_allow_html=True)
            cmr_gotowe = st.selectbox("Wystawione CMR przed wyjazdem?", ["NIE", "TAK"])
            
            if typ_transportu == "Zewnętrzny":
                st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                st.markdown("<h4 style='color: #C5A880;'>🏁 Finanse i Dowód Dostawy (POD)</h4>", unsafe_allow_html=True)
                d_col1, d_col2, d_col3 = st.columns(3)
                with d_col1: cmr_podpisane = st.selectbox("Otrzymano podpisane CMR (POD)?", ["NIE", "TAK"])
                with d_col2: pp_otrzymane = st.selectbox("Potw. Przelewu (PP)?", ["", "NIE", "TAK"])
                with d_col3: faktura_opl = st.selectbox("Faktura Opłacona?", ["", "NIE", "TAK"])

                st.markdown("<br>", unsafe_allow_html=True)
                e_col1, e_col2 = st.columns(2)
                with e_col1: koszt_transportu = st.number_input("Koszt Transportu (€)", min_value=0.0, value=0.0, step=50.0)
                with e_col2: nr_faktury = st.text_input("Nr Faktury Przewoźnika")
            else:
                st.info("💡 Wybrano Flotę Własną SQM. Sekcja finansowa i zewnętrzna została pominięta.")
                cmr_podpisane, pp_otrzymane, faktura_opl = "N/A", "N/A", "N/A"
                koszt_transportu, nr_faktury = "N/A", "N/A"

            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("🚀 Zainicjuj Zlecenie Systemowe"):
                if not nazwa_targow or not przewoznik:
                    st.error("❌ Uzupełnij nazwę targów oraz przewoźnika!")
                else:
                    if typ_transportu == "Zewnętrzny":
                        nr_zewn_final = id_zlecenia_custom
                    else:
                        nr_zewn_final = "FLOTA WŁASNA"
                        
                    roz_str = str(data_rozladunku_1) if data_rozladunku_1 else ""
                    if data_rozladunku_2:
                        roz_str += f", {data_rozladunku_2}"
                    
                    finalne_notatki = notatki
                    if roz_str:
                        finalne_notatki = f"[Rozładunki: {roz_str}] {notatki}"
                        
                    finalne_miejsce_przeznaczenia = u_miejsce_man_c if u_miejsce_sel_c == "INNE (wpisz ręcznie)" else u_miejsce_sel_c
                        
                    nowy_wiersz = {
                        "ID_Zlecenia": id_zlecenia_custom, "Nazwa_Targow": nazwa_targow, "Typ_Transportu": typ_transportu,
                        "Faza_Procesu": faza_procesu, "Typ_Pojazdu": typ_pojazdu, "Przewoznik": przewoznik,
                        "Data_Zlecenia_Tr": str(data_zaladunku_nowa) if data_zaladunku_nowa else "", 
                        "Status_Magazyn": status_magazyn,
                        "Notatki": finalne_notatki, "Koszt_Transportu_EUR": koszt_transportu, "CMR_Gotowe": cmr_gotowe, 
                        "CMR_Podpisane_POD": cmr_podpisane, "Nr_Zlecenia_Zewn": nr_zewn_final, 
                        "Nr_Faktury": nr_faktury, "Data_Zakonczenia_Uslugi": "", "Data_Platnosci": "N/A" if typ_transportu == "Własny SQM" else "",
                        "Faktura_Oplacona": faktura_opl, "PP_Otrzymane": pp_otrzymane, "Zakonczone_Arch": "NIE",
                        "Miejsce_Przeznaczenia": finalne_miejsce_przeznaczenia, "Waga": waga, "Nr_Rejestracyjny": nr_rejestracyjny, 
                        "Kierowca": kierowca, "Nr_CMR": ""
                    }

                    df_temp = pd.concat([df, pd.DataFrame([nowy_wiersz])], ignore_index=True)
                    df_temp = generuj_smart_id(df_temp, "Nazwa_Targow", "Przewoznik", "ID_Zlecenia")
                    nowy_wiersz_z_id = df_temp.iloc[-1]
                    
                    kolumny = [k for k in df.columns if k != 'sheet_row']
                    wiersz_lista = [nowy_wiersz_z_id.get(k, "") for k in kolumny]
                    
                    db.append_data("DB_Eventy", wiersz_lista)
                    
                    st.success("🎉 Zlecenie zapisane w bazie chmurowej (Bezpieczny zapis)!")
                    st.rerun()

    with tab_archiwum:
        st.markdown("<h3 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif;'>Archiwum Historyczne (Cold Storage)</h3>", unsafe_allow_html=True)
        st.info("🗄️ Zakończone zlecenia są wyizolowane do osobnej zakładki w chmurze, aby nie spowalniać pracy systemu. Załaduj je tylko w razie potrzeby.")
        
        if "arch_loaded_eventy" not in st.session_state:
            st.session_state["arch_loaded_eventy"] = False

        if not st.session_state["arch_loaded_eventy"]:
            if st.button("📥 Połącz i wczytaj bazę archiwalną", use_container_width=True):
                st.session_state["arch_loaded_eventy"] = True
                st.rerun()
                
        if st.session_state["arch_loaded_eventy"]:
            if st.button("❌ Ukryj archiwum (Zwolnij pamięć)", use_container_width=True, type="secondary"):
                st.session_state["arch_loaded_eventy"] = False
                st.rerun()
                
            with st.spinner("Pobieranie ciężkich danych archiwalnych z Google Sheets..."):
                df_arch = db.fetch_data("DB_Eventy ARCHIWUM")
            
            if not df_arch.empty:
                st.dataframe(df_arch, use_container_width=True, hide_index=True)
            else:
                st.warning("Archiwum jest puste lub zakładka 'DB_Eventy ARCHIWUM' jeszcze nie powstała (zrobi się sama przy pierwszej archiwizacji).")
