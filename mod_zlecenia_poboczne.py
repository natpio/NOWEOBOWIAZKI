import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def parse_date(d_str):
    """
    Funkcja pomocnicza zamieniająca tekst z Google Sheets z powrotem na obiekt daty dla kalendarza.
    Obsługuje formaty YYYY-MM-DD oraz DD.MM.YYYY.
    """
    try:
        if "." in str(d_str):
            return datetime.strptime(str(d_str), "%d.%m.%Y").date()
        else:
            return datetime.strptime(str(d_str), "%Y-%m-%d").date()
    except:
        return datetime.today().date()

def render(sh):
    # Nagłówek w stylu Japandi
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Zlecenia Poboczne</h1>
            <div class="module-subtitle">サブオーダー ✦ SECONDARY ORDERS</div>
        </div>
    ''', unsafe_allow_html=True)

    # Nawigacja - Zakładki
    tab1, tab2, tab3 = st.tabs(["📂 Aktywne Zlecenia", "➕ Utwórz Nowe Zlecenie", "📦 Archiwum Historyczne"])

    # Pobieranie danych z Google Sheets
    try:
        worksheet = sh.worksheet("Zlecenia Poboczne")
        data = worksheet.get_all_values()
        
        # Jeśli arkusz jest całkowicie pusty, inicjujemy nowe, poszerzone nagłówki
        if not data:
            headers = ["Nr Zlecenia", "Przewoźnik", "Opis Ładunku / Trasy", "Data Załadunku", "Data Rozładunku", "Termin Dni", "Data Płatności", "Status", "CMR", "POD", "Faktura"]
            worksheet.append_row(headers)
            data = [headers]
            
        headers = data[0]
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=headers)
            df['sheet_row'] = df.index + 2
        else:
            df = pd.DataFrame(columns=headers)
            df['sheet_row'] = []
            
    except Exception as e:
        st.error(f"Błąd komunikacji z Google Sheets: {e}. Upewnij się, że zakładka 'Zlecenia Poboczne' istnieje.")
        return

    # ==========================================
    # KARTA 1: AKTYWNE ZLECENIA
    # ==========================================
    with tab1:
        st.markdown("<div style='font-size: 10px; color: #C5A880; font-weight: 700; letter-spacing: 1px; margin-bottom: 5px;'>⚡ WYSZUKAJ I FILTRUJ ZLECENIA:</div>", unsafe_allow_html=True)
        search_query = st.text_input("", placeholder="🔍 Wpisz nazwę przewoźnika, opis, numer...", label_visibility="collapsed")

        # Filtrowanie tylko aktywnych zleceń
        active_df = df[df['Status'] != 'ARCHIWUM'] if not df.empty else df

        # Obliczenia metryk dla kart KPI
        brak_cmr = len(active_df[(active_df.get("CMR") == "NIE")]) if not active_df.empty and "CMR" in active_df.columns else 0
        brak_pod = len(active_df[(active_df.get("POD") == "NIE")]) if not active_df.empty and "POD" in active_df.columns else 0
        brak_fv = len(active_df[(active_df.get("Faktura") == "NIE")]) if not active_df.empty and "Faktura" in active_df.columns else 0

        # KARTY KPI
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-icon-bg">📄</div>
                <div class="kpi-header">DO WYSTAWIENIA CMR</div>
                <div class="kpi-sub-jp">CMRの発行待ち</div>
                <div class="kpi-value">{brak_cmr}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-bg">📋</div>
                <div class="kpi-header">BRAKUJĄCE ZWROTY POD</div>
                <div class="kpi-sub-jp">POD受領待ち</div>
                <div class="kpi-value">{brak_pod}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon-bg">💰</div>
                <div class="kpi-header">NIEOPŁACONE FAKTURY</div>
                <div class="kpi-sub-jp">未払い請求書</div>
                <div class="kpi-value">{brak_fv}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if not active_df.empty:
            for index, row in active_df.iterrows():
                # Wyszukiwarka
                if search_query.lower() not in str(row.values).lower() and search_query != "":
                    continue

                tag_cmr = '<span class="tag-zen-orange">Brak CMR</span>' if row.get("CMR") == "NIE" else ('<span class="tag-zen-blue">CMR: Nie Dotyczy</span>' if row.get("CMR") == "NIE POTRZEBA" else '')
                tag_pod = '<span class="tag-zen-red">Brak POD</span>' if row.get("POD") == "NIE" else ''
                tag_fv = '<span class="tag-zen-orange">Brak Faktury</span>' if row.get("Faktura") == "NIE" else ''
                tags_html = f'<div class="cr-col" style="flex: 2; flex-direction: row; gap: 8px;">{tag_cmr}{tag_pod}{tag_fv}</div>'

                status_val = str(row.get('Status', 'PLANOWANIE')).lower()
                nr_zlecenia_wyswietl = row.get('Nr Zlecenia', 'Brak nr')
                row_idx = row['sheet_row']
                
                # Renderowanie kafelka (Japandi)
                st.markdown(f"""
                <div class="custom-row">
                    <div class="cr-col" style="flex: 2.5;">
                        <div class="cr-title">{nr_zlecenia_wyswietl}</div>
                        <div class="cr-text">🚛 Przewoźnik: {row.get('Przewoźnik', 'Brak danych')}</div>
                        <div class="cr-text" style="color: #C5A880; font-style: italic;">📝 {row.get('Opis Ładunku / Trasy', '---')}</div>
                    </div>
                    <div class="cr-col" style="flex: 1.5;">
                        <div class="cr-text">📅 Zał: {row.get('Data Załadunku', '---')}</div>
                        <div class="cr-text">🏁 Rozł: {row.get('Data Rozładunku', '---')}</div>
                        <div class="cr-text" style="color: #8C8477;">💳 Zapłata: <strong>{row.get('Data Płatności', '---')}</strong></div>
                        <div class="cr-badge {status_val}" style="width: max-content; margin-top: 4px;">{row.get('Status', 'PLANOWANIE')}</div>
                    </div>
                    {tags_html}
                </div>
                """, unsafe_allow_html=True)
                
                # Panel edycji pod kafelkiem
                with st.expander(f"✏️ Edytuj / Archiwizuj zlec. {nr_zlecenia_wyswietl}"):
                    with st.form(key=f"edit_form_{row_idx}", clear_on_submit=False):
                        ecol1, ecol2, ecol3 = st.columns([1.5, 1, 1])
                        
                        with ecol1:
                            e_nr = st.text_input("Numer zlecenia", value=nr_zlecenia_wyswietl)
                            e_przew = st.text_input("Przewoźnik", value=row.get('Przewoźnik', ''))
                            e_opis = st.text_area("Opis Ładunku / Trasy", value=row.get('Opis Ładunku / Trasy', ''), height=115)
                            
                        with ecol2:
                            # Przetworzenie dat z bazy dla kalendarza
                            val_dz = parse_date(row.get('Data Załadunku', ''))
                            val_dr = parse_date(row.get('Data Rozładunku', ''))
                            val_dp = parse_date(row.get('Data Płatności', ''))
                            try:
                                val_term = int(row.get('Termin Dni', 30))
                            except ValueError:
                                val_term = 30
                                
                            e_data_zal = st.date_input("Data załadunku", value=val_dz)
                            e_data_roz = st.date_input("Data rozładunku", value=val_dr)
                            e_termin = st.number_input("Termin (dni)", min_value=0, max_value=120, value=val_term, step=1)
                            e_data_plat = st.date_input("Termin płatności faktury", value=val_dp)
                            
                        with ecol3:
                            statusy = ["INICJACJA", "PLANOWANIE", "ZAŁADUNEK", "TRASA", "ZAMKNIĘTE", "ARCHIWUM"]
                            e_status = st.selectbox("Status", statusy, index=statusy.index(row.get('Status', 'PLANOWANIE')) if row.get('Status') in statusy else 1)
                            
                            opcje_cmr = ["TAK", "NIE", "NIE POTRZEBA"]
                            e_cmr = st.selectbox("Status CMR", opcje_cmr, index=opcje_cmr.index(row.get('CMR', 'NIE')) if row.get('CMR') in opcje_cmr else 1)
                            
                            opcje_pod_fv = ["TAK", "NIE"]
                            e_pod = st.selectbox("Status POD", opcje_pod_fv, index=opcje_pod_fv.index(row.get('POD', 'NIE')) if row.get('POD') in opcje_pod_fv else 1)
                            e_fv = st.selectbox("Faktura opłacona?", opcje_pod_fv, index=opcje_pod_fv.index(row.get('Faktura', 'NIE')) if row.get('Faktura') in opcje_pod_fv else 1)
                            
                        save_btn = st.form_submit_button("💾 Zapisz zmiany", type="primary", use_container_width=True)
                        
                        if save_btn:
                            zakres = f"A{row_idx}:K{row_idx}"
                            nowe_wartosci = [[
                                e_nr, e_przew, e_opis, 
                                str(e_data_zal), str(e_data_roz), str(e_termin), str(e_data_plat.strftime('%d.%m.%Y')), 
                                e_status, e_cmr, e_pod, e_fv
                            ]]
                            try:
                                worksheet.update(values=nowe_wartosci, range_name=zakres)
                                st.success("Zmiany zostały zapisane! Odświeżam...")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Błąd podczas aktualizacji: {e}")
                                
                    # NOWOŚĆ: Przycisk trwałego usunięcia pod formularzem edycji
                    if st.button("🗑️ Usuń trwale to zlecenie z bazy", key=f"del_{row_idx}"):
                        try:
                            worksheet.delete_rows(row_idx)
                            st.success(f"Zlecenie {nr_zlecenia_wyswietl} usunięte. Odświeżam...")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Błąd podczas usuwania: {e}")
        else:
            st.info("Brak aktywnych zleceń pobocznych spełniających kryteria.")

    # ==========================================
    # KARTA 2: UTWÓRZ NOWE ZLECENIE
    # ==========================================
    with tab2:
        st.markdown("<h3 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif;'>Utwórz Nowe Zlecenie Poboczne</h3>", unsafe_allow_html=True)
        with st.form("form_zlecenia_poboczne", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nr_zlecenia = st.text_input("Numer zlecenia")
                przewoznik = st.text_input("Przewoźnik")
                opis_ladunku = st.text_area("Opis Ładunku / Trasy (Co, dokąd, szczegóły)", height=115)
                
                # Dodany układ trzech kolumn do wyliczania płatności
                d1, d2, d3 = st.columns(3)
                with d1: 
                    data_zal = st.date_input("Data załadunku", datetime.today())
                with d2: 
                    data_roz = st.date_input("Data rozładunku", datetime.today())
                with d3: 
                    termin_dni = st.number_input("Termin (dni)", min_value=0, max_value=120, value=30)
                
                data_platnosci = data_roz + timedelta(days=termin_dni)
                st.info(f"📅 Termin płatności faktury: **{data_platnosci.strftime('%d.%m.%Y')}**")

            with col2:
                status = st.selectbox("Status", ["INICJACJA", "PLANOWANIE", "ZAŁADUNEK", "TRASA", "ZAMKNIĘTE"])
                cmr = st.selectbox("Status CMR", ["TAK", "NIE", "NIE POTRZEBA"], index=1)
                pod = st.selectbox("Status POD", ["TAK", "NIE"], index=1)
                faktura = st.selectbox("Czy faktura opłacona?", ["TAK", "NIE"], index=1)
            
            submit_btn = st.form_submit_button("➕ Dodaj do Bazy", type="primary")
            
            if submit_btn:
                if not nr_zlecenia or not przewoznik:
                    st.error("Numer zlecenia i Przewoźnik są wymagane!")
                else:
                    try:
                        worksheet.append_row([
                            nr_zlecenia, przewoznik, opis_ladunku, 
                            str(data_zal), str(data_roz), str(termin_dni), str(data_platnosci.strftime('%d.%m.%Y')), 
                            status, cmr, pod, faktura
                        ])
                        st.success(f"Pomyślnie dodano zlecenie {nr_zlecenia} do bazy Google Sheets!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd podczas zapisu do bazy: {e}")

    # ==========================================
    # KARTA 3: ARCHIWUM
    # ==========================================
    with tab3:
        st.markdown("<h3 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif;'>Archiwum Historyczne</h3>", unsafe_allow_html=True)
        archive_df = df[df['Status'] == 'ARCHIWUM'] if not df.empty else df[0:0]
        
        if not archive_df.empty:
            for index, row in archive_df.iterrows():
                nr_zlecenia_arch = row.get('Nr Zlecenia', 'Brak nr')
                row_idx_arch = row['sheet_row']
                
                st.markdown(f"""
                <div class="custom-row" style="opacity: 0.6; background: rgba(20, 18, 16, 0.5);">
                    <div class="cr-col" style="flex: 2.5;">
                        <div class="cr-title" style="text-decoration: line-through;">{nr_zlecenia_arch}</div>
                        <div class="cr-text">🚛 Przewoźnik: {row.get('Przewoźnik', '')}</div>
                        <div class="cr-text">📝 {row.get('Opis Ładunku / Trasy', '')}</div>
                    </div>
                    <div class="cr-col" style="flex: 1.5;">
                        <div class="cr-text">📅 Zał: {row.get('Data Załadunku', '---')}</div>
                        <div class="cr-text">🏁 Rozł: {row.get('Data Rozładunku', '---')}</div>
                        <div class="cr-badge domyslny" style="width: max-content; margin-top: 4px;">ARCHIWIZOWANO</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"⚙️ Zarządzaj archiwalnym {nr_zlecenia_arch}"):
                    # Rozdzielenie na dwie kolumny: Przywróć i Usuń
                    a1, a2 = st.columns(2)
                    
                    with a1:
                        if st.button("🔄 Przywróć zlecenia do statusu ZAMKNIĘTE", key=f"restore_{row_idx_arch}", use_container_width=True):
                            try:
                                worksheet.update_cell(row_idx_arch, 8, "ZAMKNIĘTE") 
                                st.success("Zlecenie przywrócone! Odświeżam...")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Błąd: {e}")
                    
                    with a2:
                        # NOWOŚĆ: Usuwanie bezpośrednio z archiwum
                        if st.button("🗑️ Trwale usuń z bazy", key=f"del_arch_{row_idx_arch}", use_container_width=True):
                            try:
                                worksheet.delete_rows(row_idx_arch)
                                st.success("Zlecenie całkowicie usunięte z systemu! Odświeżam...")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Błąd podczas usuwania: {e}")
        else:
            st.info("Archiwum jest obecnie puste.")
