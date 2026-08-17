import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import base64
import os
import db

def parse_date(d_str):
    try:
        if "." in str(d_str): return datetime.strptime(str(d_str), "%d.%m.%Y").date()
        else: return datetime.strptime(str(d_str), "%Y-%m-%d").date()
    except:
        return datetime.today().date()

def render(sh):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Zlecenia Poboczne</h1>
            <div class="module-subtitle">サブオーダー ✦ SECONDARY ORDERS</div>
        </div>
    ''', unsafe_allow_html=True)

    worksheet, df = db.load_data(sh, "Zlecenia Poboczne")
    
    if df.empty and not worksheet.row_values(1):
        headers = ["Nr Zlecenia", "Przewoźnik", "Opis Ładunku / Trasy", "Data Załadunku", "Data Rozładunku", "Termin Dni", "Data Płatności", "Status", "CMR", "POD", "Faktura", "Nr Faktury"]
        worksheet.append_row(headers)
        st.cache_data.clear()
        worksheet, df = db.load_data(sh, "Zlecenia Poboczne")

    def is_to_pay(r):
        if str(r.get('Status', '')) == 'ARCHIWUM': return False
        pod = str(r.get('POD', 'NIE')).strip().upper()
        fv = str(r.get('Faktura', 'NIE')).strip().upper()
        nr_fv = str(r.get('Nr Faktury', '')).strip()
        if pod == 'TAK' and nr_fv and nr_fv.lower() not in ['nan', 'none'] and fv != 'TAK':
            return True
        return False

    active_all = df[df.get('Status', pd.Series()) != 'ARCHIWUM'] if not df.empty else df
    
    if not active_all.empty:
        mask = active_all.apply(is_to_pay, axis=1)
        df_do_oplacenia = active_all[mask]
        df_aktywne = active_all[~mask]
    else:
        df_do_oplacenia, df_aktywne = pd.DataFrame(), pd.DataFrame()

    brak_cmr = len(active_all[(active_all.get("CMR") == "NIE")]) if not active_all.empty and "CMR" in active_all.columns else 0
    brak_pod = len(active_all[(active_all.get("POD") == "NIE")]) if not active_all.empty and "POD" in active_all.columns else 0
    brak_fv = len(active_all[(active_all.get("Faktura") == "NIE")]) if not active_all.empty and "Faktura" in active_all.columns else 0

    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-header">DO WYSTAWIENIA CMR</div>
            <div class="kpi-sub-jp">CMRの発行待ち</div>
            <div class="kpi-value">{brak_cmr}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">BRAKUJĄCE ZWROTY POD</div>
            <div class="kpi-sub-jp">POD返却待ち</div>
            <div class="kpi-value">{brak_pod}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">NIEOPŁACONE FAKTURY</div>
            <div class="kpi-sub-jp">未払い請求書</div>
            <div class="kpi-value">{brak_fv}</div>
        </div>
    </div>
    <br>
    """, unsafe_allow_html=True)

    tab1, tab_pay, tab2, tab3 = st.tabs(["⚾ Aktywne Zlecenia", "💳 Do opłacenia", "＋ Utwórz Nowe Zlecenie", "📦 Archiwum (Cold Storage)"])

    b64_batter = ""
    if os.path.exists("batter.png"):
        with open("batter.png", "rb") as f:
            b64_batter = base64.b64encode(f.read()).decode()

    def render_order_list(df_subset, search_query, empty_msg):
        if df_subset.empty:
            st.info(empty_msg)
            return

        for index, row in df_subset.iterrows():
            if search_query.lower() not in str(row.values).lower() and search_query != "":
                continue

            action_buttons = ""
            if row.get("POD") == "NIE":
                action_buttons += f'<span class="btn-action-red" style="margin-right: 8px;">Brak POD</span>'
            if row.get("Faktura") == "NIE":
                action_buttons += f'<span class="btn-action-blue">DO OPŁACENIA</span>'

            status_val = str(row.get('Status', 'PLANOWANIE')).upper()
            nr_zlecenia_wyswietl = row.get('Nr Zlecenia', 'Brak nr')
            row_idx = int(row['sheet_row']) 
            
            img_html = ""
            if b64_batter:
                img_html = f'<div style="position: absolute; right: 20px; top: 50%; transform: translateY(-50%); opacity: 0.15; z-index: 1;"><img src="data:image/png;base64,{b64_batter}" height="80"></div>'

            st.markdown(f"""
            <div class="custom-row">
                {img_html}
                <div style="display: flex; width: 100%; position: relative; z-index: 2;">
                    
                    <div class="cr-col" style="flex: 2.5; padding-right: 15px;">
                        <div class="cr-title">{nr_zlecenia_wyswietl}</div>
                        <div class="cr-text" style="margin-top: 5px;">🚛 Przewoźnik: <strong>{row.get('Przewoźnik', 'Brak')}</strong></div>
                        <div class="cr-text">👤 Opis: <i>{row.get('Opis Ładunku / Trasy', '---')}</i></div>
                    </div>
                    
                    <div class="cr-col" style="flex: 1.5; border-left: 1px dashed rgba(10, 25, 47, 0.3); padding-left: 20px; justify-content: center;">
                        <div class="cr-text">📅 Zał: {row.get('Data Załadunku', '---')}</div>
                        <div class="cr-text">🏁 Rozł: {row.get('Data Rozładunku', '---')}</div>
                        <div class="cr-text">💲 Płatność: <strong>{row.get('Data Płatności', '---')}</strong></div>
                        <div style="font-size: 10px; font-weight: 700; margin-top: 5px; color: #0A192F;">{status_val}</div>
                    </div>
                    
                    <div class="cr-col" style="flex: 1.2; align-items: flex-end; justify-content: center; flex-direction: row; gap: 5px; padding-right: 80px;">
                        {action_buttons}
                    </div>
                </div>
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
                        e_nr_faktury = st.text_input("Nr Faktury", value=str(row.get("Nr Faktury", "")).replace("nan", "").strip(), placeholder="Wpisz by przesłać do opłacenia")
                        
                    save_btn = st.form_submit_button("💾 Zapisz zmiany")
                    
                    if save_btn:
                        nowe_wartosci = [e_nr, e_przew, e_opis, str(e_data_zal), str(e_data_roz), str(e_termin), str(e_data_plat.strftime('%d.%m.%Y')), e_status, e_cmr, e_pod, e_fv, e_nr_faktury]
                        if e_status == "ARCHIWUM":
                            if db.archive_row_safe("Zlecenia Poboczne", "Zlecenia Poboczne ARCHIWUM", row_idx, nowe_wartosci):
                                st.success("Zlecenie przeniesione do archiwum!")
                                st.rerun()
                        else:
                            if db.update_row("Zlecenia Poboczne", row_idx, nowe_wartosci):
                                st.success("Zaktualizowano pomyślnie!")
                                st.rerun()
                            
                if st.button("🗑️ Usuń trwale to zlecenie", key=f"del_{row_idx}"):
                    if db.delete_row("Zlecenia Poboczne", row_idx):
                        st.success(f"Usunięto pomyślnie.")
                        st.rerun()

    with tab1:
        sq_akt = st.text_input("", placeholder="🔍 Wpisz nazwę przewoźnika, opis, numer...", key="sq_akt", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        render_order_list(df_aktywne, sq_akt, "Brak aktywnych zleceń pobocznych.")

    with tab_pay:
        st.info("💡 Zlecenia, w których odzyskano POD oraz wprowadzono Nr Faktury zewnętrznej. Oczekują na płatność.")
        sq_pay = st.text_input("", placeholder="🔍 Wpisz numer faktury, przewoźnika...", key="sq_pay", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        render_order_list(df_do_oplacenia, sq_pay, "Obecnie brak zleceń gotowych do opłacenia.")

    with tab2:
        st.markdown("<h3 style='color: #0A192F; font-family: \"Playball\", cursive; font-size: 36px;'>Utwórz Nowe Zlecenie Poboczne</h3>", unsafe_allow_html=True)
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
                
            with col2:
                status = st.selectbox("Status", ["INICJACJA", "PLANOWANIE", "ZAŁADUNEK", "TRASA", "ZAMKNIĘTE"])
                cmr = st.selectbox("Status CMR", ["TAK", "NIE", "NIE POTRZEBA"], index=1)
                pod = st.selectbox("Status POD", ["TAK", "NIE"], index=1)
                faktura = st.selectbox("Czy faktura opłacona?", ["TAK", "NIE"], index=1)
                nr_faktury = st.text_input("Nr Faktury (jeśli już znasz)")
            
            if st.form_submit_button("＋ Dodaj do Bazy"):
                data_platnosci = data_roz + timedelta(days=termin_dni)
                if not nr_zlecenia or not przewoznik: st.error("Numer zlecenia i Przewoźnik są wymagane!")
                else:
                    nowy_wiersz = [nr_zlecenia, przewoznik, opis_ladunku, str(data_zal), str(data_roz), str(termin_dni), str(data_platnosci.strftime('%d.%m.%Y')), status, cmr, pod, faktura, nr_faktury]
                    if db.append_data("Zlecenia Poboczne", nowy_wiersz):
                        st.success(f"Dodano zlecenie {nr_zlecenia}!")
                        st.rerun()

    with tab3:
        if "arch_loaded_poboczne" not in st.session_state: st.session_state["arch_loaded_poboczne"] = False

        if not st.session_state["arch_loaded_poboczne"]:
            if st.button("📥 Połącz i wczytaj bazę archiwalną", use_container_width=True):
                st.session_state["arch_loaded_poboczne"] = True
                st.rerun()
                
        if st.session_state["arch_loaded_poboczne"]:
            if st.button("❌ Ukryj archiwum", use_container_width=True):
                st.session_state["arch_loaded_poboczne"] = False
                st.rerun()
                
            with st.spinner("Pobieranie danych z Google Sheets..."):
                df_arch = db.fetch_data("Zlecenia Poboczne ARCHIWUM")
            
            if not df_arch.empty: st.dataframe(df_arch, use_container_width=True, hide_index=True)
            else: st.warning("Archiwum jest puste.")
