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
    
    st.markdown("<p style='color: #8C8477; font-size: 13px; margin-bottom: 25px;'>Wizualna tablica (Kanban) do śledzenia pustych skrzyń na targach. Kliknij przycisk na karcie, aby szybko przenieść skrzynie do kolejnego etapu.</p>", unsafe_allow_html=True)

    # --- INICJALIZACJA BAZY ---
    worksheet, df = load_data(sh, "DB_Empties")
    
    if df.empty and not worksheet.row_values(1):
        headers = ["ID_Empties", "Nazwa_Eventu", "Numery_Projektow", "Status", 
                   "Lokalizacja_Aktualna", "Auto_Kierowca", "Data_Akcji", "Notatki"]
        worksheet.append_row(headers)
        st.cache_data.clear()
        worksheet, df = load_data(sh, "DB_Empties")

    # --- DEFINICJA STATUSÓW ---
    statusy = [
        "1. 🔴 Puste do odebrania (Hala)",
        "2. 🟢 Puste zmagazynowane",
        "3. ⚠️ Do dostarczenia (Demontaż)",
        "4. 📦 Puste dostarczone (Pakowanie)",
        "5. 🚨 Pełne gotowe do zabrania",
        "6. ✅ Pełne zabrane (W drodze)"
    ]

    tab_kanban, tab_formularz = st.tabs(["🛹 Tablica Live (Kanban)", "➕ Dodaj / Zarządzaj Rejestrem"])

    # ==========================================
    # ZAKŁADKA 1: TABLICA KANBAN
    # ==========================================
    with tab_kanban:
        if df.empty:
            st.info("Brak wpisów w bazie Empties. Przejdź do zakładki obok, aby dodać pierwsze skrzynie do śledzenia.")
        else:
            # Filtr po evencie
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
            kol_1, kol_2, kol_3 = st.columns(3, gap="large")
            
            # Helper do rysowania kafelków
            def draw_kanban_cards(df_subset, status_index, column_container):
                status_name = statusy[status_index]
                next_status_name = statusy[status_index + 1] if status_index + 1 < len(statusy) else None
                
                with column_container:
                    st.markdown(f"<div style='background-color: rgba(10, 25, 47, 0.6); padding: 8px; border-radius: 6px; border-bottom: 2px solid #C5A880; margin-bottom: 15px; text-align: center; font-weight: bold; color: #E2DCD3; font-size: 13px;'>{status_name}</div>", unsafe_allow_html=True)
                    
                    df_status = df_subset[df_subset["Status"] == status_name]
                    
                    if df_status.empty:
                        st.markdown("<div style='text-align: center; color: #8C8477; font-size: 11px; padding: 20px 0; border: 1px dashed rgba(197, 168, 128, 0.2); border-radius: 6px;'>Brak skrzyń na tym etapie</div>", unsafe_allow_html=True)
                    else:
                        for idx, row in df_status.iterrows():
                            # Stylizacja kafelka
                            card_html = f"""
                            <div style="background-color: #F7F3EC; border: 1px solid #C5A880; border-left: 5px solid #BA4949; padding: 12px; border-radius: 6px; margin-bottom: 10px; box-shadow: 2px 2px 8px rgba(0,0,0,0.2);">
                                <div style="color: #0A192F; font-size: 11px; font-weight: bold; margin-bottom: 4px;">{row.get('Numery_Projektow', '-')}</div>
                                <div style="color: #990000; font-size: 14px; font-weight: 800; font-family: 'Bebas Neue', sans-serif; letter-spacing: 1px; margin-bottom: 8px;">{row.get('Lokalizacja_Aktualna', 'Brak lokalizacji')}</div>
                                <div style="color: #1A2530; font-size: 11px;"><b>Auto:</b> {row.get('Auto_Kierowca', '-')}</div>
                                <div style="color: #1A2530; font-size: 11px; margin-bottom: 8px;"><b>Data:</b> {row.get('Data_Akcji', '-')}</div>
                                <div style="color: #4A5568; font-size: 10px; font-style: italic;">{row.get('Notatki', '')}</div>
                            </div>
                            """
                            st.markdown(card_html.replace('\n', ''), unsafe_allow_html=True)
                            
                            # Przycisk przepinania statusu
                            if next_status_name:
                                if st.button(f"➔ Przesuń dalej", key=f"btn_next_{row['ID_Empties']}", use_container_width=True):
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
                            st.markdown("<br>", unsafe_allow_html=True)

            # Rozmieszczenie statusów w 3 kolumnach (po 2 statusy na kolumnę)
            # KOLUMNA 1: ODBIÓR Z HALI
            draw_kanban_cards(df_event, 0, kol_1)
            draw_kanban_cards(df_event, 1, kol_1)
            
            # KOLUMNA 2: DOSTAWA NA DEMONTAŻ
            draw_kanban_cards(df_event, 2, kol_2)
            draw_kanban_cards(df_event, 3, kol_2)
            
            # KOLUMNA 3: POWRÓT SPRZĘTU
            draw_kanban_cards(df_event, 4, kol_3)
            draw_kanban_cards(df_event, 5, kol_3)

    # ==========================================
    # ZAKŁADKA 2: DODAJ / EDYTUJ
    # ==========================================
    with tab_formularz:
        with st.form("form_add_empties", clear_on_submit=True):
            st.markdown("<h4 style='color: #C5A880; font-family: \"Shippori Mincho\", serif;'>Zgłoś koszyk Empties do nadzorowania</h4>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                nazwa_evt = st.text_input("Nazwa Imprezy Targowej *", placeholder="np. IFA Berlin 2026")
                projekty = st.text_input("Numery Projektów (po przecinku) *", placeholder="np. 12345, 12346, 12350")
                status_start = st.selectbox("Status Początkowy", statusy)
                
            with c2:
                lokalizacja = st.text_input("Gdzie fizycznie są/będą skrzynie?", placeholder="np. Magazyn Komorniki / Naczepa PO 12345")
                auto_kier = st.text_input("Przypisane Auto / Kierowca", placeholder="np. PO 12345 / Jan Kowalski")
                data_akcji = st.date_input("Data najbliższej akcji (Odbiór/Dostawa)")
                
            notatki = st.text_area("Dodatkowe instrukcje logistyczne")
            
            if st.form_submit_button("💾 Dodaj do tablicy Kanban", type="primary"):
                if not nazwa_evt or not projekty:
                    st.error("Uzupełnij nazwę targów i numery projektów!")
                else:
                    nowe_id = f"EMP-{datetime.datetime.now().strftime('%m%d%H%M')}"
                    nowy_wiersz = [
                        nowe_id, str(nazwa_evt), str(projekty), str(status_start), 
                        str(lokalizacja), str(auto_kier), str(data_akcji), str(notatki)
                    ]
                    if db.append_data("DB_Empties", nowy_wiersz):
                        st.success("✅ Pomyślnie dodano nowe opakowania na tablicę!")
                        st.rerun()

        if not df.empty:
            st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 25px 0;'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color: #E2DCD3;'>Edycja bezpośrednia (Tabela)</h4>", unsafe_allow_html=True)
            st.info("Zmień lokalizację, popraw błędy lub dodaj notatki bezpośrednio w komórkach, a następnie zapisz.")
            
            df_do_edycji = df.drop(columns=['sheet_row'], errors='ignore')
            edited_df = st.data_editor(df_do_edycji, use_container_width=True, hide_index=True)
            
            if st.button("💾 Zapisz zmiany w tabeli", type="primary"):
                worksheet.clear()
                df_str = edited_df.astype(str).replace('nan', '')
                worksheet.update(values=[df_str.columns.values.tolist()] + df_str.values.tolist(), range_name='A1')
                st.cache_data.clear()
                st.success("Tabela zaktualizowana!")
                st.rerun()
