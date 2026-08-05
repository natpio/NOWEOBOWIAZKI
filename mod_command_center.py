import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
from collections import defaultdict
import db

def normalize_date(date_val):
    """Bezpiecznie konwertuje różne formaty dat z bazy na standard YYYY-MM-DD"""
    if pd.isna(date_val) or not str(date_val).strip():
        return None
    d_str = str(date_val).strip()
    try:
        if "." in d_str:
            return datetime.strptime(d_str, "%d.%m.%Y").strftime("%Y-%m-%d")
        elif "-" in d_str:
            # Próbuje zinterpretować długą datę z godziną lub krótką
            return datetime.strptime(d_str.split(" ")[0], "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        return None
    return None

def render(sh):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Command Center</h1>
            <div class="module-subtitle">コマンドセンター ✦ LOGISTICS DASHBOARD</div>
        </div>
    ''', unsafe_allow_html=True)

    # --- INICJALIZACJA STANU DLA KALENDARZA ---
    today = datetime.now()
    if 'cal_month' not in st.session_state:
        st.session_state.cal_month = today.month
    if 'cal_year' not in st.session_state:
        st.session_state.cal_year = today.year
    if 'cal_selected_date' not in st.session_state:
        st.session_state.cal_selected_date = today.strftime("%Y-%m-%d")

    # --- POBIERANIE DANYCH Z CHMURY ---
    with st.spinner("Synchronizacja radaru operacyjnego..."):
        df_zlecenia = db.fetch_data("Zlecenia")
        df_poboczne = db.fetch_data("Zlecenia Poboczne")

    # --- AGREGACJA ZDARZEŃ W SŁOWNIKU ---
    all_events = defaultdict(list)

    # 1. Analiza Zleceń PRO
    if not df_zlecenia.empty:
        for _, row in df_zlecenia.iterrows():
            nr = row.get("Numer zlecenia", "Brak NR")
            projekt = row.get("ID Projektu", "")
            
            # Załadunki PRO
            d_zal = normalize_date(row.get("Data załadunku"))
            if d_zal:
                all_events[d_zal].append({
                    "typ": "ZAŁADUNEK (PRO)", "nr": nr, 
                    "szczegoly": f"Projekt: {projekt} | Miejsce: {row.get('Miejsce Zaladunku', '')}", 
                    "kolor": "#C9A471", "ikona": "🟢"
                })
            
            # Rozładunki PRO
            d_roz = normalize_date(row.get("Data rozładunku"))
            if d_roz:
                all_events[d_roz].append({
                    "typ": "ROZŁADUNEK (PRO)", "nr": nr, 
                    "szczegoly": f"Projekt: {projekt} | Miejsce: {row.get('Miejsce Rozladunku', '')}", 
                    "kolor": "#83A5DB", "ikona": "🏁"
                })

    # 2. Analiza Zleceń Pobocznych
    if not df_poboczne.empty:
        for _, row in df_poboczne.iterrows():
            nr = row.get("Nr Zlecenia", "Brak NR")
            przewoznik = row.get("Przewoźnik", "Brak danych")
            
            # Weryfikacja czy to jest zlecenie wygenerowane z PRO
            is_pro_order = str(nr).startswith("CRG")
            
            # Załadunki Poboczne (pomijamy dla PRO)
            d_zal_p = normalize_date(row.get("Data Załadunku"))
            if d_zal_p and not is_pro_order:
                all_events[d_zal_p].append({
                    "typ": "ZAŁADUNEK (POBOCZNE)", "nr": nr, 
                    "szczegoly": f"Przewoźnik: {przewoznik} | Opis: {row.get('Opis Ładunku / Trasy', '')}", 
                    "kolor": "#AF8FC9", "ikona": "🟡"
                })
            
            # Rozładunki Poboczne (pomijamy dla PRO)
            d_roz_p = normalize_date(row.get("Data Rozładunku"))
            if d_roz_p and not is_pro_order:
                all_events[d_roz_p].append({
                    "typ": "ROZŁADUNEK (POBOCZNE)", "nr": nr, 
                    "szczegoly": f"Przewoźnik: {przewoznik} | Cel osiągnięty", 
                    "kolor": "#77A385", "ikona": "🚩"
                })
                
            # Terminy Płatności (ZOSTAWIAMY dla wszystkich, również dla PRO)
            d_plat_p = normalize_date(row.get("Data Płatności"))
            if d_plat_p:
                all_events[d_plat_p].append({
                    "typ": "TERMIN PŁATNOŚCI FAKTURY", "nr": nr, 
                    "szczegoly": f"Przewoźnik: {przewoznik} (Ostateczny dzień płatności)", 
                    "kolor": "#BA4949", "ikona": "💳"
                })

    # --- INTERFEJS KALENDARZA ---
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 10px;">
            <div>
                <h3 style='color: #E2DCD3; font-family: "Shippori Mincho", serif; margin: 0;'>🗓️ Interaktywny Radar</h3>
                <div style='color: #8C8477; font-size: 11px; letter-spacing: 1px;'>Zarządzaj przepływem operacji i płatnościami</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Wybór miesiąca i roku (Nowoczesny pasek nawigacyjny)
    c_m, c_y, c_btn, _ = st.columns([2, 2, 2, 4])
    
    nazwy_miesiecy = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"]
    
    with c_m:
        miesiac_nazwa = st.selectbox("Miesiąc", nazwy_miesiecy, index=st.session_state.cal_month - 1, label_visibility="collapsed")
        miesiac = nazwy_miesiecy.index(miesiac_nazwa) + 1
        st.session_state.cal_month = miesiac
    with c_y:
        rok = st.selectbox("Rok", [2025, 2026, 2027], index=[2025, 2026, 2027].index(st.session_state.cal_year), label_visibility="collapsed")
        st.session_state.cal_year = rok
    with c_btn:
        if st.button("📍 Wróć do dzisiaj", use_container_width=True):
            dzis = datetime.now()
            st.session_state.cal_month = dzis.month
            st.session_state.cal_year = dzis.year
            st.session_state.cal_selected_date = dzis.strftime("%Y-%m-%d")
            st.rerun()

    # Renderowanie siatki kalendarza w szklanym kontenerze
    with st.container():
        st.markdown("""
            <style>
            .cal-header {
                text-align: center;
                color: #C5A880;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2px;
                text-transform: uppercase;
                padding-bottom: 10px;
                border-bottom: 1px solid rgba(197, 168, 128, 0.2);
                margin-bottom: 15px;
            }
            .cal-empty {
                background: rgba(28, 26, 24, 0.3);
                border: 1px dashed rgba(197, 168, 128, 0.15);
                border-radius: 6px;
                min-height: 52px;
                margin-bottom: 15px;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='background: rgba(28, 26, 24, 0.6); border: 1px solid rgba(197, 168, 128, 0.2); border-radius: 12px; padding: 25px; backdrop-filter: blur(10px); margin-top: 5px;'>", unsafe_allow_html=True)
        
        cal = calendar.monthcalendar(rok, miesiac)
        dni_tyg = ["Pon", "Wto", "Śro", "Czw", "Pią", "Sob", "Nie"]
        
        cols = st.columns(7)
        for i, nazwa_dnia in enumerate(dni_tyg):
            cols[i].markdown(f"<div class='cal-header'>{nazwa_dnia}</div>", unsafe_allow_html=True)
            
        dzis_str = datetime.now().strftime("%Y-%m-%d")

        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    cols[i].markdown("<div class='cal-empty'></div>", unsafe_allow_html=True)
                else:
                    d_str = f"{rok}-{miesiac:02d}-{day:02d}"
                    lista_zdarzen = all_events.get(d_str, [])
                    liczba_zdarzen = len(lista_zdarzen)
                    
                    is_selected = (st.session_state.cal_selected_date == d_str)
                    btn_type = "primary" if is_selected else "secondary"
                    
                    # Generowanie estetycznych ikon zamiast zwykłego tekstu
                    ikonki = []
                    for ev in lista_zdarzen:
                        if "PŁATNOŚCI" in ev['typ'] and "💳" not in ikonki: ikonki.append("💳")
                        elif "PRO" in ev['typ'] and "📦" not in ikonki: ikonki.append("📦")
                        elif "POBOCZNE" in ev['typ'] and "🚚" not in ikonki: ikonki.append("🚚")
                    
                    ikony_str = " ".join(ikonki) if ikonki else "-"
                    
                    is_today = (d_str == dzis_str)
                    prefix = "📍 " if is_today else ""
                    
                    label = f"{prefix}{day}\n{ikony_str}"
                    
                    if cols[i].button(label, key=f"btn_{d_str}", use_container_width=True, type=btn_type):
                        st.session_state.cal_selected_date = d_str
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # --- SZCZEGÓŁY WYBRANEGO DNIA (ROZKŁAD JAZDY) ---
    wybrana_data_str = st.session_state.cal_selected_date
    zdarzenia_wybranego_dnia = all_events.get(wybrana_data_str, [])
    
    try:
        dt_obj = datetime.strptime(wybrana_data_str, "%Y-%m-%d")
        wyswietlana_data = f"{dt_obj.day} {nazwy_miesiecy[dt_obj.month - 1]} {dt_obj.year}"
    except:
        wyswietlana_data = wybrana_data_str

    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-top: 30px; margin-bottom: 15px;">
            <div style="width: 4px; height: 24px; background-color: #C5A880; border-radius: 2px;"></div>
            <h3 style='color: #E2DCD3; font-family: "Shippori Mincho", serif; margin: 0;'>Agenda logistyczna: <span style="color: #C5A880;">{wyswietlana_data}</span></h3>
        </div>
    """, unsafe_allow_html=True)

    if not zdarzenia_wybranego_dnia:
        st.info("Brak zaplanowanych operacji, załadunków i płatności na ten dzień.")
    else:
        for idx, ev in enumerate(zdarzenia_wybranego_dnia):
            c1, c2 = st.columns([5, 1])
            
            with c1:
                st.markdown(f"""
                <div class="custom-row" style="border-left: 3px solid {ev['kolor']}; margin-bottom: 8px;">
                    <div class="cr-col">
                        <div class="cr-title" style="color: {ev['kolor']}; font-size: 12px; margin-bottom: 2px;">
                            {ev['ikona']} <strong>{ev['typ']}</strong> | {ev['nr']}
                        </div>
                        <div class="cr-text" style="font-size: 13px; color: #E2DCD3;">
                            {ev['szczegoly']}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with c2:
                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                
                if st.button("Otwórz ➔", key=f"link_{wybrana_data_str}_{idx}_{ev['nr']}", use_container_width=True):
                    
                    st.session_state['przekierowanie_nr_zlecenia'] = ev['nr']
                    
                    if "PRO" in ev['typ']:
                        st.session_state['menu_option'] = "GENERATOR ZLECEŃ PRO" 
                    else:
                        st.session_state['menu_option'] = "ZLECENIA POBOCZNE"
                        
                    st.rerun()
