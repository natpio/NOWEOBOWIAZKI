import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import base64
import os
import db

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
    # Nagłówek w stylu Baseball x Japandi
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Zlecenia Poboczne</h1>
            <div class="module-subtitle">⚾ サブオーダー ✦ SECONDARY ORDERS</div>
        </div>
    ''', unsafe_allow_html=True)

    # 1. POBIERANIE DANYCH Z ZAKŁADKI (Przed renderowaniem czegokolwiek)
    worksheet, df = db.load_data(sh, "Zlecenia Poboczne")
    
    # Inicjalizacja pustej bazy, jeśli jeszcze nie ma nagłówków
    if df.empty and not worksheet.row_values(1):
        headers = ["Nr Zlecenia", "Przewoźnik", "Opis Ładunku / Trasy", "Data Załadunku", "Data Rozładunku", "Termin Dni", "Data Płatności", "Status", "CMR", "POD", "Faktura", "Nr Faktury"]
        worksheet.append_row(headers)
        st.cache_data.clear()
        worksheet, df = db.load_data(sh, "Zlecenia Poboczne")

    # 2. LOGIKA ROZDZIELANIA NA ZAKŁADKI
    def is_to_pay(r):
        if str(r.get('Status', '')) == 'ARCHIWUM': 
            return False
        pod = str(r.get('POD', 'NIE')).strip().upper()
        fv = str(r.get('Faktura', 'NIE')).strip().upper()
        nr_fv = str(r.get('Nr Faktury', '')).strip()
        # Warunek przerzucenia: Jest POD + Jest podany numer Faktury + Faktura nie jest jeszcze opłacona
        if pod == 'TAK' and nr_fv and nr_fv.lower() not in ['nan', 'none'] and fv != 'TAK':
            return True
        return False

    active_all = df[df.get('Status', pd.Series()) != 'ARCHIWUM'] if not df.empty else df
    
    if not active_all.empty:
        mask = active_all.apply(is_to_pay, axis=1)
        df_do_oplacenia = active_all[mask]
        df_aktywne = active_all[~mask]
    else:
        df_do_oplacenia = pd.DataFrame()
        df_aktywne = pd.DataFrame()

    # 3. OBLICZANIE KART KPI
    brak_cmr = len(active_all[(active_all.get("CMR") == "NIE")]) if not active_all.empty and "CMR" in active_all.columns else 0
    brak_pod = len(active_all[(active_all.get("POD") == "NIE")]) if not active_all.empty and "POD" in active_all.columns else 0
    brak_fv = len(active_all[(active_all.get("Faktura") == "NIE")]) if not active_all.empty and "Faktura" in active_all.columns else 0

    # 4. WYSWIETLANIE KART KPI NA SAMEJ GÓRZE WIDOKU
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-header">DO WYSTAWIENIA CMR</div>
            <div class="kpi-sub-jp">CMRの発行待ち</div>
            <div class="kpi-value">{brak_cmr}</div>
            <div class="kpi-icon-bg">📝</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">BRAKUJĄCE ZWROTY POD</div>
            <div class="kpi-sub-jp">POD受領待ち</div>
            <div class="kpi-value">{brak_pod}</div>
            <div class="kpi-icon-bg">📄</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">NIEOPŁACONE FAKTURY</div>
            <div class="kpi-sub-jp">未払い請求書</div>
            <div class="kpi-value">{brak_fv}</div>
            <div class="kpi-icon-bg">💰</div>
        </div>
    </div>
    <br>
    """, unsafe_allow_html=True)

    # 5. DEKLARACJA ZAKŁADEK
    tab1, tab_pay, tab2, tab3 = st.tabs(["⚾ Aktywne Zlecenia", "💳 Do opłacenia", "＋ Utwórz Nowe Zlecenie", "📦 Archiwum (Cold Storage)"])

    # Przygotowanie Base64 dla sylwetki pałkarza na kafelkach (jeśli plik istnieje)
    b64_batter = ""
    if os.path.exists("batter.png"):
        with open("batter.png", "rb") as f:
            b64_batter = base64.b64encode(f.read()).decode()

    # Funkcja generująca widok kafelków (biletów meczowych)
    def render_order_list(df_subset, search_query, empty_msg):
        if df_subset.empty:
            st.info(empty_msg)
            return

        for index, row in df_subset.iterrows():
            if search_query.lower() not in str(row.values).lower() and search_query != "":
                continue

            tag_cmr = '<span class="tag-zen-orange">Brak CMR</span>' if row.get("CMR") == "NIE" else ('<span class="tag-zen-blue">CMR: N/A</span>' if row.get("CMR") == "NIE POTRZEBA" else '')
            tag_pod = '<span class="tag-zen-red">Brak POD</span>' if row.get("POD") == "NIE" else ''
            tag_fv = '<span class="tag-zen-orange">DO OPŁACENIA</span>' if row.get("Faktura") == "NIE" else ''
            
            nr_faktury_val = str(row.get("Nr Faktury", "")).replace("nan", "").strip()
            tag_nr_fv = f'<span class="tag-zen-blue">FV: {nr_faktury_val}</span>' if nr_faktury_val else ''

            tags_html = f'<div class="cr-col" style="flex: 2; flex-direction: row; gap: 8px; align-items: center;">{tag_cmr}{tag_pod}{tag_fv}{tag_nr_fv}</div>'

            status_val = str(row.get('Status', 'PLANOWANIE')).lower()
            nr_zlecenia_wyswietl = row.get('Nr Zlecenia', 'Brak nr')
            row_idx = int(row['sheet_row']) 
            
            # Styl tła z solidnym ecru i opcjonalną sylwetką pałkarza po prawej stronie
            if b64_batter:
                bg_style = f"background-color: #F7F3EC; background-image: url('washi_bg.jpg'), url('data:image/png;base64,{b64_batter}'); background-blend-mode: multiply, normal; background-size: cover, 140px auto; background-position: center, right center; background-repeat: no-repeat, no-repeat;"
            else:
                bg_style = "background-color: #F7F3EC; background-image: url('washi_bg.jpg'); background-blend-mode: multiply; background-size: cover; background-position: center;"

            st.markdown(f"""
            <div class="custom-row" style="{bg_style}">
                <div class="cr-col" style="flex: 2.5;">
                    <div class="cr-title">⚾ {nr_zlecenia_wyswietl}</div>
                    <div class="cr-text">🚛 Przewoźnik: <strong>{row.get('Przewoźnik', 'Brak')}</strong></div>
                    <div class="cr-text" style="color: #990000; font-style: italic;">📝 {row.get('Opis Ładunku / Trasy', '---')}</div>
                </div>
                <div class="cr-col" style="flex: 1.5;">
                    <div class="cr-text">📅 Zał: {row.get('Data Załadunku', '---')}</div>
                    <div class="cr-text">🏁 Rozł: {row.get('Data Rozładunku', '---')}</div>
                    <div class="cr-text">💳 Płatność: <strong>{row.get('Data Płatności', '---')}</strong></div>
                    <div class="cr-badge {status_val}" style="width: max-content; margin-top: 4px;">{row.get('Status', 'PLANOWANIE')}</div>
                </div>
                {tags_html}
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"✏️ Edytuj / Archiwizuj zlec. {nr_zlecenia_wyswietl}"):
                with st.form(key=f"edit_form_{row_idx}", clear_on_submit=False):
                    ecol1, ecol2, ecol3 = st.columns([1.5, 1, 1])
                    
                    with ecol1:
                        e_nr = st.text_input("Numer zlecenia", value=nr_zlecenia_wyswietl)
                        e_przew = st.text_input("Przewoźnik", value=str(row.get('Przewoźnik', '')))
                        e_opis = st.text_area("Opis Ładunku / Trasy", value=str(row.get('Opis Ładunku / Trasy', '')), height=115)
                        
                    with ecol2:
                        val_dz = parse_date(row.get('Data Załadunku', ''))
                        val_dr = parse_date(row.get('Data Rozładunku', ''))
                        val_dp = parse_date(row.get('Data Płatności', ''))
                        try: val_term = int(row.get('Termin Dni', 30))
                        except ValueError: val_term = 30
                            
                        e_data_zal = st.date_input("Data załadunku", value=val_dz)
                        e_data_roz = st.date_input("Data rozładunku", value=val_dr)
                        e_termin = st.number_input("Termin (dni)", min_value=0, max_value=120, value=val_term, step=1)
                        e_data_plat = st.date_input("Termin płatności", value=val_dp)
                        
                    with ecol3:
                        statusy = ["INICJACJA", "PLANOWANIE", "ZAŁADUNEK", "TRASA", "ZAMKNIĘTE", "ARCHIWUM"]
                        e_status = st.selectbox("Status", statusy, index=statusy.index(row.get('Status', 'PLANOWANIE')) if row.get('Status') in statusy else 1)
                        
                        opcje_cmr = ["TAK", "NIE", "NIE POTRZEBA"]
                        e_cmr = st.selectbox("Status CMR", opcje_cmr, index=opcje_cmr.index(row.get('CMR', 'NIE')) if row.get('CMR') in opcje_cmr else 1)
                        
                        opcje_pod_fv = ["TAK", "NIE"]
                        e_pod = st.selectbox("Status POD", opcje_pod_fv, index=opcje_pod_fv.index(row.get('POD', 'NIE')) if row.get('POD') in opcje_pod_fv else 1)
                        e_fv = st.selectbox("Faktura opłacona?", opcje_pod_fv, index=opcje_pod_fv.index(row.get('Faktura', 'NIE')) if row.get('Faktura') in opcje_pod_fv else 1)
                        e_nr_faktury = st.text_input("Nr Faktury", value=nr_faktury_val, placeholder="Wpisz by przesłać do opłacenia")
                        
                    save_btn = st.form_submit_button("💾 Zapisz zmiany", type="primary")
                    
                    if save_btn:
                        nowe_wartosci = [
                            e_nr, e_przew, e_opis, 
                            str(e_data_zal), str(e_data_roz), str(e_termin), str(e_data_plat.strftime('%d.%m.%Y')), 
                            e_status, e_cmr, e_pod, e_fv, e_nr_faktury
                        ]
                        
                        if e_status == "ARCHIWUM":
                            if db.archive_row_safe("Zlecenia Poboczne", "Zlecenia Poboczne ARCHIWUM", row_idx, nowe_wartosci):
                                st.success("Zlecenie przeniesione do fizycznego archiwum Cold Storage!")
                                st.rerun()
                        else:
                            if db.update_row("Zlecenia Poboczne", row_idx, nowe_wartosci):
                                st.success("Zaktualizowano zlecenie punktowo!")
                                st.rerun()
                            
                if st.button("🗑️ Usuń trwale to zlecenie", key=f"del_{row_idx}"):
                    if db.delete_row("Zlecenia Poboczne", row_idx):
                        st.success(f"Zlecenie usunięte pomyślnie.")
                        st.rerun()

    # ==========================================
    # KARTA 1: AKTYWNE ZLECENIA
    # ==========================================
    with tab1:
        st.markdown("<div style='font-size: 11px; color: #C5A880; font-weight: 700; letter-spacing: 1px; margin-bottom: 5px; text-transform: uppercase;'>⚾ Wyszukaj w aktywnych:</div>", unsafe_allow_html=True)
        sq_akt = st.text_input("", placeholder="🔍 Wpisz nazwę przewoźnika, opis, numer...", key="sq_akt", label_visibility="collapsed")
        render_order_list(df_aktywne, sq_akt, "Brak aktywnych zleceń pobocznych.")

    # ==========================================
    # KARTA 2: DO OPŁACENIA
    # ==========================================
    with tab_pay:
        st.info("💡 Znajdują się tu zlecenia, w których **odzyskano POD** oraz wprowadzono **Numer Faktury zewnętrznej**. Oczekują one wyłącznie na opłacenie.")
        st.markdown("<div style='font-size: 11px; color: #C5A880; font-weight: 700; letter-spacing: 1px; margin-bottom: 5px; text-transform: uppercase;'>⚾ Wyszukaj w zobowiązaniach:</div>", unsafe_allow_html=True)
        sq_pay = st.text_input("", placeholder="🔍 Wpisz numer faktury, przewoźnika...", key="sq_pay", label_visibility="collapsed")
        render_order_list(df_do_oplacenia, sq_pay, "Obecnie brak zleceń gotowych do opłacenia.")

    # ==========================================
    # KARTA 3: UTWÓRZ NOWE ZLECENIE
    # ==========================================
    with tab2:
        st.markdown("<h3 style='color: #FDFBF7; font-family: \"Playball\", cursive; font-size: 36px;'>Utwórz Nowe Zlecenie Poboczne</h3>", unsafe_allow_html=True)
        with st.form("form_zlecenia_poboczne", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nr_zlecenia = st.text_input("Numer zlecenia")
                przewoznik = st.text_input("Przewoźnik")
                opis_ladunku = st.text_area("Opis Ładunku / Trasy (Co, dokąd, szczegóły)", height=115)
                
                d1, d2, d3 = st.columns(3)
                with d1: data_zal = st.date_input("Data załadunku", datetime.today())
                with d2: data_roz = st.date_input("Data rozładunku", datetime.today())
                with d3: termin_dni = st.number_input("Termin (dni)", min_value=0, max_value=120, value=30)
                
                data_platnosci = data_roz + timedelta(days=termin_dni)
                st.info(f"📅 Termin płatności faktury: **{data_platnosci.strftime('%d.%m.%Y')}**")

            with col2:
                status = st.selectbox("Status", ["INICJACJA", "PLANOWANIE", "ZAŁADUNEK", "TRASA", "ZAMKNIĘTE"])
                cmr = st.selectbox("Status CMR", ["TAK", "NIE", "NIE POTRZEBA"], index=1)
                pod = st.selectbox("Status POD", ["TAK", "NIE"], index=1)
                faktura = st.selectbox("Czy faktura opłacona?", ["TAK", "NIE"], index=1)
                nr_faktury = st.text_input("Nr Faktury (jeśli już znasz)")
            
            submit_btn = st.form_submit_button("＋ Dodaj do Bazy", type="primary")
            
            if submit_btn:
                if not nr_zlecenia or not przewoznik:
                    st.error("Numer zlecenia i Przewoźnik są wymagane!")
                else:
                    nowy_wiersz = [
                        nr_zlecenia, przewoznik, opis_ladunku, 
                        str(data_zal), str(data_roz), str(termin_dni), str(data_platnosci.strftime('%d.%m.%Y')), 
                        status, cmr, pod, faktura, nr_faktury
                    ]
                    if db.append_data("Zlecenia Poboczne", nowy_wiersz):
                        st.success(f"Dodano zlecenie {nr_zlecenia} na dół arkusza!")
                        st.rerun()

    # ==========================================
    # KARTA 4: ARCHIWUM
    # ==========================================
    with tab3:
        st.markdown("<h3 style='color: #FDFBF7; font-family: \"Playball\", cursive; font-size: 36px;'>Archiwum Historyczne (Cold Storage)</h3>", unsafe_allow_html=True)
        st.info("🗄️ Zakończone zlecenia są wyizolowane do osobnej zakładki w chmurze, aby nie spowalniać pracy systemu. Załaduj je tylko w razie potrzeby.")
        
        if "arch_loaded_poboczne" not in st.session_state:
            st.session_state["arch_loaded_poboczne"] = False

        if not st.session_state["arch_loaded_poboczne"]:
            if st.button("📥 Połącz i wczytaj bazę archiwalną", use_container_width=True):
                st.session_state["arch_loaded_poboczne"] = True
                st.rerun()
                
        if st.session_state["arch_loaded_poboczne"]:
            if st.button("❌ Ukryj archiwum (Zwolnij pamięć)", use_container_width=True, type="secondary"):
                st.session_state["arch_loaded_poboczne"] = False
                st.rerun()
                
            with st.spinner("Pobieranie ciężkich danych archiwalnych z Google Sheets..."):
                df_arch = db.fetch_data("Zlecenia Poboczne ARCHIWUM")
            
            if not df_arch.empty:
                st.dataframe(df_arch, use_container_width=True, hide_index=True)
            else:
                st.warning("Archiwum jest puste lub zakładka 'Zlecenia Poboczne ARCHIWUM' jeszcze nie powstała.")
