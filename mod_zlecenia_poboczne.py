import streamlit as st
import pandas as pd
from datetime import datetime

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

    # Pobieranie danych z Google Sheets (odczytujemy surowe wartości, aby mieć kontrolę nad wierszami)
    try:
        worksheet = sh.worksheet("Zlecenia Poboczne")
        data = worksheet.get_all_values()
        
        # Jeśli arkusz jest całkowicie pusty, inicjujemy nagłówki
        if not data:
            headers = ["Nr Zlecenia", "Przewoźnik", "Opis Ładunku / Trasy", "Data Załadunku", "Status", "CMR", "POD", "Faktura"]
            worksheet.append_row(headers)
            data = [headers]
            
        headers = data[0]
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=headers)
            # Dodajemy indeks wiersza z arkusza (indeks w df to 0, a w arkuszu dane zaczynają się od wiersza 2)
            df['sheet_row'] = df.index + 2
        else:
            df = pd.DataFrame(columns=headers)
            df['sheet_row'] = []
            
    except Exception as e:
        st.error(f"Błąd komunikacji z Google Sheets: {e}. Upewnij się, że zakładka 'Zlecenia Poboczne' istnieje.")
        return

    # KARTA 1: AKTYWNE ZLECENIA
    with tab1:
        st.markdown("<div style='font-size: 10px; color: #C5A880; font-weight: 700; letter-spacing: 1px; margin-bottom: 5px;'>⚡ WYSZUKAJ I FILTRUJ ZLECENIA:</div>", unsafe_allow_html=True)
        search_query = st.text_input("", placeholder="🔍 Wpisz nazwę przewoźnika, opis, numer...", label_visibility="collapsed")

        # Filtrowanie tylko aktywnych zleceń (odrzucamy ARCHIWUM)
        active_df = df[df['Status'] != 'ARCHIWUM'] if not df.empty else df

        # Obliczenia metryk dla kart KPI (tylko dla aktywnych!)
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

                # Pigułka statusu - dynamiczny kolor
                status_val = str(row.get('Status', 'PLANOWANIE')).lower()
                
                # Renderowanie kafelka (Japandi)
                st.markdown(f"""
                <div class="custom-row">
                    <div class="cr-col" style="flex: 2.5;">
                        <div class="cr-title">{row.get('Nr Zlecenia', 'Brak nr')}</div>
                        <div class="cr-text">🚛 Przewoźnik: {row.get('Przewoźnik', 'Brak danych')}</div>
                        <div class="cr-text" style="color: #C5A880; font-style: italic;">📝 {row.get('Opis Ładunku / Trasy', '---')}</div>
                    </div>
                    <div class="cr-col" style="flex: 1.5;">
                        <div class="cr-text">📅 Zał: {row.get('Data Załadunku', '---')}</div>
                        <div class="cr-badge {status_val}" style="width: max-content;">{row.get('Status', 'PLANOWANIE')}</div>
                    </div>
                    {tags_html}
                </div>
                """, unsafe_allow_html=True)
                
                # Panel edycji pod kafelkiem
                with st.expander(f"✏️ Edytuj / Archiwizuj zlec. {row.get('Nr Zlecenia', '')}"):
                    with st.form(key=f"edit_form_{row['sheet_row']}", clear_on_submit=False):
                        ecol1, ecol2 = st.columns(2)
                        with ecol1:
                            e_nr = st.text_input("Numer zlecenia", value=row.get('Nr Zlecenia', ''))
                            e_przew = st.text_input("Przewoźnik", value=row.get('Przewoźnik', ''))
                            e_opis = st.text_area("Opis Ładunku / Trasy", value=row.get('Opis Ładunku / Trasy', ''), height=115)
                        with ecol2:
                            e_data = st.text_input("Data załadunku", value=row.get('Data Załadunku', ''))
                            # Domyślny indeks dla selectboxa
                            statusy = ["INICJACJA", "PLANOWANIE", "ZAŁADUNEK", "TRASA", "ZAMKNIĘTE", "ARCHIWUM"]
                            e_status = st.selectbox("Status (Wybierz ARCHIWUM aby zarchiwizować)", statusy, index=statusy.index(row.get('Status', 'PLANOWANIE')) if row.get('Status') in statusy else 1)
                            
                            opcje_cmr = ["TAK", "NIE", "NIE POTRZEBA"]
                            e_cmr = st.selectbox("Status CMR", opcje_cmr, index=opcje_cmr.index(row.get('CMR', 'NIE')) if row.get('CMR') in opcje_cmr else 1)
                            
                            opcje_pod_fv = ["TAK", "NIE"]
                            e_pod = st.selectbox("Status POD", opcje_pod_fv, index=opcje_pod_fv.index(row.get('POD', 'NIE')) if row.get('POD') in opcje_pod_fv else 1)
                            e_fv = st.selectbox("Faktura opłacona?", opcje_pod_fv, index=opcje_pod_fv.index(row.get('Faktura', 'NIE')) if row.get('Faktura') in opcje_pod_fv else 1)
                            
                        save_btn = st.form_submit_button("💾 Zapisz zmiany", type="primary")
                        
                        if save_btn:
                            # Aktualizacja wskazanego wiersza w Google Sheets (kolumny A do H)
                            zakres = f"A{row['sheet_row']}:H{row['sheet_row']}"
                            nowe_wartosci = [[e_nr, e_przew, e_opis, e_data, e_status, e_cmr, e_pod, e_fv]]
                            try:
                                worksheet.update(values=nowe_wartosci, range_name=zakres)
                                st.success("Zmiany zostały zapisane! Odświeżam...")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Błąd podczas aktualizacji: {e}")
        else:
            st.info("Brak aktywnych zleceń pobocznych spełniających kryteria.")

    # KARTA 2: UTWÓRZ NOWE ZLECENIE
    with tab2:
        st.markdown("<h3 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif;'>Utwórz Nowe Zlecenie Poboczne</h3>", unsafe_allow_html=True)
        with st.form("form_zlecenia_poboczne", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nr_zlecenia = st.text_input("Numer zlecenia")
                przewoznik = st.text_input("Przewoźnik")
                opis_ladunku = st.text_area("Opis Ładunku / Trasy (Co, dokąd, szczegóły)", height=115)
                data_zal = st.date_input("Data załadunku", datetime.today())
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
                        worksheet.append_row([nr_zlecenia, przewoznik, opis_ladunku, str(data_zal), status, cmr, pod, faktura])
                        st.success(f"Pomyślnie dodano zlecenie {nr_zlecenia} do bazy Google Sheets!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd podczas zapisu do bazy: {e}")

    # KARTA 3: ARCHIWUM
    with tab3:
        st.markdown("<h3 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif;'>Archiwum Historyczne</h3>", unsafe_allow_html=True)
        archive_df = df[df['Status'] == 'ARCHIWUM'] if not df.empty else df[0:0]
        
        if not archive_df.empty:
            for index, row in archive_df.iterrows():
                st.markdown(f"""
                <div class="custom-row" style="opacity: 0.6; background: rgba(20, 18, 16, 0.5);">
                    <div class="cr-col" style="flex: 2.5;">
                        <div class="cr-title" style="text-decoration: line-through;">{row.get('Nr Zlecenia', 'Brak nr')}</div>
                        <div class="cr-text">🚛 Przewoźnik: {row.get('Przewoźnik', '')}</div>
                        <div class="cr-text">📝 {row.get('Opis Ładunku / Trasy', '')}</div>
                    </div>
                    <div class="cr-col" style="flex: 1.5;">
                        <div class="cr-text">📅 Zał: {row.get('Data Załadunku', '---')}</div>
                        <div class="cr-badge domyslny" style="width: max-content;">ARCHIWIZOWANO</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Możliwość przywrócenia z archiwum
                with st.expander(f"⚙️ Zarządzaj archiwalnym {row.get('Nr Zlecenia', '')}"):
                    if st.button("🔄 Przywróć zlecenia do statusu ZAMKNIĘTE", key=f"restore_{row['sheet_row']}"):
                        try:
                            worksheet.update_cell(row['sheet_row'], 5, "ZAMKNIĘTE") # Kolumna 5 to Status
                            st.success("Zlecenie przywrócone! Odświeżam...")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Błąd: {e}")
        else:
            st.info("Archiwum jest obecnie puste.")
