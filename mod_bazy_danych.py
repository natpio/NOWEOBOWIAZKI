import streamlit as st
import pandas as pd
import db

def render(sh):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Słowniki i Bazy Danych</h1>
            <div class="module-subtitle">マスターデータ ✦ MASTER DATA</div>
        </div>
    ''', unsafe_allow_html=True)

    # Główne zakładki nawigacyjne modułu
    tab_miejsca, tab_przewoznicy = st.tabs(["🏢 Baza Lokalizacji (Miejsca)", "🚚 Flota (Przewoźnicy)"])

    # ==========================================
    # SEKCJA 1: MIEJSCA (LOKALIZACJE)
    # ==========================================
    with tab_miejsca:
        df_miejsca = db.fetch_data("Miejsca")
        sub1, sub2, sub3 = st.tabs(["📋 Przeglądaj", "➕ Dodaj Nową", "🛠️ Edytuj / Usuń"])
        
        with sub1:
            st.markdown("<p style='color: #C5A880; font-size: 12px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;'>⚡ Wyszukaj Lokalizację:</p>", unsafe_allow_html=True)
            wyszukiwana_fraza = st.text_input("Szukaj miejsca", placeholder="np. Berlin, SQM, ulica...", label_visibility="collapsed", key="search_loc")
            
            if not df_miejsca.empty:
                if wyszukiwana_fraza:
                    maska = df_miejsca.astype(str).apply(lambda row: row.str.contains(wyszukiwana_fraza, case=False, na=False).any(), axis=1)
                    df_filtrowane = df_miejsca[maska]
                    st.dataframe(df_filtrowane, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(df_miejsca, use_container_width=True, hide_index=True)
            else:
                st.info("Baza miejsc jest pusta.")
        
        with sub2:
            with st.form("add_location_v3", clear_on_submit=True):
                st.markdown("<h4 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif;'>Nowa lokalizacja w słowniku</h4>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                nazwa_skrocona = c1.text_input("Nazwa krótka (do listy wyboru) *")
                pelna_firma = c2.text_input("Pełna nazwa firmy / Magazynu")
                
                d1, d2, d3, d4 = st.columns([2, 1, 1.5, 1.5])
                ulica = d1.text_input("Ulica i numer")
                kod_pocztowy = d2.text_input("Kod pocztowy")
                miasto = d3.text_input("Miasto")
                kraj = d4.text_input("Kraj", value="Polska")
                
                o1, o2 = st.columns([3, 1])
                osoba_tel = o1.text_input("Osoba kontaktowa / Numer telefonu")
                rampa = o2.selectbox("Rampa załadunkowa:", ["TAK", "NIE", "BRAK DANYCH"])
                
                if st.form_submit_button("💾 Zapisz do słownika", type="primary"):
                    if nazwa_skrocona:
                        nowy_wiersz = [nazwa_skrocona, pelna_firma, ulica, kod_pocztowy, miasto, kraj, osoba_tel, rampa]
                        if db.append_data("Miejsca", nowy_wiersz):
                            st.success(f"Pomyślnie dodano lokalizację: {nazwa_skrocona}")
                            st.rerun()
                    else:
                        st.error("Wymagane jest podanie Nazwy Krótkiej!")
                        
        with sub3:
            if not df_miejsca.empty and 'Nazwa do listy' in df_miejsca.columns:
                lista_miejsc = df_miejsca['Nazwa do listy'].dropna().tolist()
                wybrane = st.selectbox("Wybierz lokalizację do modyfikacji:", ["Wybierz..."] + lista_miejsc)
                
                if wybrane != "Wybierz...":
                    idx_pd = df_miejsca[df_miejsca['Nazwa do listy'] == wybrane].index[0]
                    row_to_edit = df_miejsca.iloc[idx_pd]
                    gs_row_index = int(idx_pd) + 2
                    
                    with st.form("edit_location_form"):
                        st.markdown(f"<p style='color: #C5A880; font-size: 14px;'>Tryb edycji rekordu: <b style='color: #E2DCD3;'>{wybrane}</b></p>", unsafe_allow_html=True)
                        e1, e2 = st.columns(2)
                        n_skrocona = e1.text_input("Nazwa krótka", value=str(row_to_edit.get('Nazwa do listy', '')))
                        n_pelna = e2.text_input("Pełna nazwa", value=str(row_to_edit.get('Nazwa pełna / Firma', '')))
                        
                        e3, e4, e5, e6 = st.columns([2, 1, 1.5, 1.5])
                        n_ulica = e3.text_input("Ulica", value=str(row_to_edit.get('Ulica i numer', '')))
                        n_kod = e4.text_input("Kod pocztowy", value=str(row_to_edit.get('Kod pocztowy', '')))
                        n_miasto = e5.text_input("Miasto", value=str(row_to_edit.get('Miasto', '')))
                        n_kraj = e6.text_input("Kraj", value=str(row_to_edit.get('Kraj', 'Polska')))
                        
                        e7, e8 = st.columns([3, 1])
                        n_kontakt = e7.text_input("Osoba / Tel", value=str(row_to_edit.get('Osoba / Tel', '')))
                        obecna_rampa = str(row_to_edit.get('Rampa (TAK/NIE)', 'BRAK DANYCH'))
                        opcje_rampa = ["TAK", "NIE", "BRAK DANYCH"]
                        n_rampa = e8.selectbox("Rampa:", opcje_rampa, index=opcje_rampa.index(obecna_rampa) if obecna_rampa in opcje_rampa else 2)
                        
                        col_save, col_del = st.columns([3, 1])
                        if col_save.form_submit_button("💾 ZAPISZ ZMIANY", type="primary"):
                            nowe_dane = [n_skrocona, n_pelna, n_ulica, n_kod, n_miasto, n_kraj, n_kontakt, n_rampa]
                            if db.update_row("Miejsca", gs_row_index, nowe_dane):
                                st.success("Pomyślnie zaktualizowano lokalizację!")
                                st.rerun()
                        if col_del.form_submit_button("🗑️ USUŃ TRWALE", type="secondary"):
                            if db.delete_row("Miejsca", gs_row_index):
                                st.error("Lokalizacja została trwale usunięta.")
                                st.rerun()
                                
    # ==========================================
    # SEKCJA 2: PRZEWOŹNICY (FLOTA)
    # ==========================================
    with tab_przewoznicy:
        df_przewoznicy = db.fetch_data("Zleceniobiorcy")
        psub1, psub2, psub3 = st.tabs(["📋 Przeglądaj", "➕ Dodaj Nowego", "🛠️ Edytuj / Usuń"])
        
        with psub1:
            st.markdown("<p style='color: #C5A880; font-size: 12px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;'>⚡ Wyszukaj Przewoźnika:</p>", unsafe_allow_html=True)
            wyszukiwana_fraza_p = st.text_input("Szukaj przewoźnika", placeholder="np. Trans, Marcin, Poznań...", label_visibility="collapsed", key="search_carr")
            if not df_przewoznicy.empty:
                if wyszukiwana_fraza_p:
                    maska_p = df_przewoznicy.astype(str).apply(lambda row: row.str.contains(wyszukiwana_fraza_p, case=False, na=False).any(), axis=1)
                    st.dataframe(df_przewoznicy[maska_p], use_container_width=True, hide_index=True)
                else:
                    st.dataframe(df_przewoznicy, use_container_width=True, hide_index=True)
            else:
                st.info("Baza przewoźników jest pusta.")
                
        with psub2:
            with st.form("add_carrier_v3", clear_on_submit=True):
                st.markdown("<h4 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif;'>Nowy podwykonawca / Przewoźnik</h4>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                skrot = c1.text_input("Nazwa krótka (Skrót) *")
                pelna = c2.text_input("Pełna nazwa firmy *")
                
                c3, c4, c5 = st.columns([2, 2, 1])
                ulica = c3.text_input("Ulica i numer")
                miasto = c4.text_input("Kod i Miasto")
                kraj = c5.text_input("Kraj", value="Polska")
                
                c6, c7 = st.columns(2)
                nip = c6.text_input("NIP")
                pojazd = c7.text_input("Domyślny pojazd / Kierowca")
                
                if st.form_submit_button("💾 Zapisz w bazie", type="primary"):
                    if skrot and pelna:
                        if db.append_data("Zleceniobiorcy", [skrot, pelna, ulica, miasto, kraj, nip, pojazd]):
                            st.success("Pomyślnie dodano przewoźnika!")
                            st.rerun()
                    else:
                        st.error("Pola oznaczone gwiazdką (*) są wymagane.")
                        
        with psub3:
            if not df_przewoznicy.empty and 'Skrócona Nazwa' in df_przewoznicy.columns:
                lista_firm = df_przewoznicy['Skrócona Nazwa'].dropna().tolist()
                wybrany = st.selectbox("Wybierz firmę do modyfikacji:", ["Wybierz..."] + lista_firm)
                
                if wybrany != "Wybierz...":
                    idx_pd = df_przewoznicy[df_przewoznicy['Skrócona Nazwa'] == wybrany].index[0]
                    row_to_edit = df_przewoznicy.iloc[idx_pd]
                    gs_row_index = int(idx_pd) + 2
                    
                    with st.form("edit_carrier_form"):
                        st.markdown(f"<p style='color: #C5A880; font-size: 14px;'>Tryb edycji rekordu: <b style='color: #E2DCD3;'>{wybrany}</b></p>", unsafe_allow_html=True)
                        e1, e2 = st.columns(2)
                        n_skrot = e1.text_input("Skrót", value=str(row_to_edit.get('Skrócona Nazwa', '')))
                        n_pelna = e2.text_input("Pełna nazwa", value=str(row_to_edit.get('Pełna Nazwa', '')))
                        
                        e3, e4, e5 = st.columns([2, 2, 1])
                        n_ulica = e3.text_input("Ulica", value=str(row_to_edit.get('Ulica i numer', '')))
                        n_miasto = e4.text_input("Miasto", value=str(row_to_edit.get('Kod pocztowy i Miasto', '')))
                        n_kraj = e5.text_input("Kraj", value=str(row_to_edit.get('Kraj', 'Polska')))
                        
                        e6, e7 = st.columns(2)
                        n_nip = e6.text_input("NIP", value=str(row_to_edit.get('NIP', '')))
                        n_pojazd = e7.text_input("Pojazd", value=str(row_to_edit.get('Pojazd / Kierowca', '')))
                        
                        col_save, col_del = st.columns([3, 1])
                        if col_save.form_submit_button("💾 ZAPISZ ZMIANY", type="primary"):
                            nowe_dane = [n_skrot, n_pelna, n_ulica, n_miasto, n_kraj, n_nip, n_pojazd]
                            if db.update_row("Zleceniobiorcy", gs_row_index, nowe_dane):
                                st.success("Pomyślnie zaktualizowano dane przewoźnika!")
                                st.rerun()
                        if col_del.form_submit_button("🗑️ USUŃ TRWALE", type="secondary"):
                            if db.delete_row("Zleceniobiorcy", gs_row_index):
                                st.error("Przewoźnik został trwale usunięty.")
                                st.rerun()
