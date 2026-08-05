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
    # Słownik w formacie: {'YYYY-MM-DD': [lista_zdarzen]}
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
            
            # Załadunki Poboczne
            d_zal_p = normalize_date(row.get("Data Załadunku"))
            if d_zal_p:
                all_events[d_zal_p].append({
                    "typ": "ZAŁADUNEK (POBOCZNE)", "nr": nr, 
                    "szczegoly": f"Przewoźnik: {przewoznik} | Opis: {row.get('Opis Ładunku / Trasy', '')}", 
                    "kolor": "#AF8FC9", "ikona": "🟡"
                })
            
            # Rozładunki Poboczne
            d_roz_p = normalize_date(row.get("Data Rozładunku"))
            if d_roz_p:
                all_events[d_roz_p].append({
                    "typ": "ROZŁADUNEK (POBOCZNE)", "nr": nr, 
                    "szczegoly": f"Przewoźnik: {przewoznik} | Cel osiągnięty", 
                    "kolor": "#77A385", "ikona": "🚩"
                })
                
            # Terminy Płatności
            d_plat_p = normalize_date(row.get("Data Płatności"))
            if d_plat_p:
                all_events[d_plat_p].append({
                    "typ": "TERMIN PŁATNOŚCI FAKTURY", "nr": nr, 
                    "szczegoly": f"Przewoźnik: {przewoznik} (Ostateczny dzień płatności)", 
                    "kolor": "#BA4949", "ikona": "💳"
                })

    # --- INTERFEJS KALENDARZA ---
    st.markdown("<p style='color: #C5A880; font-weight: 700; margin-bottom: 10px; text-transform: uppercase;'>🗓️ Interaktywny Kalendarz Operacyjny</p>", unsafe_allow_html=True)
    
    # Wybór miesiąca i roku
    c_m, c_y, _ = st.columns([1, 1, 3])
    with c_m:
        miesiac = st.selectbox("Miesiąc", range(1, 13), index=st.session_state.cal_month - 1)
        st.session_state.cal_month = miesiac
    with c_y:
        rok = st.selectbox("Rok", [2025, 2026, 2027], index=[2025, 2026, 2027].index(st.session_state.cal_year))
        st.session_state.cal_year = rok

    # Renderowanie siatki kalendarza
    with st.container(border=True):
        cal = calendar.monthcalendar(rok, miesiac)
        dni_tyg = ["PONIEDZIAŁEK", "WTOREK", "ŚRODA", "CZWARTEK", "PIĄTEK", "SOBOTA", "NIEDZIELA"]
        
        # Nagłówki dni
        cols = st.columns(7)
        for i, nazwa_dnia in enumerate(dni_tyg):
            cols[i].markdown(f"<div style='text-align: center; color: #8C8477; font-size: 10px; font-weight: bold;'>{nazwa_dnia}</div>", unsafe_allow_html=True)
            
        st.markdown("<hr style='margin: 10px 0; border-color: rgba(197, 168, 128, 0.1);'>", unsafe_allow_html=True)

        # Generowanie przycisków dni
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    cols[i].markdown("<div style='min-height: 40px;'></div>", unsafe_allow_html=True)
                else:
                    d_str = f"{rok}-{miesiac:02d}-{day:02d}"
                    lista_zdarzen = all_events.get(d_str, [])
                    liczba_zdarzen = len(lista_zdarzen)
                    
                    # Wizualne wskazanie wybranego dnia
                    is_selected = (st.session_state.cal_selected_date == d_str)
                    btn_type = "primary" if is_selected else "secondary"
                    
                    # Formaty etykiety w zależności od ilości zdarzeń
                    if liczba_zdarzen > 0:
                        label = f"{day} \n 🔥 [{liczba_zdarzen}]"
                    else:
                        label = f"{day}"
                    
                    # Kliknięcie w dzień aktualizuje stan i przeładowuje widok
                    if cols[i].button(label, key=f"btn_{d_str}", use_container_width=True, type=btn_type):
                        st.session_state.cal_selected_date = d_str
                        st.rerun()

    # --- SZCZEGÓŁY WYBRANEGO DNIA (ROZKŁAD JAZDY) ---
    wybrana_data_str = st.session_state.cal_selected_date
    zdarzenia_wybranego_dnia = all_events.get(wybrana_data_str, [])
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif;'>🔎 Rozkład na dzień: {wybrana_data_str}</h3>", unsafe_allow_html=True)

    if not zdarzenia_wybranego_dnia:
        st.info("Brak zaplanowanych operacji, załadunków i płatności na ten dzień.")
    else:
        for ev in zdarzenia_wybranego_dnia:
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
