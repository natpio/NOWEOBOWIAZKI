import streamlit as st
import pandas as pd
import datetime
import db
from db import load_data

def render(sh):
    # --- NAGŁÓWEK ---
    st.markdown("""
        <div class="module-header-container">
            <h1 class="module-title">Zarządzanie Empties</h1>
            <div class="module-subtitle" style="color: #C5A880; letter-spacing: 3px;">エンプティーズ ✦ ADVANCED TRACKING TOWER</div>
        </div>
    """, unsafe_allow_html=True)

    # --- INICJALIZACJA BAZY ---
    worksheet, df = load_data(sh, "DB_Empties")
    
    if df.empty and len(df.columns) <= 1:
        headers = ["ID_Empties", "Nazwa_Eventu", "Numery_Projektow", "Status", 
                   "Lokalizacja_Aktualna", "Auto_Kierowca", "Data_Akcji", "Notatki"]
        fresh_ws = sh.worksheet("DB_Empties")
        fresh_ws.append_row(headers)
        st.cache_data.clear()
        worksheet, df = load_data(sh, "DB_Empties")

    # --- DEFINICJA STATUSÓW I KOLORÓW (NEON ZEN) ---
    statusy = [
        "0. 🚚 Dostarczone na targi (Pełne)",
        "1. 🔴 Puste do odebrania (Hala)",
        "2. 🟢 Puste zmagazynowane",
        "3. ⚠️ Do dostarczenia (Demontaż)",
        "4. 📦 Puste dostarczone (Pakowanie)",
        "5. 🚨 Pełne gotowe do zabrania",
        "6. ✅ Pełne zabrane (W drodze)"
    ]
    
    kolory_statusow = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#E11D48", "#059669"]

    tab_kanban, tab_formularz = st.tabs(["🚀 Tablica Operacyjna Live", "➕ Nowa Rejestracja (Start)"])

    # ==========================================
    # ZAKŁADKA 1: TABLICA KANBAN (PRO 999)
    # ==========================================
    with tab_kanban:
        if df.empty:
            st.info("Baza jest pusta. Rozpocznij od zarejestrowania zrzutu w zakładce obok.")
        else:
            lista_eventow = df["Nazwa_Eventu"].dropna().unique().tolist()
            if "filtr_event_empties" not in st.session_state:
                st.session_state.filtr_event_empties = lista_eventow[0] if lista_eventow else ""
                
            c_filtr, c_kpi1, c_kpi2, c_kpi3 = st.columns([1.5, 1, 1, 1])
            wybrany_event = c_filtr.selectbox("🎯 Wybierz Imprezę Targową:", lista_eventow, 
                                              index=lista_eventow.index(st.session_state.filtr_event_empties) if st.session_state.filtr_event_empties in lista_eventow else 0,
                                              label_visibility="collapsed")
            st.session_state.filtr_event_empties = wybrany_event
            
            df_event = df[df["Nazwa_Eventu"] == wybrany_event].copy()
            
            # --- RADAR TARGOWY (KPIs) ---
            l_zmagazynowane = len(df_event[df_event["Status"].str.contains("2. ")])
            l_na_hali = len(df_event[df_event["Status"].str.contains("4. |5. ")])
            l_zakonczone = len(df_event[df_event["Status"].str.contains("6. ")])
            
            c_kpi1.markdown(f"<div style='background: rgba(16, 185, 129, 0.1); border: 1px solid #10B981; border-radius: 6px; padding: 5px 10px; text-align: center;'><div style='color:#10B981; font-size:10px; font-weight:bold; text-transform:uppercase;'>W magazynie/buforze</div><div style='color:#E2DCD3; font-size:18px; font-weight:900;'>{l_zmagazynowane}</div></div>", unsafe_allow_html=True)
            c_kpi2.markdown(f"<div style='background: rgba(139, 92, 246, 0.1); border: 1px solid #8B5CF6; border-radius: 6px; padding: 5px 10px; text-align: center;'><div style='color:#8B5CF6; font-size:10px; font-weight:bold; text-transform:uppercase;'>Puste na stoisku</div><div style='color:#E2DCD3; font-size:18px; font-weight:900;'>{l_na_hali}</div></div>", unsafe_allow_html=True)
            c_kpi3.markdown(f"<div style='background: rgba(5, 150, 105, 0.1); border: 1px solid #059669; border-radius: 6px; padding: 5px 10px; text-align: center;'><div style='color:#059669; font-size:10px; font-weight:bold; text-transform:uppercase;'>Zamknięte (Powroty)</div><div style='color:#E2DCD3; font-size:18px; font-weight:900;'>{l_zakonczone}</div></div>", unsafe_allow_html=True)
            
            st.markdown("<hr style='border-color: rgba(197, 168, 128, 0.15); margin: 15px 0 20px 0;'>", unsafe_allow_html=True)
            
            # --- UKŁAD KANBAN (3 KOLUMNY STRUMIENIOWE) ---
            kol_1, kol_2, kol_3 = st.columns(3, gap="medium")
            
            def draw_kanban_cards(df_subset, status_index, column_container):
                status_name = statusy[status_index]
                b_color = kolory_statusow[status_index]
                
                with column_container:
                    df_status = df_subset[df_subset["Status"] == status_name]
                    liczba_elementow = len(df_status)
                    
                    # Nagłówek statusu z licznikiem
                    header_html = f"""
                    <div style='background: linear-gradient(90deg, rgba(10,25,47,0.8) 0%, rgba(10,25,47,0.2) 100%); border-left: 4px solid {b_color}; padding: 10px 15px; border-radius: 4px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;'>
                        <span style='color: #E2DCD3; font-weight: 700; font-size: 13px; letter-spacing: 0.5px;'>{status_name[3:]}</span>
                        <span style='background: rgba(0,0,0,0.6); color: {b_color}; font-weight: 800; font-size: 12px; padding: 2px 8px; border-radius: 12px; border: 1px solid {b_color}40;'>{liczba_elementow}</span>
                    </div>
                    """
                    st.markdown(header_html.replace('\n', ''), unsafe_allow_html=True)
                    
                    if df_status.empty:
                        st.markdown("<div style='text-align: center; color: #8C8477; font-size: 11px; padding: 15px 0; border: 1px dashed rgba(197, 168, 128, 0.15); border-radius: 6px;'>Brak projektów na tym etapie</div><br>", unsafe_allow_html=True)
                    else:
                        for idx, row in df_status.iterrows():
                            # Właściwości karty
                            proj_id = row['ID_Empties']
                            gs_row = int(row['sheet_row'])
                            notatki_val = str(row.get('Notatki', '')).strip()
                            
                            notatki_html = f"<div style='color: #A39B8F; font-size: 11px; font-style: italic; background: rgba(0,0,0,0.3); padding: 6px 10px; border-radius: 4px; margin-top: 8px; border-left: 2px solid #C5A880;'>📝 {notatki_val}</div>" if notatki_val else ""
                            
                            # Karta HTML (Design PRO)
                            card_html = f"""
                            <div style="background: rgba(20, 20, 25, 0.95); border: 1px solid rgba(197, 168, 128, 0.2); border-top: 3px solid {b_color}; padding: 15px; border-radius: 8px; margin-bottom: 5px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                    <div style="color: {b_color}; font-size: 18px; font-weight: 800; font-family: 'Bebas Neue', sans-serif; letter-spacing: 1.5px; text-shadow: 0 0 10px {b_color}40;">#{row.get('Numery_Projektow', '-')}</div>
                                    <div style="background: rgba(197, 168, 128, 0.1); border: 1px solid rgba(197, 168, 128, 0.3); padding: 3px 8px; border-radius: 4px; font-size: 10px; color: #C5A880; font-weight: 600;">📅 {row.get('Data_Akcji', '-')}</div>
                                </div>
                                <div style="color: #E2DCD3; font-size: 13px; font-weight: 600; margin-bottom: 6px; display: flex; align-items: center; gap: 5px;"><span>📍</span> {row.get('Lokalizacja_Aktualna', 'Brak lokalizacji')}</div>
                                <div style="color: #8C8477; font-size: 12px; margin-bottom: 4px; display: flex; align-items: center; gap: 5px;"><span>🚚</span> {row.get('Auto_Kierowca', '-')}</div>
                                {notatki_html}
                            </div>
                            """
                            st.markdown(card_html.replace('\n', ''), unsafe_allow_html=True)
                            
                            # PANEL OPERACYJNY (4 Przyciski zagnieżdżone w kolumnach pod kartą)
                            b_prev, b_edit, b_del, b_next = st.columns([1, 1, 1, 1])
                            
                            # 1. AKCJA: COFNIJ
                            with b_prev:
                                if status_index > 0:
                                    if st.button("⬅️", key=f"prev_{proj_id}", help="Cofnij do poprzedniego etapu", use_container_width=True):
                                        db.update_single_row_safe("DB_Empties", gs_row, pd.Series([
                                            proj_id, row['Nazwa_Eventu'], row['Numery_Projektow'], statusy[status_index - 1], 
                                            row['Lokalizacja_Aktualna'], row['Auto_Kierowca'], row['Data_Akcji'], row['Notatki']
                                        ]))
                                        st.cache_data.clear()
                                        st.rerun()

                            # 2. AKCJA: EDYCJA W LOCIE (Popover)
                            with b_edit:
                                with st.popover("✏️", use_container_width=True):
                                    st.markdown(f"**Edycja Projektu: {row['Numery_Projektow']}**")
                                    e_loc = st.text_input("📍 Zmień lokalizację:", value=row['Lokalizacja_Aktualna'], key=f"e_loc_{proj_id}")
                                    e_auto = st.text_input("🚚 Zmień Auto/Kierowcę:", value=row['Auto_Kierowca'], key=f"e_auto_{proj_id}")
                                    
                                    # Parsowanie daty do obiektu date
                                    try: parsed_date = datetime.datetime.strptime(row['Data_Akcji'], "%Y-%m-%d").date()
                                    except: parsed_date = datetime.datetime.now().date()
                                    e_date = st.date_input("📅 Aktualizuj Datę:", value=parsed_date, key=f"e_date_{proj_id}")
                                    
                                    e_notatki = st.text_area("📝 Dodaj Notatkę:", value=row['Notatki'], key=f"e_not_{proj_id}")
                                    
                                    if st.button("💾 Zapisz Zmiany", key=f"save_{proj_id}", type="primary", use_container_width=True):
                                        db.update_single_row_safe("DB_Empties", gs_row, pd.Series([
                                            proj_id, row['Nazwa_Eventu'], row['Numery_Projektow'], status_name, 
                                            e_loc, e_auto, str(e_date), e_notatki
                                        ]))
                                        st.cache_data.clear()
                                        st.rerun()

                            # 3. AKCJA: USUŃ (Popover z potwierdzeniem)
                            with b_del:
                                with st.popover("🗑️", use_container_width=True):
                                    st.error("Trwale usunąć ten projekt z tablicy?")
                                    if st.button("Tak, Usuń", key=f"del_{proj_id}", type="primary", use_container_width=True):
                                        db.delete_row("DB_Empties", gs_row)
                                        st.cache_data.clear()
                                        st.rerun()

                            # 4. AKCJA: DALEJ
                            with b_next:
                                if status_index < len(statusy) - 1:
                                    if st.button("➡️", key=f"next_{proj_id}", help="Przesuń do kolejnego etapu", use_container_width=True):
                                        db.update_single_row_safe("DB_Empties", gs_row, pd.Series([
                                            proj_id, row['Nazwa_Eventu'], row['Numery_Projektow'], statusy[status_index + 1], 
                                            row['Lokalizacja_Aktualna'], row['Auto_Kierowca'], row['Data_Akcji'], row['Notatki']
                                        ]))
                                        st.cache_data.clear()
                                        st.rerun()
                            
                            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

            # --- RYSOWANIE STATUSÓW ---
            # Kolumna 1: STRUMIEŃ INBOUND & ZMAGAZYNOWANIE
            draw_kanban_cards(df_event, 0, kol_1)
            draw_kanban_cards(df_event, 1, kol_1)
            draw_kanban_cards(df_event, 2, kol_1)
            
            # Kolumna 2: STRUMIEŃ PREP & OUTBOUND
            draw_kanban_cards(df_event, 3, kol_2)
            draw_kanban_cards(df_event, 4, kol_2)
            
            # Kolumna 3: STRUMIEŃ FINALIZACJI
            draw_kanban_cards(df_event, 5, kol_3)
            draw_kanban_cards(df_event, 6, kol_3)

    # ==========================================
    # ZAKŁADKA 2: DODAJ NOWE PROJEKTY (START)
    # ==========================================
    with tab_formularz:
        with st.form("form_add_empties", clear_on_submit=True):
            st.markdown("<h4 style='color: #C5A880; font-family: \"Shippori Mincho\", serif;'>Zgłoś zrzut sprzętu na targach (Start Procesu)</h4>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                nazwa_evt = st.text_input("Nazwa Imprezy Targowej *", placeholder="np. IFA Berlin 2026")
                projekty = st.text_input("Numery Projektów (po przecinku) *", placeholder="np. 12345, 12346, 12350")
                status_start = st.selectbox("Status Początkowy", statusy, index=0)
                
            with c2:
                lokalizacja = st.text_input("Lokalizacja Startowa (Hala/Stoisko)", placeholder="np. Hala 3.2, stoisko 100")
                auto_kier = st.text_input("Auto / Kierowca realizujący zrzut", placeholder="np. PO 12345 / Jan Kowalski")
                data_akcji = st.date_input("Data zrzutu (Dostawy)")
                
            notatki = st.text_area("Dodatkowe instrukcje (np. priorytet odbioru pustych)")
            
            if st.form_submit_button("💾 Wygeneruj karty dla podanych projektów", type="primary"):
                if not nazwa_evt or not projekty:
                    st.error("Uzupełnij nazwę targów i numery projektów!")
                else:
                    lista_projektow = [p.strip() for p in projekty.split(",") if p.strip()]
                    nowe_wiersze = []
                    pominete = []
                    
                    for i, proj in enumerate(lista_projektow):
                        czy_istnieje = False
                        if not df.empty:
                            duplikat = df[(df["Nazwa_Eventu"].astype(str).str.strip().str.lower() == nazwa_evt.strip().lower()) & 
                                          (df["Numery_Projektow"].astype(str).str.strip().str.lower() == proj.lower())]
                            if not duplikat.empty:
                                czy_istnieje = True
                        
                        if czy_istnieje:
                            pominete.append(proj)
                        else:
                            nowe_id = f"EMP-{proj}-{datetime.datetime.now().strftime('%m%d%H%M%S')}-{i}"
                            nowe_wiersze.append({
                                "ID_Empties": nowe_id,
                                "Nazwa_Eventu": str(nazwa_evt),
                                "Numery_Projektow": str(proj),
                                "Status": str(status_start),
                                "Lokalizacja_Aktualna": str(lokalizacja),
                                "Auto_Kierowca": str(auto_kier),
                                "Data_Akcji": str(data_akcji),
                                "Notatki": str(notatki)
                            })
                    
                    if nowe_wiersze:
                        df_temp = pd.concat([df, pd.DataFrame(nowe_wiersze)], ignore_index=True)
                        if 'sheet_row' in df_temp.columns:
                            df_temp = df_temp.drop(columns=['sheet_row'])
                        
                        fresh_ws = sh.worksheet("DB_Empties")
                        fresh_ws.clear()
                        df_str = df_temp.astype(str).replace('nan', '')
                        fresh_ws.update(values=[df_str.columns.values.tolist()] + df_str.values.tolist(), range_name='A1')
                        st.cache_data.clear()
                        
                        msg = f"✅ Pomyślnie utworzono {len(nowe_wiersze)} niezależnych kart projektów!"
                        if pominete: msg += f" Pominięto duplikaty: {', '.join(pominete)}."
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(f"⚠️ Wszystkie podane projekty ({', '.join(pominete)}) już istnieją na tablicy dla tej imprezy.")
