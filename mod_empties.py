import streamlit as st
import pandas as pd
import datetime
import db
from db import load_data

def render(sh):
    # --- DEDYKOWANY CSS DLA EFEKTU "ADVANCED TOWER" (Makieta) ---
    st.markdown("""
        <style>
        /* Stylizacja cienkiego paska przycisków akcji pod kartą */
        div[data-testid="stHorizontalBlock"] button {
            background-color: rgba(30, 35, 45, 0.9) !important;
            border: 1px solid rgba(255,255,255,0.05) !important;
            border-radius: 4px !important;
            padding: 2px 0px !important;
            min-height: 28px !important;
        }
        div[data-testid="stHorizontalBlock"] button:hover {
            background-color: rgba(60, 65, 75, 1) !important;
            border-color: #C5A880 !important;
        }
        /* Mroczne tła popoverów */
        div[data-testid="stPopoverBody"] {
            background-color: rgba(20, 25, 30, 0.95) !important;
            border: 1px solid rgba(197, 168, 128, 0.3) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- NAGŁÓWEK ---
    st.markdown("""
        <div style="margin-bottom: 25px;">
            <h1 style="font-family: 'Playball', cursive; font-size: 56px; color: #E2DCD3; margin: 0; line-height: 1; text-shadow: 2px 2px 10px rgba(0,0,0,0.8);">Zarządzanie Empties</h1>
            <div style="color: #C5A880; font-size: 11px; letter-spacing: 4px; font-weight: 700; font-family: 'Inter', sans-serif; text-transform: uppercase;">ザーノーズ ✦ ADVANCED TRACKING TOWER</div>
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
    # Kolory zgrane z makietą (Niebieski, Ciemny Róż, Zielony, Pomarańczowy, Fioletowy, Czerwony, Szmaragdowy)
    kolory_statusow = ["#3B82F6", "#9D174D", "#10B981", "#D97706", "#7C3AED", "#DC2626", "#059669"]

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
                
            # --- GÓRNY PASEK (WYBÓR + RADARY KPI) ---
            c_filtr, c_kpi1, c_kpi2, c_kpi3 = st.columns([1.5, 1, 1, 1], gap="small")
            
            with c_filtr:
                wybrany_event = st.selectbox("Wybierz Imprezę Targową:", lista_eventow, 
                                             index=lista_eventow.index(st.session_state.filtr_event_empties) if st.session_state.filtr_event_empties in lista_eventow else 0,
                                             label_visibility="collapsed")
                st.session_state.filtr_event_empties = wybrany_event
            
            df_event = df[df["Nazwa_Eventu"] == wybrany_event].copy()
            
            # Zliczanie do radarów
            l_bufor = len(df_event[df_event["Status"].str.contains("2. ")])
            l_hali = len(df_event[df_event["Status"].str.contains("1. |4. ")])
            l_suma = len(df_event)
            
            c_kpi1.markdown(f"""<div style="background: rgba(30, 35, 45, 0.8); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 6px 12px; display: flex; align-items: center; justify-content: space-between;"><div style="color: #D97706; font-size: 22px;">🗄️</div><div style="text-align: right;"><div style="color: #94A3B8; font-size: 9px; font-weight: bold; letter-spacing: 1px;">W MAGAZYNIE (BUFOR)</div><div style="color: #E2DCD3; font-size: 20px; font-weight: bold; line-height: 1;">{l_bufor}</div></div></div>""", unsafe_allow_html=True)
            c_kpi2.markdown(f"""<div style="background: rgba(30, 35, 45, 0.8); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 6px 12px; display: flex; align-items: center; justify-content: space-between;"><div style="color: #E11D48; font-size: 22px;">📦</div><div style="text-align: right;"><div style="color: #94A3B8; font-size: 9px; font-weight: bold; letter-spacing: 1px;">PUSTE NA HALI</div><div style="color: #E2DCD3; font-size: 20px; font-weight: bold; line-height: 1;">{l_hali}</div></div></div>""", unsafe_allow_html=True)
            c_kpi3.markdown(f"""<div style="background: rgba(30, 35, 45, 0.8); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 6px 12px; display: flex; align-items: center; justify-content: space-between;"><div style="color: #10B981; font-size: 22px;">📊</div><div style="text-align: right;"><div style="color: #94A3B8; font-size: 9px; font-weight: bold; letter-spacing: 1px;">DANE PODSUMOWANIA</div><div style="color: #E2DCD3; font-size: 20px; font-weight: bold; line-height: 1;">{l_suma}</div></div></div>""", unsafe_allow_html=True)
            
            st.markdown("<hr style='border-color: rgba(197, 168, 128, 0.15); margin: 15px 0 20px 0;'>", unsafe_allow_html=True)
            
            # --- UKŁAD KANBAN (3 KOLUMNY) ---
            kol_1, kol_2, kol_3 = st.columns(3, gap="medium")
            
            def render_status_panel(df_subset, status_indices, container):
                with container:
                    for idx in status_indices:
                        s_name = statusy[idx]
                        s_color = kolory_statusow[idx]
                        df_s = df_subset[df_subset["Status"] == s_name]
                        
                        # Elegancki nagłówek panelu
                        st.markdown(f"""
                        <div style="background: linear-gradient(90deg, rgba(20,25,35,0.9) 0%, rgba(20,25,35,0.4) 100%); border: 1px solid rgba(255,255,255,0.03); border-left: 4px solid {s_color}; border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #E2DCD3; font-size: 13px; font-weight: 600;">{s_name[3:]}</span>
                            <span style="background: rgba(0,0,0,0.6); color: {s_color}; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; border: 1px solid {s_color}40;">{len(df_s)}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if df_s.empty:
                            st.markdown("""<div style="text-align: center; background: rgba(0,0,0,0.2); padding: 15px; border-radius: 6px; border: 1px dashed rgba(255,255,255,0.1); color: #6B7280; font-size: 11px; margin-bottom: 15px;">Brak projektów na tym etapie</div>""", unsafe_allow_html=True)
                        else:
                            for _, row in df_s.iterrows():
                                proj_id = row['ID_Empties']
                                gs_row = int(row['sheet_row'])
                                
                                # Stylizowane body karty (bez przycisków)
                                st.markdown(f"""
                                <div style="background: rgba(30, 35, 45, 0.85); border: 1px solid rgba(255,255,255,0.05); border-top: 2px solid {s_color}; border-radius: 6px 6px 0 0; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                                        <div style="color: #60A5FA; font-size: 16px; font-weight: 800; letter-spacing: 1px;">{row.get('Numery_Projektow', '-')}</div>
                                        <div style="background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 4px; font-size: 9px; color: #A39B8F; border: 1px solid rgba(255,255,255,0.05);">📅 {row.get('Data_Akcji', '-')}</div>
                                    </div>
                                    <div style="color: #E2DCD3; font-size: 11px; margin-bottom: 4px;">📍 {row.get('Lokalizacja_Aktualna', 'Brak lokalizacji')}</div>
                                    <div style="color: #8C8477; font-size: 11px; margin-bottom: 2px;">🚚 {row.get('Auto_Kierowca', '-')}</div>
                                    <div style="color: #94A3B8; font-size: 10px; font-style: italic;">{row.get('Notatki', '')}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # --- PANEL AKCJI NA KARCIE ---
                                b_prev, b_edit, b_del, b_next = st.columns([1, 1, 1, 1], gap="small")
                                
                                with b_prev:
                                    if idx > 0:
                                        if st.button("⬅️", key=f"p_{proj_id}", help="Cofnij etap", use_container_width=True):
                                            db.update_single_row_safe("DB_Empties", gs_row, pd.Series([
                                                proj_id, row['Nazwa_Eventu'], row['Numery_Projektow'], statusy[idx - 1], 
                                                row['Lokalizacja_Aktualna'], row['Auto_Kierowca'], row['Data_Akcji'], row['Notatki']
                                            ]))
                                            st.cache_data.clear(); st.rerun()
                                            
                                with b_edit:
                                    with st.popover("✏️", use_container_width=True):
                                        st.markdown(f"**Edycja: {row['Numery_Projektow']}**")
                                        e_loc = st.text_input("📍 Lokalizacja:", value=row['Lokalizacja_Aktualna'], key=f"el_{proj_id}")
                                        e_auto = st.text_input("🚚 Auto:", value=row['Auto_Kierowca'], key=f"ea_{proj_id}")
                                        try: parsed_date = datetime.datetime.strptime(row['Data_Akcji'], "%Y-%m-%d").date()
                                        except: parsed_date = datetime.datetime.now().date()
                                        e_date = st.date_input("📅 Data:", value=parsed_date, key=f"ed_{proj_id}")
                                        e_not = st.text_area("📝 Notatki:", value=row['Notatki'], key=f"en_{proj_id}")
                                        
                                        if st.button("💾 Zapisz", key=f"sv_{proj_id}", type="primary", use_container_width=True):
                                            db.update_single_row_safe("DB_Empties", gs_row, pd.Series([
                                                proj_id, row['Nazwa_Eventu'], row['Numery_Projektow'], statusy[idx], 
                                                e_loc, e_auto, str(e_date), e_not
                                            ]))
                                            st.cache_data.clear(); st.rerun()
                                            
                                with b_del:
                                    with st.popover("🗑️", use_container_width=True):
                                        st.error("Na pewno usunąć?")
                                        if st.button("Tak, Usuń", key=f"dl_{proj_id}", type="primary", use_container_width=True):
                                            db.delete_row("DB_Empties", gs_row)
                                            st.cache_data.clear(); st.rerun()
                                            
                                with b_next:
                                    if idx < len(statusy) - 1:
                                        if st.button("➡️", key=f"n_{proj_id}", help="Następny etap", use_container_width=True):
                                            db.update_single_row_safe("DB_Empties", gs_row, pd.Series([
                                                proj_id, row['Nazwa_Eventu'], row['Numery_Projektow'], statusy[idx + 1], 
                                                row['Lokalizacja_Aktualna'], row['Auto_Kierowca'], row['Data_Akcji'], row['Notatki']
                                            ]))
                                            st.cache_data.clear(); st.rerun()
                                            
                                # Margines między kartami
                                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            # --- RYSOWANIE STATUSÓW DO ODPOWIEDNICH KOLUMN (Zgodnie z Twoją makietą) ---
            # Kolumna 1: Statusy 0, 1, 2
            render_status_panel(df_event, [0, 1, 2], kol_1)
            # Kolumna 2: Statusy 3, 4
            render_status_panel(df_event, [3, 4], kol_2)
            # Kolumna 3: Statusy 5, 6
            render_status_panel(df_event, [5, 6], kol_3)

    # ==========================================
    # ZAKŁADKA 2: DODAJ NOWE PROJEKTY (START)
    # ==========================================
    with tab_formularz:
        with st.form("form_add_empties", clear_on_submit=True):
            st.markdown("<h4 style='color: #C5A880; font-family: \"Shippori Mincho\", serif;'>Zgłoś zrzut sprzętu na targach (Rozbicie koszyka)</h4>", unsafe_allow_html=True)
            
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
