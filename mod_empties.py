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
            <div class="module-subtitle">エンプティーズ ✦ EMPTY CASES TRACKING</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<p style='color: #8C8477; font-size: 13px; margin-bottom: 25px;'>Zarządzaj przepływem opakowań targowych. System poprowadzi Cię od momentu dostarczenia sprzętu, przez magazynowanie pustych skrzyń, aż po ich powrót na bazę.</p>", unsafe_allow_html=True)

    # --- INICJALIZACJA BAZY ---
    worksheet, df = load_data(sh, "DB_Empties")
    
    # Zabezpieczenie przed utratą sesji HTTP w cache'u
    if df.empty and len(df.columns) <= 1:
        headers = ["ID_Empties", "Nazwa_Eventu", "Numery_Projektow", "Status", 
                   "Lokalizacja_Aktualna", "Auto_Kierowca", "Data_Akcji", "Notatki"]
        fresh_ws = sh.worksheet("DB_Empties")
        fresh_ws.append_row(headers)
        st.cache_data.clear()
        worksheet, df = load_data(sh, "DB_Empties")

    # --- DEFINICJA STATUSÓW I KOLORÓW ---
    statusy = [
        "0. 🚚 Dostarczone na targi (Pełne)",
        "1. 🔴 Puste do odebrania (Hala)",
        "2. 🟢 Puste zmagazynowane",
        "3. ⚠️ Do dostarczenia (Demontaż)",
        "4. 📦 Puste dostarczone (Pakowanie)",
        "5. 🚨 Pełne gotowe do zabrania",
        "6. ✅ Pełne zabrane (W drodze)"
    ]
    
    # Kolory przypisane do każdego statusu (wizualna kategoryzacja)
    kolory_statusow = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#BA4949", "#047857"]

    tab_kanban, tab_formularz = st.tabs(["🛹 Tablica Live (Kanban)", "➕ Dodaj / Zarządzaj Rejestrem"])

    # ==========================================
    # ZAKŁADKA 1: TABLICA KANBAN
    # ==========================================
    with tab_kanban:
        if df.empty:
            st.info("Brak wpisów w bazie Empties. Przejdź do zakładki obok, aby zgłosić pierwsze zrzuty sprzętu na targach.")
        else:
            lista_eventow = df["Nazwa_Eventu"].dropna().unique().tolist()
            if "filtr_event_empties" not in st.session_state:
                st.session_state.filtr_event_empties = lista_eventow[0] if lista_eventow else ""
                
            c_filtr, _ = st.columns([1, 2])
            wybrany_event = c_filtr.selectbox("🎯 Wybierz Imprezę Targową:", lista_eventow, 
                                              index=lista_eventow.index(st.session_state.filtr_event_empties) if st.session_state.filtr_event_empties in lista_eventow else 0)
            st.session_state.filtr_event_empties = wybrany_event
            
            df_event = df[df["Nazwa_Eventu"] == wybrany_event].copy()
            
            st.markdown("<hr style='border-color: rgba(197, 168, 128, 0.2); margin: 15px 0 25px 0;'>", unsafe_allow_html=True)
            
            # --- UKŁAD KANBAN (3 KOLUMNY) ---
            kol_1, kol_2, kol_3 = st.columns(3, gap="medium")
            
            def draw_kanban_cards(df_subset, status_index, column_container):
                status_name = statusy[status_index]
                b_color = kolory_statusow[status_index]
                next_status_name = statusy[status_index + 1] if status_index + 1 < len(statusy) else None
                
                with column_container:
                    df_status = df_subset[df_subset["Status"] == status_name]
                    liczba_elementow = len(df_status)
                    
                    # Nowy, czytelny nagłówek kolumny statusu
                    header_html = f"""
                    <div style='background: linear-gradient(90deg, rgba(10,25,47,0.8) 0%, rgba(10,25,47,0.3) 100%); border-left: 4px solid {b_color}; padding: 10px 15px; border-radius: 4px; margin-bottom: 15px; margin-top: 5px; display: flex; justify-content: space-between; align-items: center;'>
                        <span style='color: #E2DCD3; font-weight: 700; font-size: 13px; letter-spacing: 0.5px;'>{status_name[3:]}</span>
                        <span style='background: rgba(0,0,0,0.5); color: {b_color}; font-weight: 800; font-size: 12px; padding: 2px 8px; border-radius: 12px;'>{liczba_elementow}</span>
                    </div>
                    """
                    st.markdown(header_html.replace('\n', ''), unsafe_allow_html=True)
                    
                    if df_status.empty:
                        st.markdown("<div style='text-align: center; color: #8C8477; font-size: 11px; padding: 15px 0; border: 1px dashed rgba(197, 168, 128, 0.15); border-radius: 6px;'>Brak skrzyń</div>", unsafe_allow_html=True)
                    else:
                        for idx, row in df_status.iterrows():
                            notatki_val = row.get('Notatki', '')
                            notatki_html = f"<div style='color: #A39B8F; font-size: 11px; font-style: italic; background: rgba(0,0,0,0.2); padding: 5px 8px; border-radius: 4px; margin-bottom: 8px;'>📝 {notatki_val}</div>" if notatki_val else ""
                            
                            # Ciemny, elegancki styl kafelka (Zen)
                            card_html = f"""
                            <div style="background-color: rgba(28, 26, 24, 0.85); border: 1px solid rgba(197, 168, 128, 0.15); border-left: 4px solid {b_color}; padding: 15px; border-radius: 6px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                    <div style="color: #C5A880; font-size: 16px; font-weight: 800; font-family: 'Bebas Neue', sans-serif; letter-spacing: 1px;">PROJEKT: {row.get('Numery_Projektow', '-')}</div>
                                    <div style="background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 4px; font-size: 10px; color: #A39B8F;">📅 {row.get('Data_Akcji', '-')}</div>
                                </div>
                                <div style="color: #E2DCD3; font-size: 13px; font-weight: 600; margin-bottom: 6px;">📍 {row.get('Lokalizacja_Aktualna', 'Brak lokalizacji')}</div>
                                <div style="color: #8C8477; font-size: 11px; margin-bottom: 8px;">🚚 Auto/Kier: <span style="color:#A39B8F;">{row.get('Auto_Kierowca', '-')}</span></div>
                                {notatki_html}
                            </div>
                            """
                            st.markdown(card_html.replace('\n', ''), unsafe_allow_html=True)
                            
                            if next_status_name:
                                if st.button(f"➔ Dalej ({next_status_name[3:12]}...)", key=f"btn_next_{row['ID_Empties']}", use_container_width=True, type="secondary"):
                                    db.update_single_row_safe(
                                        "DB_Empties", 
                                        int(row['sheet_row']), 
                                        pd.Series([
                                            row['ID_Empties'], row['Nazwa_Eventu'], row['Numery_Projektow'], 
                                            next_status_name, row['Lokalizacja_Aktualna'], row['Auto_Kierowca'], 
                                            row['Data_Akcji'], row['Notatki']
                                        ])
                                    )
                                    st.cache_data.clear()
                                    st.rerun()
                            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)

            # Rozmieszczenie statusów (pojemność tablicy dopasowana do ilości etapów)
            draw_kanban_cards(df_event, 0, kol_1)
            draw_kanban_cards(df_event, 1, kol_1)
            
            draw_kanban_cards(df_event, 2, kol_2)
            draw_kanban_cards(df_event, 3, kol_2)
            
            draw_kanban_cards(df_event, 4, kol_3)
            draw_kanban_cards(df_event, 5, kol_3)
            draw_kanban_cards(df_event, 6, kol_3)

    # ==========================================
    # ZAKŁADKA 2: DODAJ / EDYTUJ
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
                lokalizacja = st.text_input("Lokalizacja (np. nr Hali/Stoiska)", placeholder="np. Hala 3.2, stoisko 100")
                auto_kier = st.text_input("Przypisane Auto / Kierowca", placeholder="np. PO 12345 / Jan Kowalski")
                data_akcji = st.date_input("Data zrzutu (Dostawy)")
                
            notatki = st.text_area("Dodatkowe instrukcje (np. priorytet odbioru pustych)")
            
            if st.form_submit_button("💾 Utwórz karty projektów", type="primary"):
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
                        
                        msg = f"✅ Pomyślnie utworzono {len(nowe_wiersze)} osobnych kart na tablicy!"
                        if pominete: msg += f" Pominięto duplikaty: {', '.join(pominete)}."
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(f"⚠️ Wszystkie podane projekty ({', '.join(pominete)}) już istnieją na tablicy dla tej imprezy.")

        if not df.empty:
            st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 25px 0;'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color: #E2DCD3;'>Edycja bezpośrednia (Tabela)</h4>", unsafe_allow_html=True)
            st.info("Zmień lokalizację, przypisane auto lub dodaj notatki bezpośrednio w komórkach, a następnie zapisz.")
            
            df_do_edycji = df.drop(columns=['sheet_row'], errors='ignore')
            edited_df = st.data_editor(df_do_edycji, use_container_width=True, hide_index=True)
            
            if st.button("💾 Zapisz zmiany w tabeli", type="primary"):
                fresh_ws = sh.worksheet("DB_Empties")
                fresh_ws.clear()
                df_str = edited_df.astype(str).replace('nan', '')
                fresh_ws.update(values=[df_str.columns.values.tolist()] + df_str.values.tolist(), range_name='A1')
                st.cache_data.clear()
                st.success("Tabela zaktualizowana!")
                st.rerun()
