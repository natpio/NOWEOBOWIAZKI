import streamlit as st
import pandas as pd
from datetime import datetime, date, time
from streamlit_calendar import calendar
import db

def render(sh):
    # Nagłówek modułu
    st.markdown("""
        <div class="module-header-container">
            <h1 class="module-title">Rezerwacja Rampy</h1>
            <div class="module-subtitle">ドック予約 ✦ RAMP BOOKING CENTER</div>
        </div>
        <p style="color: #8C8477; font-size: 13px;">Zarządzaj rezerwacjami ramp 11-15. Przeciągnij i upuść bilet, aby błyskawicznie zmienić godzinę lub rampę.</p>
    """, unsafe_allow_html=True)

    # 1. ŁADOWANIE BAZY DANYCH (Inicjalizacja jeśli nie istnieje)
    worksheet_rampy, df_rampy = db.load_data(sh, "DB_Rampy")
    
    if df_rampy.empty and not worksheet_rampy.row_values(1):
        headers = ["ID_Rezerwacji", "Rampa", "Data", "Godzina_Od", "Godzina_Do", "Nazwa_Imprezy", "Pojazd", "Kierowca", "Faktyczny_Podjazd", "Notatki"]
        worksheet_rampy.append_row(headers)
        st.cache_data.clear()
        worksheet_rampy, df_rampy = db.load_data(sh, "DB_Rampy")

    # 2. PANEL GÓRNY - NAWIGACJA DATĄ
    col_date, col_view, col_add = st.columns([2, 3, 2], vertical_alignment="bottom")
    
    if "rampy_data" not in st.session_state:
        st.session_state["rampy_data"] = date.today()

    with col_date:
        wybrana_data = st.date_input("Wybierz dzień operacyjny:", value=st.session_state["rampy_data"])
        st.session_state["rampy_data"] = wybrana_data
        
    with col_view:
        if st.button("📍 Wróć do dzisiaj", use_container_width=True):
            st.session_state["rampy_data"] = date.today()
            st.rerun()

    st.markdown("<hr style='border-color: rgba(197, 168, 128, 0.1); margin: 15px 0;'>", unsafe_allow_html=True)

    # 3. PRZYGOTOWANIE DANYCH DO KALENDARZA
    events = []
    if not df_rampy.empty:
        # Filtrujemy tylko wybraną datę
        df_dzien = df_rampy[df_rampy['Data'] == str(wybrana_data)]
        
        for _, row in df_dzien.iterrows():
            podjazd = str(row.get('Faktyczny_Podjazd', '')).strip()
            status_podjazdu = f"✅ Podjechał: {podjazd}" if podjazd and podjazd not in ["nan", "None", ""] else "🕒 Oczekuje"
            
            # Formatowanie tekstu na bilecie
            tytul = f"{row.get('Nazwa_Imprezy', '')}\n🚛 {row.get('Pojazd', '')}\n👤 {row.get('Kierowca', '')}\n{status_podjazdu}"
            
            kolor_tla = "#F7F3EC" # Kremowe tło biletu
            kolor_ramki = "#10B981" if "✅" in status_podjazdu else "#BA4949" # Zielone boki jeśli podjechał, czerwone jeśli czeka
            
            events.append({
                "id": str(row.get('ID_Rezerwacji', '')),
                "resourceId": str(row.get('Rampa', '')),
                "start": f"{row['Data']}T{row.get('Godzina_Od', '00:00')}",
                "end": f"{row['Data']}T{row.get('Godzina_Do', '01:00')}",
                "title": tytul,
                "backgroundColor": kolor_tla,
                "borderColor": kolor_ramki,
                "textColor": "#050A15",
                "extendedProps": {
                    "impreza": str(row.get('Nazwa_Imprezy', '')),
                    "pojazd": str(row.get('Pojazd', '')),
                    "kierowca": str(row.get('Kierowca', '')),
                    "podjazd": podjazd,
                    "notatki": str(row.get('Notatki', ''))
                }
            })

    # Konfiguracja widoku siatki (Drag & Drop)
    calendar_options = {
        "initialView": "resourceTimeGridDay",
        "initialDate": str(wybrana_data),
        "resources": [
            {"id": "11", "title": "RAMPA 11"},
            {"id": "12", "title": "RAMPA 12"},
            {"id": "13", "title": "RAMPA 13"},
            {"id": "14", "title": "RAMPA 14"},
            {"id": "15", "title": "RAMPA 15"}
        ],
        "slotMinTime": "06:00:00",
        "slotMaxTime": "22:00:00",
        "slotDuration": "00:30:00",
        "allDaySlot": False,
        "editable": True,         # Pozwala na DRAG & DROP
        "droppable": True,
        "selectable": True,
        "headerToolbar": False,   # Wyłączamy pasek nawigacji kalendarza (mamy własny wyżej)
        "height": "auto"
    }

    # Wstrzyknięcie niestandardowego CSS dla biletów baseballowych wewnątrz kalendarza
    custom_css = """
        .fc-event {
            border-left: 4px dashed var(--fc-border-color) !important;
            border-right: 4px dashed var(--fc-border-color) !important;
            border-top: 1px solid rgba(0,0,0,0.1) !important;
            border-bottom: 1px solid rgba(0,0,0,0.1) !important;
            border-radius: 4px !important;
            box-shadow: 2px 4px 10px rgba(0,0,0,0.4) !important;
            padding: 4px !important;
            font-family: 'Inter', sans-serif !important;
            cursor: grab !important;
        }
        .fc-event-title {
            white-space: pre-wrap !important; /* Pozwala na entery w tytule (\n) */
            font-size: 11px !important;
            font-weight: 600 !important;
            line-height: 1.4 !important;
        }
        .fc-timegrid-slot-label { color: #C5A880 !important; font-weight: bold; }
        .fc-col-header-cell { 
            background: #0B1120 !important; 
            color: #E2DCD3 !important; 
            padding: 10px 0 !important;
            font-family: 'Bebas Neue', sans-serif !important;
            letter-spacing: 2px !important;
            font-size: 18px !important;
        }
        .fc-theme-standard td, .fc-theme-standard th { border-color: rgba(197, 168, 128, 0.15) !important; }
        .fc-timegrid-col { background: rgba(5, 10, 21, 0.4) !important; }
    """

    st.markdown('<div style="background: rgba(28, 26, 24, 0.85); padding: 10px; border-radius: 8px; border: 1px solid rgba(197, 168, 128, 0.2);">', unsafe_allow_html=True)
    
    # RENDEROWANIE KALENDARZA (Z nasłuchiwaniem zdarzeń)
    cal_state = calendar(events=events, options=calendar_options, custom_css=custom_css, key="rampy_calendar")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # 4. OBSŁUGA ZDARZEŃ DRAG & DROP
    if cal_state.get("eventChange"):
        zmieniony_event = cal_state["eventChange"]["event"]
        ev_id = zmieniony_event["id"]
        
        # Wyciąganie nowych danych po upuszczeniu
        nowa_rampa = zmieniony_event.get("resourceId", "")
        # Format stringa z JS: "2026-05-31T09:00:00Z"
        nowy_start = zmieniony_event["start"].split("T")
        nowy_end = zmieniony_event["end"].split("T")
        
        nowa_data = nowy_start[0]
        nowy_czas_od = nowy_start[1][:5] # Pobiera samo HH:MM
        nowy_czas_do = nowy_end[1][:5] if "end" in zmieniony_event else "23:59"
        
        # Zapisz do Google Sheets
        idx = df_rampy[df_rampy['ID_Rezerwacji'] == ev_id].index[0]
        df_rampy.at[idx, 'Rampa'] = nowa_rampa
        df_rampy.at[idx, 'Data'] = nowa_data
        df_rampy.at[idx, 'Godzina_Od'] = nowy_czas_od
        df_rampy.at[idx, 'Godzina_Do'] = nowy_czas_do
        
        gs_row = int(df_rampy.at[idx, 'sheet_row'])
        if db.update_single_row_safe("DB_Rampy", gs_row, df_rampy.loc[idx]):
            st.toast(f"✅ Rezerwacja przeniesiona na Rampę {nowa_rampa} ({nowy_czas_od} - {nowy_czas_do})")
            # Czyścimy stan kalendarza z sesji, żeby nie wpadał w pętlę i przeładowujemy
            st.session_state.pop("rampy_calendar", None) 
            time.sleep(0.5)
            st.rerun()

    # 5. EDYCJA I DODAWANIE (PANEL DOLNY)
    st.markdown("<hr style='border-color: rgba(197, 168, 128, 0.1); margin: 25px 0;'>", unsafe_allow_html=True)
    
    tab_dodaj, tab_edytuj = st.tabs(["➕ Utwórz Nową Rezerwację", "✏️ Edytuj / Zgłoś Podjazd"])
    
    with tab_dodaj:
        with st.form("form_add_rampa", clear_on_submit=True):
            st.markdown("<p style='color:#C5A880; font-weight:700; font-size: 14px;'>Nowe awizowanie dostawy/odbioru</p>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            nowa_data = c1.date_input("Data rezerwacji", value=wybrana_data)
            nowy_od = c2.time_input("Godzina Od")
            nowy_do = c3.time_input("Godzina Do")
            
            c4, c5 = st.columns([1, 3])
            nowa_rampa = c4.selectbox("Wybierz Rampę", ["11", "12", "13", "14", "15"])
            nowa_impreza = c5.text_input("Nazwa Imprezy / Cel", placeholder="np. GAMESCOM 2026")
            
            c6, c7 = st.columns(2)
            nowy_pojazd = c6.text_input("Dane pojazdu (Rejestracja / Typ)", placeholder="np. WGM 12345 / Volvo FH")
            nowy_kierowca = c7.text_input("Dane kierowcy (Imię / Telefon)")
            
            nowe_notatki = st.text_input("Notatki dodatkowe")
            
            if st.form_submit_button("💾 Dodaj Rezerwację Rampy", type="primary", use_container_width=True):
                if not nowa_impreza:
                    st.error("Podaj nazwę imprezy!")
                else:
                    new_id = f"RMP-{int(time.time())}"
                    nowy_wiersz = [
                        new_id, nowa_rampa, str(nowa_data), 
                        nowy_od.strftime("%H:%M"), nowy_do.strftime("%H:%M"),
                        nowa_impreza, nowy_pojazd, nowy_kierowca, "", nowe_notatki
                    ]
                    if db.append_data("DB_Rampy", nowy_wiersz):
                        st.success("Rezerwacja dodana pomyślnie!")
                        st.rerun()

    with tab_edytuj:
        if not df_dzien.empty:
            df_dzien['Label'] = df_dzien['Godzina_Od'] + " | Rampa " + df_dzien['Rampa'] + " | " + df_dzien['Nazwa_Imprezy']
            opcje_slownik = dict(zip(df_dzien['ID_Rezerwacji'], df_dzien['Label']))
            
            wybrane_id = st.selectbox("Wybierz rezerwację z dzisiaj do edycji:", options=list(opcje_slownik.keys()), format_func=lambda x: opcje_slownik[x])
            dane_rez = df_dzien[df_dzien['ID_Rezerwacji'] == wybrane_id].iloc[0]
            
            with st.form("form_edit_rampa"):
                st.markdown("<p style='color:#C5A880; font-weight:700; font-size: 14px;'>Szczegóły i Zgłoszenie Podjazdu</p>", unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                e_impreza = c1.text_input("Nazwa Imprezy", value=dane_rez.get('Nazwa_Imprezy', ''))
                
                podj_baza = str(dane_rez.get('Faktyczny_Podjazd', '')).strip()
                if podj_baza and podj_baza not in ["nan", "None"]:
                    try: val_podj = datetime.strptime(podj_baza, "%H:%M").time()
                    except: val_podj = None
                else: val_podj = None
                
                e_podjazd = c2.time_input("Faktyczny czas podjazdu pod rampę (Zostaw puste jeśli czeka)", value=val_podj)
                usun_podjazd = c2.checkbox("🗑️ Cofnij status podjazdu (Wyczyść czas)", value=(val_podj is None))
                
                c3, c4 = st.columns(2)
                e_pojazd = c3.text_input("Pojazd", value=dane_rez.get('Pojazd', ''))
                e_kierowca = c4.text_input("Kierowca", value=dane_rez.get('Kierowca', ''))
                
                c_zapisz, c_usun = st.columns([3, 1])
                if c_zapisz.form_submit_button("💾 Zapisz Zmiany", type="primary", use_container_width=True):
                    idx = df_rampy[df_rampy['ID_Rezerwacji'] == wybrane_id].index[0]
                    df_rampy.at[idx, 'Nazwa_Imprezy'] = e_impreza
                    df_rampy.at[idx, 'Pojazd'] = e_pojazd
                    df_rampy.at[idx, 'Kierowca'] = e_kierowca
                    df_rampy.at[idx, 'Faktyczny_Podjazd'] = "" if usun_podjazd else (e_podjazd.strftime("%H:%M") if e_podjazd else "")
                    
                    gs_row = int(df_rampy.at[idx, 'sheet_row'])
                    if db.update_single_row_safe("DB_Rampy", gs_row, df_rampy.loc[idx]):
                        st.success("Zaktualizowano dane rezerwacji!")
                        st.rerun()
                        
                if c_usun.form_submit_button("🗑️ Usuń Trwale", use_container_width=True):
                    gs_row = int(dane_rez['sheet_row'])
                    db.delete_row("DB_Rampy", gs_row)
                    st.error("Rezerwacja została usunięta z kalendarza.")
                    st.rerun()
        else:
            st.info("Brak rezerwacji w wybranym dniu do edycji.")
