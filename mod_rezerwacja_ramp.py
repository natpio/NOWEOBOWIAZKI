import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
from streamlit_calendar import calendar
import db

def render(sh):
    # ==========================================
    # 1. NAPRAWA WYDAJNOŚCI (LAG PODCZAS PISANIA) ORAZ STYLIZACJA 100% MOCKUP
    # ==========================================
    st.markdown("""
        <style>
        /* CRITICAL PERFORMANCE FIX: Usunięcie blur'a i wymuszenie akceleracji sprzętowej na polach tekstowych */
        div[data-testid="stTextInput"] input, 
        div[data-testid="stTextArea"] textarea, 
        div[data-testid="stNumberInput"] input {
            backdrop-filter: none !important;
            background-color: #0A1428 !important; 
            transform: translateZ(0) !important; 
            will-change: transform !important;
            border: 1px solid #1C2D4A !important;
        }
        
        /* Główne tło i usuwanie marginesów w kontenerach kalendarza */
        .fc { background-color: transparent !important; color: #E2DCD3; font-family: 'Inter', sans-serif; }
        
        /* Stylizacja nagłówków kolumn (RAMP A 11, itp.) */
        .fc-col-header-cell {
            background-color: #12100E !important;
            border-bottom: 2px solid rgba(197, 168, 128, 0.2) !important;
            font-family: 'Bebas Neue', sans-serif !important;
            font-size: 20px !important;
            letter-spacing: 2px !important;
            color: #E2DCD3 !important;
            padding: 12px 0 !important;
        }
        
        /* Stylizacja siatki godzinowej i tła */
        .fc-timegrid-slot { height: 50px !important; border-bottom: 1px dashed rgba(197, 168, 128, 0.1) !important; }
        .fc-timegrid-slot-label {
            font-size: 13px !important; color: #C5A880 !important; font-weight: 600 !important;
            border-right: 1px solid rgba(197, 168, 128, 0.1) !important;
            vertical-align: top !important; padding-top: 5px !important;
        }
        .fc-theme-standard td, .fc-theme-standard th { border-right: 1px solid rgba(197, 168, 128, 0.1) !important; }
        
        /* Całkowite wyczyszczenie domyślnych stylów FullCalendar dla zdarzeń */
        .fc-event {
            background: transparent !important;
            border: none !important;
            padding: 2px 6px !important; /* Daje miejsce na cień biletu */
            cursor: grab !important;
        }
        .fc-event:active { cursor: grabbing !important; }
        .fc-event-main { padding: 0 !important; height: 100% !important; }
        
        /* Legenda poniżej kalendarza */
        .legend-container {
            display: flex; gap: 20px; align-items: center; margin: 15px 0 30px 0;
            font-size: 13px; color: #A39B8F; font-weight: 600;
        }
        .legend-item { display: flex; align-items: center; gap: 8px; }
        .l-box { width: 14px; height: 14px; border-radius: 3px; }
        .l-yellow { background-color: #C5A880; }
        .l-green { background-color: #10B981; }
        .l-blue { background-color: #3B82F6; }
        .l-gray { background-color: #718096; }
        
        /* Pasek górny (Top Bar) */
        .top-bar-btn button {
            background-color: #12100E !important; border: 1px solid rgba(197, 168, 128, 0.3) !important;
            color: #C5A880 !important; font-weight: bold !important; font-family: 'Bebas Neue', sans-serif !important; letter-spacing: 1px !important;
        }
        .top-bar-btn button:hover { background-color: #1C1A18 !important; color: #FDFBF7 !important; border-color: #C5A880 !important; }
        </style>
    """, unsafe_allow_html=True)

    # Nagłówek modułu
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
            <div style="font-size: 40px;">📅</div>
            <div>
                <h1 style="color: #FDFBF7; margin: 0; font-size: 32px; font-weight: 800; font-family: 'Bebas Neue', sans-serif; letter-spacing: 2px;">REZERWACJA RAMPY</h1>
                <div style="color: #A39B8F; font-size: 13px;">Zarządzaj rezerwacjami ramp – przeciągaj i upuszczaj, aby zmienić czas lub rampę</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # 2. BAZA DANYCH
    # ==========================================
    worksheet_rampy, df_rampy = db.load_data(sh, "DB_Rampy")
    
    if worksheet_rampy is None:
        st.warning("⚠️ Zbyt wiele zapytań do Google Sheets. Odczekaj chwilę i odśwież.")
        return

    # Jeśli baza jest pusta, inicjalizujemy ją nowym zestawem kolumn z mockupu
    if df_rampy.empty and len(df_rampy.columns) <= 1:
        headers = [
            "ID_Rezerwacji", "Rampa", "Data", "Godzina_Od", "Godzina_Do", 
            "Nazwa_Imprezy", "Pojazd", "Kierowca", "Telefon", "Email", 
            "Naczepa", "Typ_Naczepy", "Faktyczny_Podjazd", "Trwa_Zaladunek", "Zakonczono", "Notatki"
        ]
        worksheet_rampy.append_row(headers)
        st.cache_data.clear()
        worksheet_rampy, df_rampy = db.load_data(sh, "DB_Rampy")

    # Ustawienie stanu sesji do kontroli interfejsu
    if "rampy_data" not in st.session_state: st.session_state.rampy_data = date.today()
    if "wybrana_rezerwacja" not in st.session_state: st.session_state.wybrana_rezerwacja = None
    if "pokaz_formularz" not in st.session_state: st.session_state.pokaz_formularz = None

    # ==========================================
    # 3. GÓRNY PASEK NAWIGACYJNY (100% Mockup)
    # ==========================================
    st.markdown('<div class="top-bar-btn">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6, c7 = st.columns([0.5, 2, 0.5, 1.2, 2, 3.5, 2], vertical_alignment="center")
    
    with c1:
        if st.button("❮", use_container_width=True): st.session_state.rampy_data -= timedelta(days=1); st.rerun()
    with c2:
        nowa_data = st.date_input("Data", value=st.session_state.rampy_data, label_visibility="collapsed")
        if nowa_data != st.session_state.rampy_data: st.session_state.rampy_data = nowa_data; st.rerun()
    with c3:
        if st.button("❯", use_container_width=True): st.session_state.rampy_data += timedelta(days=1); st.rerun()
    with c4:
        if st.button("DZIŚ", use_container_width=True): st.session_state.rampy_data = date.today(); st.rerun()
    with c5:
        pokaz_moje = st.toggle("POKAŻ TYLKO MOJE")
    with c6:
        # Formularz wyszukiwania zablokuje niepotrzebne przeładowywanie co literę!
        with st.form("search_form", border=False):
            sc1, sc2 = st.columns([5, 1])
            szukana_fraza = sc1.text_input("Szukaj", placeholder="🔍 Szukaj rezerwacji, auta, kierowcy...", label_visibility="collapsed")
            sc2.form_submit_button("Szukaj")
    with c7:
        st.markdown('</div>', unsafe_allow_html=True) # Zamykamy klasę szarych przycisków przed czerwonym
        if st.button("➕ NOWA REZERWACJA", type="primary", use_container_width=True):
            st.session_state.pokaz_formularz = "NOWA"
            st.session_state.wybrana_rezerwacja = None
            st.rerun()

    # ==========================================
    # 4. SILNIK KALENDARZA I WIZUALIZACJA
    # ==========================================
    events = []
    if not df_rampy.empty:
        df_dzien = df_rampy[df_rampy['Data'] == str(st.session_state.rampy_data)]
        
        if szukana_fraza:
            mask = df_dzien.astype(str).apply(lambda row: row.str.contains(szukana_fraza, case=False, na=False).any(), axis=1)
            df_dzien = df_dzien[mask]

        for _, row in df_dzien.iterrows():
            podjazd = str(row.get('Faktyczny_Podjazd', '')).strip()
            trwa_zaladunek = str(row.get('Trwa_Zaladunek', '')).strip().upper() == "TAK"
            zakonczono = str(row.get('Zakonczono', '')).strip().upper() == "TAK"
            
            events.append({
                "id": str(row.get('ID_Rezerwacji', '')),
                "resourceId": str(row.get('Rampa', '')),
                "start": f"{row['Data']}T{row.get('Godzina_Od', '00:00')}:00",
                "end": f"{row['Data']}T{row.get('Godzina_Do', '01:00')}:00",
                "title": str(row.get('Nazwa_Imprezy', '')),
                "extendedProps": {
                    "pojazd": str(row.get('Pojazd', '')),
                    "kierowca": str(row.get('Kierowca', '')),
                    "podjazd": podjazd,
                    "trwa_zaladunek": "TAK" if trwa_zaladunek else "NIE",
                    "zakonczono": "TAK" if zakonczono else "NIE"
                }
            })

    # Konfiguracja struktury siatki
    calendar_options = {
        "initialView": "resourceTimeGridDay",
        "initialDate": str(st.session_state.rampy_data),
        "resources": [
            {"id": "11", "title": "RAMP A  11"},
            {"id": "12", "title": "RAMP A  12"},
            {"id": "13", "title": "RAMP A  13"},
            {"id": "14", "title": "RAMP A  14"},
            {"id": "15", "title": "RAMP A  15"}
        ],
        "slotMinTime": "07:00:00",
        "slotMaxTime": "19:00:00",
        "slotDuration": "00:30:00",
        "allDaySlot": False,
        "editable": True,         # Włącza DRAG & DROP!
        "droppable": True,
        "selectable": True,
        "headerToolbar": False,   # Ukrywamy brzydki pasek nawigacji
        "height": "auto",
        "slotLabelFormat": { "hour": "2-digit", "minute": "2-digit", "hour12": False }
    }

    # JAVASCRIPT: Magiczny generator biletów. Tworzy idealne "Dashed borders" wg makiety!
    js_event_content = """function(arg) {
        let props = arg.event.extendedProps;
        let podjazd = props.podjazd;
        let isZaladunek = props.trwa_zaladunek === 'TAK';
        let isDone = props.zakonczono === 'TAK';
        
        let statusHtml = '';
        let borderColor = '#C5A880'; // Żółty - Planowana rezerwacja
        
        if (isDone) {
            borderColor = '#718096'; // Szary - Zakończono
            statusHtml = `<div style='color: #718096; font-size: 11px; margin-top: 4px;'><span style='margin-right: 4px;'>⬛</span> Zakończono</div>`;
        } else if (isZaladunek) {
            borderColor = '#3B82F6'; // Niebieski - Trwa załadunek
            statusHtml = `<div style='color: #3B82F6; font-size: 11px; margin-top: 4px;'><span style='margin-right: 4px;'>⏳</span> Trwa załadunek...</div>`;
        } else if (podjazd && podjazd !== 'nan' && podjazd !== 'None' && podjazd !== '') {
            borderColor = '#10B981'; // Zielony - Podjechał pod rampę
            statusHtml = `<div style='color: #10B981; font-size: 11px; margin-top: 4px;'><span style='margin-right: 4px;'>✔</span> Podjechał: ${podjazd}</div>`;
        } else {
            statusHtml = `<div style='color: #A0AEC0; font-size: 11px; margin-top: 4px;'><span style='margin-right: 4px;'>🕒</span> Podjechał: –</div>`;
        }

        let html = `
            <div style='height: 100%; width: 100%; background-color: #FDFBF7; border-left: 5px dashed ${borderColor}; border-right: 5px dashed ${borderColor}; box-sizing: border-box; padding: 6px 10px; display: flex; flex-direction: column; justify-content: space-between; color: #1A2530; font-family: "Inter", sans-serif; box-shadow: inset 0px 0px 5px rgba(0,0,0,0.05);'>
                <div>
                    <div style='font-size: 10px; color: #718096; margin-bottom: 2px; font-weight: 600;'>${arg.timeText}</div>
                    <div style='font-size: 13px; font-weight: 800; color: #050A15; text-transform: uppercase; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>${arg.event.title}</div>
                    <div style='font-size: 11px; color: #4A5568; margin-bottom: 1px;'>${props.pojazd}</div>
                    <div style='font-size: 11px; color: #4A5568;'>${props.kierowca}</div>
                </div>
                ${statusHtml}
            </div>
        `;
        return { html: html };
    }"""

    # Tło pod kalendarz
    st.markdown('<div style="background: rgba(18, 16, 14, 0.9); padding: 15px; border-radius: 8px; border: 1px solid rgba(197, 168, 128, 0.2); margin-top: 15px;">', unsafe_allow_html=True)
    
    cal_state = calendar(
        events=events, 
        options=calendar_options, 
        callbacks={"eventContent": js_event_content},
        key="rampy_calendar_comp"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Legenda pod kalendarzem (100% Mockup)
    st.markdown("""
        <div class="legend-container">
            <div class="legend-item"><div class="l-box l-yellow"></div> Planowana rezerwacja</div>
            <div class="legend-item"><div class="l-box l-green"></div> Podjechał pod rampę</div>
            <div class="legend-item"><div class="l-box l-blue"></div> Trwa załadunek</div>
            <div class="legend-item"><div class="l-box l-gray"></div> Zakończono</div>
        </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # 5. OBSŁUGA ZDARZEŃ Z KALENDARZA
    # ==========================================
    
    # Przesunięcie myszką (Drag & Drop)
    if cal_state.get("eventChange"):
        zmieniony = cal_state["eventChange"]["event"]
        ev_id = zmieniony["id"]
        nowa_rampa = zmieniony.get("resourceId", "")
        
        try:
            start_dt = datetime.fromisoformat(zmieniony["start"].replace("Z", "+00:00"))
            nowa_data = start_dt.strftime("%Y-%m-%d")
            nowy_od = start_dt.strftime("%H:%M")
            
            if "end" in zmieniony and zmieniony["end"]:
                end_dt = datetime.fromisoformat(zmieniony["end"].replace("Z", "+00:00"))
                nowy_do = end_dt.strftime("%H:%M")
            else: nowy_do = ""
            
            # Zapisz zmianę bezpośrednio do bazy
            idx = df_rampy[df_rampy['ID_Rezerwacji'] == ev_id].index[0]
            df_rampy.at[idx, 'Rampa'] = nowa_rampa
            df_rampy.at[idx, 'Data'] = nowa_data
            df_rampy.at[idx, 'Godzina_Od'] = nowy_od
            df_rampy.at[idx, 'Godzina_Do'] = nowy_do
            gs_row = int(df_rampy.at[idx, 'sheet_row'])
            db.update_single_row_safe("DB_Rampy", gs_row, df_rampy.loc[idx])
            
            # Czyścimy bufor, by zmiana załadowała się poprawnie
            st.session_state.pop("rampy_calendar_comp", None)
            st.toast(f"✅ Przypisano do Rampy {nowa_rampa} ({nowy_od} - {nowy_do})")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd przesunięcia: {e}")

    # Kliknięcie w bilet
    if cal_state.get("eventClick"):
        klikniete_id = cal_state["eventClick"]["event"]["id"]
        # Aktualizujemy stan i robimy rerun by wyświetlić panel na dole
        if st.session_state.wybrana_rezerwacja != klikniete_id:
            st.session_state.wybrana_rezerwacja = klikniete_id
            st.session_state.pokaz_formularz = None
            st.session_state.pop("rampy_calendar_comp", None)
            st.rerun()

    # ==========================================
    # 6. KREMOWY PANEL SZCZEGÓŁÓW (Wzorowany 1:1 na grafice)
    # ==========================================
    if st.session_state.get("wybrana_rezerwacja") and st.session_state.get("pokaz_formularz") != "NOWA":
        rez_id = st.session_state.wybrana_rezerwacja
        # Pobieramy najświeższe dane z df (odświeżanego regularnie przez Streamlit)
        try:
            row = df_rampy[df_rampy['ID_Rezerwacji'] == rez_id].iloc[0]
            
            html_panel = f"""
            <div style="background-color: #FDFBF7; border: 1px dashed #C5A880; border-radius: 8px; padding: 25px; color: #1A2530; display: flex; flex-direction: row; gap: 20px; box-shadow: 0px 10px 25px rgba(0,0,0,0.5);">
                <div style="flex: 2.5;">
                    <h2 style="color: #050A15; margin: 0; font-size: 28px; font-weight: 800;">{row.get('Nazwa_Imprezy', '-')}</h2>
                    <h4 style="color: #8B2635; margin: 5px 0 20px 0; font-family: 'Bebas Neue', sans-serif; letter-spacing: 1.5px;">RAMP A  {row.get('Rampa', '-')}</h4>
                    <div style="display: flex; gap: 40px;">
                        <div>
                            <div style="font-family: 'Bebas Neue', sans-serif; color: #8C8477; font-size: 14px; letter-spacing: 1px;">PLANOWANA REZERWACJA</div>
                            <div style="font-weight: 600; color: #050A15; margin-top: 5px;">📅 {row.get('Data', '-')}</div>
                            <div style="font-weight: 600; color: #050A15; margin-top: 2px;">🕒 {row.get('Godzina_Od', '-')} - {row.get('Godzina_Do', '-')}</div>
                        </div>
                        <div>
                            <div style="font-family: 'Bebas Neue', sans-serif; color: #8C8477; font-size: 14px; letter-spacing: 1px;">PODJECHAŁ POD RAMPĘ</div>
                            <div style="font-weight: 600; color: #10B981; margin-top: 5px;">📅 {row.get('Data', '-')}</div>
                            <div style="font-weight: 600; color: #10B981; margin-top: 2px;">🕒 {row.get('Faktyczny_Podjazd', '–') if str(row.get('Faktyczny_Podjazd', '')).strip() not in ['', 'nan', 'None'] else '–'}</div>
                        </div>
                    </div>
                </div>
                <div style="flex: 2; border-left: 1px solid rgba(0,0,0,0.1); padding-left: 20px;">
                    <div style="font-family: 'Bebas Neue', sans-serif; color: #8C8477; font-size: 14px; margin-bottom: 10px; letter-spacing: 1px;">🚛 DANE AUTA</div>
                    <table style="width: 100%; font-size: 13px;">
                        <tr><td style="color: #4A5568; padding-bottom: 8px; width: 45%;">REJESTRACJA</td><td style="font-weight: 600; color: #050A15; padding-bottom: 8px;">{str(row.get('Pojazd', '')).split('/')[0].strip() if '/' in str(row.get('Pojazd', '')) else str(row.get('Pojazd', '-'))}</td></tr>
                        <tr><td style="color: #4A5568; padding-bottom: 8px;">TYP</td><td style="font-weight: 600; color: #050A15; padding-bottom: 8px;">{str(row.get('Pojazd', '')).split('/')[1].strip() if '/' in str(row.get('Pojazd', '')) else '-'}</td></tr>
                        <tr><td style="color: #4A5568; padding-bottom: 8px;">NACZEPA</td><td style="font-weight: 600; color: #050A15; padding-bottom: 8px;">{row.get('Naczepa', '-')}</td></tr>
                        <tr><td style="color: #4A5568;">TYP NACZEPY</td><td style="font-weight: 600; color: #050A15;">{row.get('Typ_Naczepy', '-')}</td></tr>
                    </table>
                </div>
                <div style="flex: 2; border-left: 1px solid rgba(0,0,0,0.1); padding-left: 20px;">
                    <div style="font-family: 'Bebas Neue', sans-serif; color: #8C8477; font-size: 14px; margin-bottom: 10px; letter-spacing: 1px;">👤 DANE KIEROWCY</div>
                    <div style="color: #4A5568; font-size: 10px;">IMIĘ I NAZWISKO</div>
                    <div style="font-weight: 800; color: #050A15; font-size: 14px; margin-bottom: 10px;">{row.get('Kierowca', '-')}</div>
                    <div style="color: #4A5568; font-size: 10px;">TELEFON</div>
                    <div style="font-weight: 600; color: #050A15; font-size: 14px; margin-bottom: 10px;">{row.get('Telefon', '-')}</div>
                    <div style="color: #4A5568; font-size: 10px;">E-MAIL</div>
                    <div style="font-weight: 600; color: #050A15; font-size: 14px;">{row.get('Email', '-')}</div>
                </div>
            </div>
            """
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_info, col_btn = st.columns([8.5, 1.5])
            with col_info:
                st.markdown(html_content, unsafe_allow_html=True)
                
                c_text, c_close = st.columns([8, 2])
                c_text.markdown("<p style='color: #8C8477; font-size: 12px; margin-top: 15px; text-align: center;'>⤢ Przeciągnij rezerwację w kalendarzu, aby zmienić godzinę lub rampę</p>", unsafe_allow_html=True)
                if c_close.button("✖ ZAMKNIJ", use_container_width=True):
                    st.session_state.wybrana_rezerwacja = None
                    st.rerun()
                    
            with col_btn:
                st.markdown("<div style='font-family: \"Bebas Neue\", sans-serif; color: #C5A880; font-size: 16px; margin-bottom: 10px; text-align: center; letter-spacing: 2px;'>AKCJE</div>", unsafe_allow_html=True)
                if st.button("✏️ EDYTUJ", use_container_width=True): 
                    st.session_state.pokaz_formularz = "EDYCJA"
                    st.rerun()
                if st.button("🗑️ USUŃ", use_container_width=True):
                    gs_row = int(row['sheet_row'])
                    db.delete_row("DB_Rampy", gs_row)
                    st.session_state.wybrana_rezerwacja = None
                    st.success("Rezerwacja trwale usunięta!")
                    st.rerun()

        except Exception as e:
            st.error(f"Błąd ładowania szczegółów: {e}")

    # ==========================================
    # 7. FORMULARZ (DODAJ / EDYTUJ)
    # ==========================================
    if st.session_state.get("pokaz_formularz") in ["NOWA", "EDYCJA"]:
        st.markdown("<hr style='border-color: rgba(197, 168, 128, 0.1); margin: 20px 0;'>", unsafe_allow_html=True)
        tytul = "➕ Nowa Rezerwacja" if st.session_state.pokaz_formularz == "NOWA" else "✏️ Edycja Rezerwacji"
        st.markdown(f"<h3 style='color: #C5A880; font-family: \"Shippori Mincho\", serif;'>{tytul}</h3>", unsafe_allow_html=True)
        
        # Pobieranie istniejących danych jeśli edycja
        dane_edycja = {}
        if st.session_state.pokaz_formularz == "EDYCJA" and st.session_state.wybrana_rezerwacja:
            dane_edycja = df_rampy[df_rampy['ID_Rezerwacji'] == st.session_state.wybrana_rezerwacja].iloc[0].to_dict()

        with st.form("form_rampy", clear_on_submit=True):
            fc1, fc2, fc3 = st.columns([1, 1, 1])
            with fc1:
                f_impreza = st.text_input("Nazwa Imprezy *", value=dane_edycja.get('Nazwa_Imprezy', ''))
                f_rampa = st.selectbox("Rampa", ["11", "12", "13", "14", "15"], index=["11", "12", "13", "14", "15"].index(dane_edycja.get('Rampa', '11')) if dane_edycja.get('Rampa') in ["11", "12", "13", "14", "15"] else 0)
                
                dt_str = str(dane_edycja.get('Data', st.session_state.rampy_data))
                f_data = st.date_input("Data rezerwacji", value=datetime.strptime(dt_str, "%Y-%m-%d").date() if dt_str else st.session_state.rampy_data)
                
                od_str = str(dane_edycja.get('Godzina_Od', '08:00')).strip()
                f_od = st.time_input("Godzina Od", value=datetime.strptime(od_str, "%H:%M").time() if od_str and od_str not in ["nan", "None"] else datetime.strptime("08:00", "%H:%M").time())
                
                do_str = str(dane_edycja.get('Godzina_Do', '10:00')).strip()
                f_do = st.time_input("Godzina Do", value=datetime.strptime(do_str, "%H:%M").time() if do_str and do_str not in ["nan", "None"] else datetime.strptime("10:00", "%H:%M").time())
                
            with fc2:
                f_pojazd = st.text_input("Pojazd (Rejestracja / Typ)", value=dane_edycja.get('Pojazd', ''))
                f_naczepa = st.text_input("Rejestracja Naczepy", value=dane_edycja.get('Naczepa', ''))
                f_typ_naczepy = st.text_input("Typ Naczepy", value=dane_edycja.get('Typ_Naczepy', ''))
                f_kierowca = st.text_input("Imię i Nazwisko Kierowcy", value=dane_edycja.get('Kierowca', ''))
                f_tel = st.text_input("Telefon Kierowcy", value=dane_edycja.get('Telefon', ''))
                f_email = st.text_input("E-mail", value=dane_edycja.get('Email', ''))
                
            with fc3:
                st.markdown("<div style='background: rgba(10, 20, 40, 0.5); padding: 15px; border-radius: 8px; border: 1px solid #1C2D4A;'>", unsafe_allow_html=True)
                st.markdown("<p style='color: #8C8477; font-weight: bold; margin-bottom: 5px;'>Status Operacji na Rampie</p>", unsafe_allow_html=True)
                
                podj_baza = str(dane_edycja.get('Faktyczny_Podjazd', '')).strip()
                val_podj = datetime.strptime(podj_baza, "%H:%M").time() if podj_baza and podj_baza not in ["nan", "None"] else None
                f_podjazd = st.time_input("Kiedy podjechał? (Zostaw puste = czeka)", value=val_podj)
                usun_podjazd = st.checkbox("Wyczyść datę podjazdu (Cofnij)")
                
                f_trwa = st.selectbox("Czy trwa załadunek/rozładunek?", ["NIE", "TAK"], index=1 if str(dane_edycja.get('Trwa_Zaladunek', 'NIE')).upper() == "TAK" else 0)
                f_koniec = st.selectbox("Czy zakończono całkowicie?", ["NIE", "TAK"], index=1 if str(dane_edycja.get('Zakonczono', 'NIE')).upper() == "TAK" else 0)
                st.markdown("</div>", unsafe_allow_html=True)
                
                f_notatki = st.text_area("Dodatkowe notatki", value=dane_edycja.get('Notatki', ''))
            
            sc1, sc2 = st.columns([1, 1])
            if sc1.form_submit_button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                if not f_impreza:
                    st.error("Nazwa Imprezy jest obowiązkowa!")
                else:
                    final_podjazd = "" if usun_podjazd else (f_podjazd.strftime("%H:%M") if f_podjazd else "")
                    
                    if st.session_state.pokaz_formularz == "NOWA":
                        new_id = f"RMP-{int(time.time())}"
                        nowy_wiersz = [
                            new_id, f_rampa, str(f_data), f_od.strftime("%H:%M"), f_do.strftime("%H:%M"),
                            f_impreza, f_pojazd, f_kierowca, f_tel, f_email,
                            f_naczepa, f_typ_naczepy, final_podjazd, f_trwa, f_koniec, f_notatki
                        ]
                        db.append_data("DB_Rampy", nowy_wiersz)
                        st.success("Rezerwacja dodana pomyślnie!")
                    else:
                        idx = df_rampy[df_rampy['ID_Rezerwacji'] == st.session_state.wybrana_rezerwacja].index[0]
                        df_rampy.at[idx, 'Rampa'] = f_rampa
                        df_rampy.at[idx, 'Data'] = str(f_data)
                        df_rampy.at[idx, 'Godzina_Od'] = f_od.strftime("%H:%M")
                        df_rampy.at[idx, 'Godzina_Do'] = f_do.strftime("%H:%M")
                        df_rampy.at[idx, 'Nazwa_Imprezy'] = f_impreza
                        df_rampy.at[idx, 'Pojazd'] = f_pojazd
                        df_rampy.at[idx, 'Kierowca'] = f_kierowca
                        df_rampy.at[idx, 'Telefon'] = f_tel
                        df_rampy.at[idx, 'Email'] = f_email
                        df_rampy.at[idx, 'Naczepa'] = f_naczepa
                        df_rampy.at[idx, 'Typ_Naczepy'] = f_typ_naczepy
                        df_rampy.at[idx, 'Faktyczny_Podjazd'] = final_podjazd
                        df_rampy.at[idx, 'Trwa_Zaladunek'] = f_trwa
                        df_rampy.at[idx, 'Zakonczono'] = f_koniec
                        df_rampy.at[idx, 'Notatki'] = f_notatki
                        
                        gs_row = int(df_rampy.at[idx, 'sheet_row'])
                        db.update_single_row_safe("DB_Rampy", gs_row, df_rampy.loc[idx])
                        st.success("Zaktualizowano dane rezerwacji!")

                    st.session_state.pokaz_formularz = None
                    st.session_state.pop("rampy_calendar_comp", None)
                    st.rerun()
            if sc2.form_submit_button("✖ ANULUJ", use_container_width=True):
                st.session_state.pokaz_formularz = None
                st.rerun()
