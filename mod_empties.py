import streamlit as st
import pandas as pd
import datetime
import base64
import os
import db
from db import load_data

def render(sh):
    # --- ŁADOWANIE GRAFIK BASE64 DLA KLIMATU BASEBALLOWEGO ---
    b64_batter = ""
    if os.path.exists("batter.png"):
        with open("batter.png", "rb") as f:
            b64_batter = base64.b64encode(f.read()).decode()

    # --- DEDYKOWANY CSS DLA SCOREBOARDU ---
    st.markdown("""
        <style>
        /* Panel akcji pod kartą (Scoreboard Buttons) */
        .mlb-btn-group {
            display: flex; gap: 4px; margin-top: 10px; padding-top: 10px;
            border-top: 1px dashed rgba(255,255,255,0.1);
        }
        div[data-testid="stHorizontalBlock"] button {
            background-color: #12100E !important;
            border: 1px solid rgba(197, 168, 128, 0.3) !important;
            border-radius: 3px !important;
            padding: 2px 0px !important;
            min-height: 26px !important;
            color: #C5A880 !important;
            font-family: 'Bebas Neue', sans-serif !important;
            letter-spacing: 1px;
            transition: all 0.2s;
        }
        div[data-testid="stHorizontalBlock"] button:hover {
            background-color: #C5A880 !important;
            color: #050A15 !important;
            border-color: #FDFBF7 !important;
        }
        /* Mroczne tła popoverów edycji */
        div[data-testid="stPopoverBody"] {
            background-color: rgba(18, 16, 14, 0.95) !important;
            border: 2px solid #C5A880 !important;
            border-radius: 8px !important;
            box-shadow: 0px 10px 30px rgba(0,0,0,0.8) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- NAGŁÓWEK ---
    st.markdown("""
        <div style="margin-bottom: 25px; display: flex; align-items: center; gap: 20px;">
            <div>
                <h1 style="font-family: 'Playball', cursive; font-size: 58px; color: #EFE9DB; margin: 0; line-height: 1; text-shadow: 3px 3px 0px #BA4949, 6px 6px 15px rgba(0,0,0,0.6);">Empties Scoreboard</h1>
                <div style="color: #C5A880; font-size: 13px; letter-spacing: 4px; font-weight: 800; font-family: 'Bebas Neue', sans-serif; text-transform: uppercase;">MAJOR LEAGUE LOGISTICS ✦ ザーノーズ</div>
            </div>
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

    # --- STATUSY W STYLU DRUŻYN MLB ---
    statusy = [
        "0. 🚚 Dostarczone na targi (Pełne)",
        "1. 🔴 Puste do odebrania (Hala)",
        "2. 🟢 Puste zmagazynowane",
        "3. ⚠️ Do dostarczenia (Demontaż)",
        "4. 📦 Puste dostarczone (Pakowanie)",
        "5. 🚨 Pełne gotowe do zabrania",
        "6. ✅ Pełne zabrane (W drodze)"
    ]
    
    # Słownik stylów MLB (Kolory, gradienty, czcionki)
    mlb_styles = [
        # 0: NY Yankees (Granat, Biel, Pinstripes)
        {"bg": "linear-gradient(135deg, #0C2340 0%, #1D428A 100%)", "border": "#FFFFFF", "text": "#FFFFFF", "font": "'Bebas Neue', sans-serif", "accent": "#C4CED4"},
        # 1: Boston Red Sox (Karmazyn, Granat)
        {"bg": "linear-gradient(135deg, #BD3039 0%, #0C2340 100%)", "border": "#FFFFFF", "text": "#FFFFFF", "font": "'Bebas Neue', sans-serif", "accent": "#BD3039"},
        # 2: Oakland Athletics (Zieleń, Złoto)
        {"bg": "linear-gradient(135deg, #003831 0%, #115e45 100%)", "border": "#EFB21E", "text": "#FFFFFF", "font": "'Bebas Neue', sans-serif", "accent": "#EFB21E"},
        # 3: SF Giants (Czerń, Pomarańcz)
        {"bg": "linear-gradient(135deg, #27251F 0%, #111111 100%)", "border": "#FD5A1E", "text": "#FD5A1E", "font": "'Playball', cursive", "accent": "#FD5A1E"},
        # 4: LA Dodgers (Dodger Blue)
        {"bg": "linear-gradient(135deg, #005A9C 0%, #00447A 100%)", "border": "#FFFFFF", "text": "#FFFFFF", "font": "'Playball', cursive", "accent": "#005A9C"},
        # 5: Chicago Cubs (Niebieski, Czerwony)
        {"bg": "linear-gradient(135deg, #0E3386 0%, #0A225A 100%)", "border": "#CC3433", "text": "#FFFFFF", "font": "'Bebas Neue', sans-serif", "accent": "#CC3433"},
        # 6: White Sox (Czerń, Srebro)
        {"bg": "linear-gradient(135deg, #27251F 0%, #000000 100%)", "border": "#C4CED4", "text": "#FFFFFF", "font": "'Bebas Neue', sans-serif", "accent": "#C4CED4"}
    ]

    tab_kanban, tab_formularz = st.tabs(["🏟️ Płyta Główna (Live Scoreboard)", "🎟️ Kasa Biletowa (Rejestracja)"])

    # ==========================================
    # ZAKŁADKA 1: TABLICA LIVE
    # ==========================================
    with tab_kanban:
        if df.empty:
            st.info("Baza jest pusta. Rozpocznij od zarejestrowania zrzutu w zakładce obok.")
        else:
            lista_eventow = df["Nazwa_Eventu"].dropna().unique().tolist()
            if "filtr_event_empties" not in st.session_state:
                st.session_state.filtr_event_empties = lista_eventow[0] if lista_eventow else ""
                
            # --- GÓRNY PASEK: WYBÓR, WYSZUKIWARKA I RADARY ---
            c_filtr, c_search, c_kpi1, c_kpi2 = st.columns([1.5, 2, 1, 1], gap="small")
            
            with c_filtr:
                wybrany_event = st.selectbox("Wybierz Imprezę:", lista_eventow, 
                                             index=lista_eventow.index(st.session_state.filtr_event_empties) if st.session_state.filtr_event_empties in lista_eventow else 0,
                                             label_visibility="collapsed")
                st.session_state.filtr_event_empties = wybrany_event
            
            with c_search:
                search_query = st.text_input("🔍 Szukaj:", placeholder="Projekt, Auto, Miasto...", label_visibility="collapsed")

            df_event = df[df["Nazwa_Eventu"] == wybrany_event].copy()
            
            # Filtrowanie wyszukiwarką
            if search_query:
                mask = df_event.astype(str).apply(lambda row: row.str.contains(search_query, case=False, na=False).any(), axis=1)
                df_event = df_event[mask]
            
            # Statystyki z uwzględnieniem filtrowania
            l_bufor = len(df_event[df_event["Status"].str.contains("2. ")])
            l_gotowe = len(df_event[df_event["Status"].str.contains("5. ")])
            
            kpi_style = "background: rgba(18, 16, 14, 0.9); border: 2px solid #C5A880; border-radius: 4px; padding: 4px 10px; display: flex; align-items: center; justify-content: space-between;"
            c_kpi1.markdown(f"""<div style="{kpi_style}"><div style="color: #E2DCD3; font-size: 9px; font-family: 'Bebas Neue'; letter-spacing: 1px;">W BUFORZE</div><div style="color: #10B981; font-size: 22px; font-weight: bold; font-family: 'Bebas Neue'; line-height: 1;">{l_bufor}</div></div>""", unsafe_allow_html=True)
            c_kpi2.markdown(f"""<div style="{kpi_style}"><div style="color: #E2DCD3; font-size: 9px; font-family: 'Bebas Neue'; letter-spacing: 1px;">GOTOWE DO ODB.</div><div style="color: #DC2626; font-size: 22px; font-weight: bold; font-family: 'Bebas Neue'; line-height: 1;">{l_gotowe}</div></div>""", unsafe_allow_html=True)
            
            st.markdown("<hr style='border-color: #BA4949; margin: 15px 0 20px 0; border-style: dashed;'>", unsafe_allow_html=True)
            
            # --- UKŁAD MLB SCOREBOARD (3 KOLUMNY) ---
            kol_1, kol_2, kol_3 = st.columns(3, gap="large")
            
            def render_mlb_panel(df_subset, status_indices, container):
                with container:
                    for idx in status_indices:
                        s_name = statusy[idx]
                        s_style = mlb_styles[idx]
                        df_s = df_subset[df_subset["Status"] == s_name]
                        
                        # MLB Header z Watermarkiem pałkarza
                        bg_img = f"url('data:image/png;base64,{b64_batter}')" if b64_batter else "none"
                        
                        header_html = f"""
                        <div style="background: {s_style['bg']}; position: relative; overflow: hidden; border: 2px solid {s_style['border']}; border-radius: 8px; padding: 12px 15px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
                            <div style="position: absolute; right: -10px; top: -10px; opacity: 0.15; height: 150%; width: auto; background-image: {bg_img}; background-size: cover; background-repeat: no-repeat;"></div>
                            <span style="color: {s_style['text']}; font-family: {s_style['font']}; font-size: 22px; letter-spacing: 1.5px; position: relative; z-index: 2; text-shadow: 2px 2px 4px rgba(0,0,0,0.8);">{s_name[3:]}</span>
                            <span style="background: {s_style['border']}; color: #000000; padding: 2px 10px; border-radius: 20px; font-size: 16px; font-family: 'Bebas Neue', sans-serif; font-weight: bold; position: relative; z-index: 2; box-shadow: 2px 2px 0px rgba(0,0,0,0.5);">{len(df_s)}</span>
                        </div>
                        """
                        st.markdown(header_html.replace('\n', ''), unsafe_allow_html=True)
                        
                        if df_s.empty:
                            st.markdown(f"""<div style="text-align: center; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 6px; border: 1px dashed {s_style['border']}80; color: #8C8477; font-size: 12px; font-family: 'Bebas Neue'; letter-spacing: 1px; margin-bottom: 15px;">Pusto na boisku</div>""", unsafe_allow_html=True)
                        else:
                            for _, row in df_s.iterrows():
                                proj_id = row['ID_Empties']
                                gs_row = int(row['sheet_row'])
                                
                                # TRADING CARD STYLE
                                notatki_val = str(row.get('Notatki', '')).strip()
                                notatki_html = f"<div style='background: rgba(0,0,0,0.4); border-left: 2px solid {s_style['border']}; padding: 6px; font-size: 10px; color: #A39B8F; font-style: italic; margin-top: 8px;'>📝 {notatki_val}</div>" if notatki_val else ""
                                
                                card_html = f"""
                                <div style="background: #1C1A18; border: 1px solid rgba(197, 168, 128, 0.2); border-top: 4px solid {s_style['accent']}; border-radius: 6px; padding: 12px; margin-bottom: 5px; box-shadow: 0 4px 8px rgba(0,0,0,0.4); position: relative;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 6px; margin-bottom: 8px;">
                                        <div style="color: {s_style['accent']}; font-size: 20px; font-weight: 800; font-family: 'Bebas Neue', sans-serif; letter-spacing: 2px;">#{row.get('Numery_Projektow', '-')}</div>
                                        <div style="background: rgba(197, 168, 128, 0.15); padding: 2px 6px; border-radius: 3px; font-size: 10px; font-family: 'Bebas Neue', sans-serif; color: #FDFBF7; letter-spacing: 1px;">📅 {row.get('Data_Akcji', '-')}</div>
                                    </div>
                                    <div style="color: #E2DCD3; font-size: 12px; font-weight: 600; margin-bottom: 4px;">📍 {row.get('Lokalizacja_Aktualna', 'Brak lokalizacji')}</div>
                                    <div style="color: #C5A880; font-size: 11px; font-weight: bold;">🚚 {row.get('Auto_Kierowca', '-')}</div>
                                    {notatki_html}
                                </div>
                                """
                                st.markdown(card_html.replace('\n', ''), unsafe_allow_html=True)
                                
                                # --- SCOREBOARD BUTTONS ---
                                b_prev, b_edit, b_del, b_next = st.columns([1, 1, 1, 1], gap="small")
                                
                                with b_prev:
                                    if idx > 0:
                                        if st.button("⏪ UNDO", key=f"p_{proj_id}", help="Cofnij etap", use_container_width=True):
                                            db.update_single_row_safe("DB_Empties", gs_row, pd.Series([
                                                proj_id, row['Nazwa_Eventu'], row['Numery_Projektow'], statusy[idx - 1], 
                                                row['Lokalizacja_Aktualna'], row['Auto_Kierowca'], row['Data_Akcji'], row['Notatki']
                                            ]))
                                            st.cache_data.clear(); st.rerun()
                                            
                                with b_edit:
                                    with st.popover("⚙️ EDIT", use_container_width=True):
                                        st.markdown(f"<h4 style='color:#C5A880; font-family:\"Playball\"; margin:0;'>Korekta Projektu</h4>", unsafe_allow_html=True)
                                        e_loc = st.text_input("📍 Lokalizacja:", value=row['Lokalizacja_Aktualna'], key=f"el_{proj_id}")
                                        e_auto = st.text_input("🚚 Auto:", value=row['Auto_Kierowca'], key=f"ea_{proj_id}")
                                        try: parsed_date = datetime.datetime.strptime(row['Data_Akcji'], "%Y-%m-%d").date()
                                        except: parsed_date = datetime.datetime.now().date()
                                        e_date = st.date_input("📅 Data:", value=parsed_date, key=f"ed_{proj_id}")
                                        e_not = st.text_area("📝 Notatki:", value=row['Notatki'], key=f"en_{proj_id}")
                                        
                                        if st.button("💾 UPDATE", key=f"sv_{proj_id}", type="primary", use_container_width=True):
                                            db.update_single_row_safe("DB_Empties", gs_row, pd.Series([
                                                proj_id, row['Nazwa_Eventu'], row['Numery_Projektow'], statusy[idx], 
                                                e_loc, e_auto, str(e_date), e_not
                                            ]))
                                            st.cache_data.clear(); st.rerun()
                                            
                                with b_del:
                                    with st.popover("🗑️ DEL", use_container_width=True):
                                        st.error("Wymazać ten rekord z tablicy?")
                                        if st.button("POTWIERDŹ", key=f"dl_{proj_id}", type="primary", use_container_width=True):
                                            db.delete_row("DB_Empties", gs_row)
                                            st.cache_data.clear(); st.rerun()
                                            
                                with b_next:
                                    if idx < len(statusy) - 1:
                                        if st.button("NEXT ⏩", key=f"n_{proj_id}", help="Następna Baza", use_container_width=True):
                                            db.update_single_row_safe("DB_Empties", gs_row, pd.Series([
                                                proj_id, row['Nazwa_Eventu'], row['Numery_Projektow'], statusy[idx + 1], 
                                                row['Lokalizacja_Aktualna'], row['Auto_Kierowca'], row['Data_Akcji'], row['Notatki']
                                            ]))
                                            st.cache_data.clear(); st.rerun()
                                            
                                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            # Rysowanie paneli w kolumnach
            render_mlb_panel(df_event, [0, 1, 2], kol_1)
            render_mlb_panel(df_event, [3, 4], kol_2)
            render_mlb_panel(df_event, [5, 6], kol_3)

    # ==========================================
    # ZAKŁADKA 2: REJESTRACJA (KASA BILETOWA)
    # ==========================================
    with tab_formularz:
        with st.form("form_add_empties", clear_on_submit=True):
            st.markdown("<h3 style='color: #C5A880; font-family: \"Playball\", cursive;'>Otwarcie Zrzutu na Targach</h3>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                nazwa_evt = st.text_input("Nazwa Imprezy Targowej *", placeholder="np. IFA Berlin 2026")
                projekty = st.text_input("Numery Projektów (po przecinku) *", placeholder="np. 12345, 12346, 12350")
                status_start = st.selectbox("Wybierz Bazę Startową (Status)", statusy, index=0)
                
            with c2:
                lokalizacja = st.text_input("Lokalizacja Zrzutu (Hala/Stoisko)", placeholder="np. Hala 3.2, stoisko 100")
                auto_kier = st.text_input("Auto / Kierowca obsługujący zrzut", placeholder="np. PO 12345 / Jan Kowalski")
                data_akcji = st.date_input("Data Dostawy na Targi")
                
            notatki = st.text_area("Dodatkowe dyspozycje logistyczne")
            
            if st.form_submit_button("⚾ WPUŚĆ PROJEKTY NA BOISKO (Generuj Karty)", type="primary"):
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
                        
                        msg = f"✅ HOME RUN! Utworzono {len(nowe_wiersze)} kart projektów na tablicy!"
                        if pominete: msg += f" Pominięto duplikaty: {', '.join(pominete)}."
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(f"⚠️ Wszystkie podane projekty ({', '.join(pominete)}) już są na tablicy dla tej imprezy.")
