import streamlit as st
import pandas as pd
from datetime import datetime

def render(sh):
    # Nagłówek w stylu Japandi (zgodny z nowym style.css)
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Zlecenia Poboczne</h1>
            <div class="module-subtitle">サブオーダー ✦ SECONDARY ORDERS</div>
        </div>
    ''', unsafe_allow_html=True)

    # Nawigacja - Zakładki
    tab1, tab2, tab3 = st.tabs(["📂 Aktywne Zlecenia", "➕ Utwórz Nowe Zlecenie", "📦 Archiwum Historyczne"])

    # Pobieranie danych z Google Sheets
    # UWAGA: Upewnij się, że w Google Sheets masz arkusz o nazwie "Zlecenia Poboczne"
    try:
        worksheet = sh.worksheet("Zlecenia Poboczne")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Brak zakładki 'Zlecenia Poboczne' w Google Sheets lub arkusz jest pusty. Zbuduj arkusz z kolumnami: Nr Zlecenia, Przewoźnik, Data Załadunku, Status, CMR, POD, Faktura. Błąd: {e}")
        df = pd.DataFrame(columns=["Nr Zlecenia", "Przewoźnik", "Data Załadunku", "Status", "CMR", "POD", "Faktura"])

    with tab1:
        # Wyszukiwarka
        st.markdown("<div style='font-size: 10px; color: #C5A880; font-weight: 700; letter-spacing: 1px; margin-bottom: 5px;'>⚡ WYSZUKAJ I FILTRUJ ZLECENIA:</div>", unsafe_allow_html=True)
        search_query = st.text_input("", placeholder="🔍 Wpisz nazwę przewoźnika, numer zlecenia...", label_visibility="collapsed")

        # Obliczenia metryk dla kart KPI (przykładowa logika - można dostosować do dokładnych nazw kolumn w GSheets)
        brak_cmr = len(df[(df.get("CMR") == "NIE")]) if not df.empty and "CMR" in df.columns else 0
        brak_pod = len(df[(df.get("POD") == "NIE")]) if not df.empty and "POD" in df.columns else 0
        brak_fv = len(df[(df.get("Faktura") == "NIE")]) if not df.empty and "Faktura" in df.columns else 0

        # KARTY KPI (korzystają z japońskiego Washi i czcionek pędzlowych)
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

        # Filtrowanie i renderowanie wierszy na podstawie dataframe
        if not df.empty:
            for index, row in df.iterrows():
                # Prosta logika wyszukiwania
                if search_query.lower() not in str(row.values).lower() and search_query != "":
                    continue

                # Definiowanie tagów braków
                tag_cmr = '<span class="tag-zen-orange">Brak CMR</span>' if row.get("CMR") == "NIE" else ('<span class="tag-zen-blue">CMR: Nie Dotyczy</span>' if row.get("CMR") == "NIE POTRZEBA" else '')
                tag_pod = '<span class="tag-zen-red">Brak POD</span>' if row.get("POD") == "NIE" else ''
                tag_fv = '<span class="tag-zen-orange">Brak Faktury</span>' if row.get("Faktura") == "NIE" else ''
                
                tags_html = f'<div class="cr-col" style="flex: 2; flex-direction: row; gap: 8px;">{tag_cmr}{tag_pod}{tag_fv}</div>'

                # Renderowanie Custom Row w stylu Japandi
                st.markdown(f"""
                <div class="custom-row">
                    <div class="cr-col" style="flex: 2;">
                        <div class="cr-title">{row.get('Nr Zlecenia', 'Brak nr')}</div>
                        <div class="cr-text">🚛 Przewoźnik: {row.get('Przewoźnik', 'Brak danych')}</div>
                    </div>
                    <div class="cr-col" style="flex: 2;">
                        <div class="cr-text">📅 Załadunek: {row.get('Data Załadunku', '---')}</div>
                        <div class="cr-badge domyslny" style="width: max-content;">{row.get('Status', 'PLANOWANIE')}</div>
                    </div>
                    {tags_html}
                    <div class="cr-col" style="flex: 1; align-items: flex-end;">
                        <button style="background: transparent; border: 1px solid rgba(197, 168, 128, 0.4); color: #C5A880; padding: 6px 14px; border-radius: 4px; font-size: 10px; cursor: pointer; transition: all 0.3s ease;">🔍 Szczegóły</button>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Brak aktywnych zleceń pobocznych lub brak połączenia z bazą.")

    with tab2:
        st.markdown("<h3 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif;'>Nowe Zlecenie Poboczne</h3>", unsafe_allow_html=True)
        with st.form("form_zlecenia_poboczne", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nr_zlecenia = st.text_input("Numer zlecenia")
                przewoznik = st.text_input("Przewoźnik")
                data_zal = st.date_input("Data załadunku", datetime.today())
            with col2:
                status = st.selectbox("Status", ["INICJACJA", "PLANOWANIE", "ZAŁADUNEK", "TRASA", "ZAMKNIĘTE"])
                cmr = st.selectbox("Status CMR", ["TAK", "NIE", "NIE POTRZEBA"])
                pod = st.selectbox("Status POD", ["TAK", "NIE"])
                faktura = st.selectbox("Czy faktura opłacona?", ["TAK", "NIE"])
            
            submit_btn = st.form_submit_button("➕ Dodaj do Bazy", type="primary")
            
            if submit_btn:
                if not nr_zlecenia or not przewoznik:
                    st.error("Numer zlecenia i Przewoźnik są wymagane!")
                else:
                    try:
                        worksheet.append_row([nr_zlecenia, przewoznik, str(data_zal), status, cmr, pod, faktura])
                        st.success(f"Pomyślnie dodano zlecenie {nr_zlecenia} do bazy Google Sheets!")
                    except Exception as e:
                        st.error(f"Błąd podczas zapisu do bazy: {e}")

    with tab3:
        st.markdown("<p style='color: #8C8477;'>Sekcja archiwum (w budowie).</p>", unsafe_allow_html=True)
