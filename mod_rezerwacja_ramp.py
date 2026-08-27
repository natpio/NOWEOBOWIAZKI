import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
from streamlit_calendar import calendar
import db

def render(sh):
    # ==========================================
    # 1. NAPRAWA WYDAJNOŚCI I CSS 100% ZGODNY Z MOCKUPEM
    # ==========================================
    st.markdown("""
        <style>
        /* NAPRAWA WYDAJNOŚCI (ZERO LAGÓW) */
        div[data-testid="stTextInput"] input, 
        div[data-testid="stTextArea"] textarea, 
        div[data-testid="stNumberInput"] input,
        .stSelectbox div {
            transition: none !important;
            animation: none !important;
            backdrop-filter: none !important;
            background-color: #0A1428 !important; 
            transform: translateZ(0) !important; 
            border: 1px solid #1C2D4A !important;
            color: #FDFBF7 !important;
        }

        /* Pasek górny (Top Bar) */
        .top-bar-btn button {
            background-color: #12100E !important; border: 1px solid rgba(197, 168, 128, 0.3) !important;
            color: #C5A880 !important; font-weight: bold !important; font-family: 'Bebas Neue', sans-serif !important; letter-spacing: 1px !important;
            transition: none !important;
        }
        .top-bar-btn button:hover { background-color: #1C1A18 !important; color: #FDFBF7 !important; border-color: #C5A880 !important; }
        
        .btn-action-primary button { background-color: #8B2635 !important; border: 1px solid #BA4949 !important; color: #FDFBF7 !important; }
        .btn-action-primary button:hover { background-color: #BA4949 !important; border-color: #FDFBF7 !important; }
        
        .btn-action-auto button { background-color: rgba(197, 168, 128, 0.15) !important; border: 1px solid #C5A880 !important; color: #C5A880 !important; }
        .btn-action-auto button:hover { background-color: #C5A880 !important; color: #12100E !important; }

        /* Legenda */
        .legend-container {
            display: flex; gap: 20px; align-items: center; margin: 15px 0 20px 0;
            font-size: 12px; color: #A39B8F; font-weight: 600;
        }
        .legend-item { display: flex; align-items: center; gap: 8px; }
        .l-box { width: 12px; height: 12px; border-radius: 2px; }
        .l-yellow { background-color: #F7E8D0; }
        .l-green { background-color: #10B981; }
        .l-blue { background-color: #3B82F6; }
        .l-gray { background-color: #718096; }
        </style>
    """.replace('\n', ''), unsafe_allow_html=True)

    # Nagłówek wizualny
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px;">
            <div style="font-size: 42px;">📅</div>
            <div>
                <h1 style="color: #FDFBF7; margin: 0; font-size: 34px; font-weight: 800; font-family: 'Bebas Neue', sans-serif; letter-spacing: 2px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">REZERWACJA RAMPY</h1>
                <div style="color: #A39B8F; font-size: 13px;">Zarządzaj rezerwacjami ramp – przeciągaj i upuszczaj, aby zmienić czas lub rampę</div>
            </div>
        </div>
    """.replace('\n', ''), unsafe_allow_html=True)

    # ==========================================
    # 2. BAZA DANYCH
    # ==========================================
    worksheet_rampy, df_rampy = db.load_data(sh, "DB_Rampy")
    
    if worksheet_rampy is None:
        st.warning("⚠️ Zbyt wiele zapytań do Google Sheets. Odczekaj chwilę i odśwież.")
        return

    if df_rampy.empty and len(df_rampy.columns) <= 1:
        headers = [
            "ID_Rezerwacji", "Rampa", "Data", "Godzina_Od", "Godzina_Do", 
            "Nazwa_Imprezy", "Pojazd", "Kierowca", "Telefon", "Email", 
            "Naczepa", "Typ_Naczepy", "Faktyczny_Podjazd", "Trwa_Zaladunek", "Zakonczono", "Notatki"
        ]
        worksheet_rampy.append_row(headers)
        st.cache_data.clear()
        worksheet_rampy, df_rampy = db.load_data(sh, "DB_Rampy")

    if "rampy_data" not in st.session_state: st.session_state.rampy_data = date.today()
    if "wybrana_rezerwacja" not in st.session_state: st.session_state.wybrana_rezerwacja = None
    if "pokaz_formularz" not in st.session_state: st.session_state.pokaz_formularz = None

    # ==========================================
    # 3. GÓRNY PASEK NAWIGACYJNY I AUTO-PLANOWANIE
    # ==========================================
    st.markdown('<div class="top-bar-btn">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6, c7 = st.columns([0.5, 2.0, 0.5, 1.0, 3.5, 2.2, 2.2], vertical_alignment="center")
    
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
        with st.form("search_form", border=False):
            sc1, sc2 = st.columns([5, 1])
            szukana_fraza = sc1.text_input("Szukaj", placeholder="🔍 Szukaj rezerwacji, auta, kierowcy...", label_visibility="collapsed")
            sc2.form_submit_button("Szukaj")
    with c6:
        st.markdown('<div class="btn-action-auto">', unsafe_allow_html=True)
        if st.button("🤖 AUTO-PLANUJ Z EVENTÓW", use_container_width=True):
            # SILNIK INTELIGENTNEGO PLANOWANIA
            with st.spinner("Skanowanie bazy Eventów i alokacja slotów..."):
                ws_ev, df_ev = db.load_data(sh, "DB_Eventy")
                zmieniono = 0
                if not df_ev.empty:
                    df_aktywne_ev = df_ev[df_ev.get("Zakonczone_Arch", pd.Series()) != "TAK"]
                    
                    # Definiujemy standardowe dwugodzinne okna
                    dostepne_sloty = [
                        ("07:00", "09:00"), ("09:00", "11:00"), 
                        ("11:00", "13:00"), ("13:00", "15:00"), ("15:00", "17:00")
                    ]
                    dostepne_rampy = ["11", "12", "13", "14", "15"]

                    for _, ev in df_aktywne_ev.iterrows():
                        ev_id = str(ev.get("ID_Zlecenia", "")).strip()
                        data_zal = str(ev.get("Data_Zlecenia_Tr", "")).strip()
                        
                        if not ev_id or not data_zal or data_zal in ["nan", "None", "NaT", "Brak danych"]:
                            continue
                            
                        # Sprawdzamy, czy ten Event nie ma już przypisanej rampy
                        is_scheduled = False
                        if not df_rampy.empty and 'Notatki' in df_rampy.columns:
                            if df_rampy['Notatki'].astype(str).str.contains(ev_id).any():
                                is_scheduled = True
                                
                        if not is_scheduled:
                            przypisano = False
                            for test_od, test_do in dostepne_sloty:
                                if przypisano: break
                                
                                for rampa_test in dostepne_rampy:
                                    # Sprawdzamy czy dany slot jest wolny
                                    overlap = False
                                    if not df_rampy.empty:
                                        zajete = df_rampy[(df_rampy['Data'] == data_zal) & (df_rampy['Rampa'] == rampa_test)]
                                        for _, z in zajete.iterrows():
                                            z_od = str(z.get('Godzina_Od', '00:00')).strip()
                                            z_do = str(z.get('Godzina_Do', '00:00')).strip()
                                            if test_od < z_do and test_do > z_od:
                                                overlap = True
                                                break
                                                
                                    if not overlap:
                                        # ZNALEZIONO WOLNĄ LUKĘ!
                                        rej = str(ev.get('Nr_Rejestracyjny', '')).strip()
                                        typ = str(ev.get('Typ_Pojazdu', '')).strip()
                                        pojazd_comb = f"{rej} / {typ}" if rej != "nan" and typ != "nan" and rej and typ else (rej if rej != "nan" else typ)
                                        kier = str(ev.get('Kierowca', '')).strip()
                                        
                                        nowy_id = f"RMP-{int(time.time())}-{ev_id[-4:]}"
                                        nowy_wiersz = [
                                            nowy_id, rampa_test, data_zal, test_od, test_do,
                                            str(ev.get('Nazwa_Targow', '')).strip(), pojazd_comb, 
                                            kier if kier != "nan" else "", "", "", "", "", "", "NIE", "NIE", 
                                            f"Powiązane z: {ev_id}"
                                        ]
                                        db.append_data("DB_Rampy", nowy_wiersz)
                                        
                                        # BEZPIECZNE DODANIE DO DF (naprawia błąd "mismatched columns")
                                        kolumny = [
                                            "ID_Rezerwacji", "Rampa", "Data", "Godzina_Od", "Godzina_Do", 
                                            "Nazwa_Imprezy", "Pojazd", "Kierowca", "Telefon", "Email", 
                                            "Naczepa", "Typ_Naczepy", "Faktyczny_Podjazd", "Trwa_Zaladunek", "Zakonczono", "Notatki"
                                        ]
                                        nowy_dict = dict(zip(kolumny, nowy_wiersz))
                                        df_rampy = pd.concat([df_rampy, pd.DataFrame([nowy_dict])], ignore_index=True)
                                        
                                        przypisano = True
                                        zmieniono += 1
                                        break
                                        
                if zmieniono > 0:
                    st.toast(f"✅ Auto-Planowanie zakończone: Zarezerwowano {zmieniono} nowych slotów!", icon="🤖")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.toast("ℹ️ Brak nowych załadunków do zaplanowania.", icon="🤖")
        st.markdown('</div>', unsafe_allow_html=True)

    with c7:
        st.markdown('<div class="btn-action-primary">', unsafe_allow_html=True)
        if st.button("➕ NOWA REZERWACJA", use_container_width=True):
            st.session_state.pokaz_formularz = "NOWA"
            st.session_state.wybrana_rezerwacja = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Ostrzeżenie weekendowe
    if st.session_state.rampy_data.weekday() >= 5:
        st.error("⚠️ Magazyn w weekendy jest zamknięty. Dodawaj rezerwacje tylko po wcześniejszym uzgodnieniu z pracownikami magazynu.")

    # ==========================================
    # 4. SILNIK KALENDARZA (Z wyglądem biletów)
    # ==========================================
    events = []
    if not df_rampy.empty:
        df_dzien = df_rampy[df_rampy['Data'] == str(st.session_state.rampy_data)]
        
        if szukana_fraza:
            mask = df_dzien.astype(str).apply(lambda row: row.str.contains(szukana_fraza, case=False, na=False).any(), axis=1)
            df_dzien = df_dzien[mask]

        for _, row in df_dzien.iterrows():
            podjazd_db = str(row.get('Faktyczny_Podjazd', '')).strip()
            trwa_zaladunek = str(row.get('Trwa_Zaladunek', '')).strip().upper() == "TAK"
            zakonczono = str(row.get('Zakonczono', '')).strip().upper() == "TAK"
            
            # Formatowanie czasu podjazdu
            podj_display = ""
            if podjazd_db and podjazd_db not in ["nan", "None", ""]:
                if len(podjazd_db) > 5:
                    p_date, p_time = podjazd_db.split(" ")[0], podjazd_db.split(" ")[1]
                    if p_date != str(row['Data']): podj_display = f"{p_date[8:10]}.{p_date[5:7]} {p_time}"
                    else: podj_display = p_time
                else:
                    podj_display = podjazd_db

            # Konstruowanie zawartości biletu
            impreza = str(row.get('Nazwa_Imprezy', ''))
            pojazd = str(row.get('Pojazd', ''))
            kierowca = str(row.get('Kierowca', ''))
            
            if zakonczono:
                kolor_ramki = "#718096"
                status_txt = "⬛ Zakończono"
                kolor_tla = "#E2E8F0"
            elif trwa_zaladunek:
                kolor_ramki = "#3B82F6"
                status_txt = "⏳ Trwa załadunek..."
                kolor_tla = "#EBF8FF"
            elif podj_display:
                kolor_ramki = "#10B981"
                status_txt = f"✔ Podjechał: {podj_display}"
                kolor_tla = "#FDFBF7"
            else:
                kolor_ramki = "#C5A880"
                status_txt = "🕒 Podjechał: –"
                kolor_tla = "#FDFBF7"

            tytul_eventu = f"{impreza}\n{pojazd}\n{kierowca}\n\n{status_txt}"

            events.append({
                "id": str(row.get('ID_Rezerwacji', '')),
                "resourceId": str(row.get('Rampa', '')),
                "start": f"{row['Data']}T{row.get('Godzina_Od', '00:00')}:00",
                "end": f"{row['Data']}T{row.get('Godzina_Do', '01:00')}:00",
                "title": tytul_eventu,
                "borderColor": kolor_ramki,
                "backgroundColor": kolor_tla,
                "textColor": "#1A2530"
            })

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
        "slotMaxTime": "18:00:00",
        "slotDuration": "00:30:00",
        "allDaySlot": False,
        "editable": True,         
        "droppable": True,
        "selectable": True,
        "headerToolbar": False,   
        "height": "auto",
        "slotLabelFormat": { "hour": "2-digit", "minute": "2-digit", "hour12": False }
    }

    cal_css = """
        .fc { background-color: transparent !important; color: #E2DCD3; font-family: 'Inter', sans-serif; }
        
        .fc-col-header-cell {
            background-color: #0A1428 !important; border-bottom: 1px solid rgba(197, 168, 128, 0.2) !important;
            font-family: 'Bebas Neue', sans-serif !important; font-size: 18px !important; letter-spacing: 2px !important;
            color: #E2DCD3 !important; padding: 10px 0 !important;
        }
        
        .fc-timegrid-slot { height: 45px !important; border-bottom: 1px dashed rgba(255, 255, 255, 0.08) !important; }
        .fc-timegrid-slot-label { font-size: 12px !important; color: #C5A880 !important; font-weight: 600 !important; border-right: 1px solid rgba(197, 168, 128, 0.1) !important; vertical-align: top !important; padding-top: 5px !important; }
        .fc-theme-standard td, .fc-theme-standard th { border-color: rgba(197, 168, 128, 0.15) !important; }
        
        .fc-timegrid-col { background: rgba(5, 10, 21, 0.6) !important; }
        
        /* Baseball ticket style */
        .fc-event {
            border-left: 5px dashed var(--fc-border-color) !important;
            border-right: 5px dashed var(--fc-border-color) !important;
            border-top: 1px solid rgba(0,0,0,0.1) !important;
            border-bottom: 1px solid rgba(0,0,0,0.1) !important;
            border-radius: 4px !important;
            box-shadow: 2px 4px 10px rgba(0,0,0,0.6) !important;
            padding: 6px !important;
            cursor: grab !important;
        }
        .fc-event:active { cursor: grabbing !important; }
        .fc-event-main { padding: 0 !important; height: 100% !important; }
        
        .fc-event-title {
            white-space: pre-wrap !important; 
            font-size: 11px !important;
            font-weight: 700 !important;
            line-height: 1.4 !important;
            color: #1A2530 !important;
        }
    """

    st.markdown('<div style="background: #11151E; border-top: 2px solid #BA4949; padding: 10px; border-radius: 4px; box-shadow: inset 0 0 20px rgba(0,0,0,0.8);">', unsafe_allow_html=True)
    
    cal_state = calendar(
        events=events, 
        options=calendar_options, 
        custom_css=cal_css,
        callbacks=["eventClick", "eventChange"], 
        key="rampy_calendar_comp"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Legenda pod kalendarzem
    st.markdown("""
        <div class="legend-container">
            <div class="legend-item"><div class="l-box l-yellow"></div> Planowana rezerwacja</div>
            <div class="legend-item"><div class="l-box l-green"></div> Podjechał pod rampę</div>
            <div class="legend-item"><div class="l-box l-blue"></div> Trwa załadunek</div>
            <div class="legend-item"><div class="l-box l-gray"></div> Zakończono</div>
        </div>
    """.replace('\n', ''), unsafe_allow_html=True)

    # ==========================================
    # 5. OBSŁUGA ZDARZEŃ (DRAG & DROP)
    # ==========================================
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
            
            idx = df_rampy[df_rampy['ID_Rezerwacji'] == ev_id].index[0]
            df_rampy.at[idx, 'Rampa'] = nowa_rampa
            df_rampy.at[idx, 'Data'] = nowa_data
            df_rampy.at[idx, 'Godzina_Od'] = nowy_od
            df_rampy.at[idx, 'Godzina_Do'] = nowy_do
            gs_row = int(df_rampy.at[idx, 'sheet_row'])
            db.update_single_row_safe("DB_Rampy", gs_row, df_rampy.loc[idx])
            
            st.session_state.pop("rampy_calendar_comp", None)
            st.toast(f"✅ Przypisano do Rampy {nowa_rampa} ({nowy_od} - {nowy_do})")
            time.sleep(0.5)
            st.rerun()
        except Exception as e:
            st.error(f"Błąd przesunięcia: {e}")

    if cal_state.get("eventClick"):
        klikniete_id = cal_state["eventClick"]["event"]["id"]
        if st.session_state.wybrana_rezerwacja != klikniete_id:
            st.session_state.wybrana_rezerwacja = klikniete_id
            st.session_state.pokaz_formularz = None
            st.session_state.pop("rampy_calendar_comp", None)
            st.rerun()

    # ==========================================
    # 6. KREMOWY PANEL SZCZEGÓŁÓW
    # ==========================================
    if st.session_state.get("wybrana_rezerwacja") and st.session_state.get("pokaz_formularz") != "NOWA":
        rez_id = st.session_state.wybrana_rezerwacja
        try:
            row = df_rampy[df_rampy['ID_Rezerwacji'] == rez_id].iloc[0]
            
            podjazd_db = str(row.get('Faktyczny_Podjazd', '')).strip()
            if podjazd_db and podjazd_db not in ["nan", "None", ""]:
                if len(podjazd_db) > 5:
                    p_date, p_time = podjazd_db.split(" ")[0], podjazd_db.split(" ")[1]
                    podj_data_disp, podj_czas_disp = f"📅 {p_date}", f"🕒 {p_time}"
                else:
                    podj_data_disp, podj_czas_disp = f"📅 {row.get('Data', '-')}", f"🕒 {podjazd_db}"
            else:
                podj_data_disp, podj_czas_disp = "📅 –", "🕒 –"

            pojazd_str = str(row.get('Pojazd', ''))
            rej = pojazd_str.split('/')[0].strip() if '/' in pojazd_str else (pojazd_str if pojazd_str else '-')
            typ = pojazd_str.split('/')[1].strip() if '/' in pojazd_str else '-'

            html_panel = f"""
            <div style="background-color: #FDFBF7; border-top: 4px solid #BA4949; border-radius: 6px; padding: 25px; color: #1A2530; display: flex; flex-direction: row; gap: 20px; box-shadow: 0px 10px 30px rgba(0,0,0,0.7);">
                <div style="flex: 3;">
                    <h2 style="color: #050A15; margin: 0; font-size: 26px; font-weight: 800; font-family: 'Inter', sans-serif;">{row.get('Nazwa_Imprezy', '-')}</h2>
                    <h4 style="color: #8C8477; margin: 2px 0 15px 0; font-family: 'Bebas Neue', sans-serif; letter-spacing: 1.5px; font-size: 18px;">RAMP A {row.get('Rampa', '-')}</h4>
                    <div style="display: flex; gap: 30px;">
                        <div>
                            <div style="font-family: 'Bebas Neue', sans-serif; color: #8C8477; font-size: 14px; letter-spacing: 1px;">PLANOWANA REZERWACJA</div>
                            <div style="font-weight: 600; color: #050A15; font-size: 14px; margin-top: 4px;">📅 {row.get('Data', '-')}</div>
                            <div style="font-weight: 600; color: #050A15; font-size: 14px; margin-top: 2px;">🕒 {row.get('Godzina_Od', '-')} - {row.get('Godzina_Do', '-')}</div>
                        </div>
                        <div>
                            <div style="font-family: 'Bebas Neue', sans-serif; color: #8C8477; font-size: 14px; letter-spacing: 1px;">PODJECHAŁ POD RAMPĘ</div>
                            <div style="font-weight: 600; color: #10B981; font-size: 14px; margin-top: 4px;">{podj_data_disp}</div>
                            <div style="font-weight: 600; color: #10B981; font-size: 14px; margin-top: 2px;">{podj_czas_disp}</div>
                        </div>
                    </div>
                </div>
                <div style="flex: 2; border-left: 1px solid rgba(197,168,128,0.3); padding-left: 20px;">
                    <div style="font-family: 'Bebas Neue', sans-serif; color: #8C8477; font-size: 14px; letter-spacing: 1px; margin-bottom: 10px;">🚛 DANE AUTA</div>
                    <table style="width: 100%; font-size: 12px; color: #4A5568;">
                        <tr><td style="padding-bottom: 6px; width: 40%;">REJESTRACJA</td><td style="font-weight: 700; color: #050A15; padding-bottom: 6px;">{rej}</td></tr>
                        <tr><td style="padding-bottom: 6px;">TYP</td><td style="font-weight: 700; color: #050A15; padding-bottom: 6px;">{typ}</td></tr>
                        <tr><td style="padding-bottom: 6px;">NACZEPA</td><td style="font-weight: 700; color: #050A15; padding-bottom: 6px;">{row.get('Naczepa', '-')}</td></tr>
                        <tr><td>TYP NACZEPY</td><td style="font-weight: 700; color: #050A15;">{row.get('Typ_Naczepy', '-')}</td></tr>
                    </table>
                </div>
                <div style="flex: 2; border-left: 1px solid rgba(197,168,128,0.3); padding-left: 20px;">
                    <div style="font-family: 'Bebas Neue', sans-serif; color: #8C8477; font-size: 14px; letter-spacing: 1px; margin-bottom: 10px;">👤 DANE KIEROWCY</div>
                    <div style="font-size: 10px; color: #8C8477; margin-bottom: 2px;">IMIĘ I NAZWISKO</div>
                    <div style="font-size: 14px; font-weight: 800; color: #050A15; margin-bottom: 8px;">{row.get('Kierowca', '-')}</div>
                    <div style="font-size: 10px; color: #8C8477; margin-bottom: 2px;">TELEFON</div>
                    <div style="font-size: 13px; font-weight: 600; color: #050A15; margin-bottom: 8px;">{row.get('Telefon', '-')}</div>
                    <div style="font-size: 10px; color: #8C8477; margin-bottom: 2px;">E-MAIL</div>
                    <div style="font-size: 13px; font-weight: 600; color: #050A15;">{row.get('Email', '-')}</div>
                </div>
            </div>
            """
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_info, col_akcje = st.columns([8.5, 1.5])
            
            with col_info:
                st.markdown(html_panel.replace('\n', ''), unsafe_allow_html=True)
                
                c_text, c_close = st.columns([8, 2])
                c_text.markdown("<p style='color: #8C8477; font-size: 12px; margin-top: 15px; text-align: center;'>⤢ Przeciągnij rezerwację w kalendarzu, aby zmienić godzinę lub rampę</p>", unsafe_allow_html=True)
                if c_close.button("✖ ZAMKNIJ", use_container_width=True):
                    st.session_state.wybrana_rezerwacja = None
                    st.rerun()
                    
            with col_akcje:
                st.markdown("<div style='background-color: #FDFBF7; border: 1px solid #C5A880; border-radius: 6px; padding: 15px; height: 100%; box-shadow: 0 5px 15px rgba(0,0,0,0.3);'>", unsafe_allow_html=True)
                st.markdown("<div style='font-family: \"Bebas Neue\", sans-serif; color: #8C8477; font-size: 16px; margin-bottom: 10px; text-align: center; letter-spacing: 2px;'>AKCJE</div>", unsafe_allow_html=True)
                
                if st.button("✏️ EDYTUJ", use_container_width=True): 
                    st.session_state.pokaz_formularz = "EDYCJA"
                    st.rerun()
                    
                if st.button("📄 DUPLIKUJ", use_container_width=True): 
                    st.session_state.pokaz_formularz = "DUPLIKUJ"
                    st.rerun()
                    
                st.markdown("<hr style='margin: 10px 0; border-color: rgba(197, 168, 128, 0.3);'>", unsafe_allow_html=True)
                if st.button("🗑️ USUŃ", use_container_width=True):
                    gs_row = int(row['sheet_row'])
                    db.delete_row("DB_Rampy", gs_row)
                    st.session_state.wybrana_rezerwacja = None
                    st.success("Rezerwacja trwale usunięta!")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # ==========================================
            # INTELIGENTNE PRZYCISKI: ROZPOCZNIJ / ZWOLNIJ RAMPĘ
            # ==========================================
            st.markdown("<br>", unsafe_allow_html=True)
            b1, b2, _ = st.columns([3, 3, 4])
            
            is_loading = str(row.get('Trwa_Zaladunek', 'NIE')).upper() == "TAK"
            is_done = str(row.get('Zakonczono', 'NIE')).upper() == "TAK"
            
            with b1:
                if not is_done:
                    if not is_loading:
                        if st.button("▶ ROZPOCZNIJ ZAŁADUNEK", type="primary", use_container_width=True):
                            idx = df_rampy[df_rampy['ID_Rezerwacji'] == rez_id].index[0]
                            df_rampy.at[idx, 'Trwa_Zaladunek'] = "TAK"
                            if not podjazd_db or podjazd_db in ["nan", "None"]:
                                df_rampy.at[idx, 'Faktyczny_Podjazd'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                            gs_row = int(df_rampy.at[idx, 'sheet_row'])
                            db.update_single_row_safe("DB_Rampy", gs_row, df_rampy.loc[idx])
                            st.rerun()
                    else:
                        st.button("⏳ ZAŁADUNEK W TOKU...", disabled=True, use_container_width=True)

            with b2:
                if not is_done and is_loading:
                    if st.button("🟢 ZWOLNIJ RAMPĘ (ZAKOŃCZ)", use_container_width=True):
                        now = datetime.now()
                        today = now.date()
                        start_dt = now
                        
                        if podjazd_db and podjazd_db not in ["nan", "None"]:
                            if len(podjazd_db) > 5:
                                try: start_dt = datetime.strptime(podjazd_db, "%Y-%m-%d %H:%M")
                                except: pass
                            else:
                                try:
                                    r_date = datetime.strptime(str(row['Data']), "%Y-%m-%d").date()
                                    r_time = datetime.strptime(podjazd_db, "%H:%M").time()
                                    start_dt = datetime.combine(r_date, r_time)
                                except: pass
                                
                        if start_dt.date() < today:
                            start_dt = datetime.combine(today, datetime.time(7, 0))
                        elif start_dt.date() == today and start_dt.time() < datetime.time(7, 0):
                            start_dt = datetime.combine(today, datetime.time(7, 0))
                            
                        delta = now - start_dt
                        total_minutes = int(delta.total_seconds() / 60)
                        if total_minutes < 0: total_minutes = 0
                        hours, minutes = total_minutes // 60, total_minutes % 60
                        duration_str = f"{hours}h {minutes}m"
                        
                        idx = df_rampy[df_rampy['ID_Rezerwacji'] == rez_id].index[0]
                        df_rampy.at[idx, 'Trwa_Zaladunek'] = "NIE"
                        df_rampy.at[idx, 'Zakonczono'] = "TAK"
                        
                        stare_notatki = str(df_rampy.at[idx, 'Notatki'])
                        if stare_notatki in ["nan", "None"]: stare_notatki = ""
                        df_rampy.at[idx, 'Notatki'] = f"[⏱️ Czas operacji na rampie: {duration_str}] " + stare_notatki
                        
                        gs_row = int(df_rampy.at[idx, 'sheet_row'])
                        db.update_single_row_safe("DB_Rampy", gs_row, df_rampy.loc[idx])
                        st.session_state.wybrana_rezerwacja = None
                        st.success(f"Rampa zwolniona! Zarejestrowany czas operacji: {duration_str}")
                        st.rerun()

        except Exception as e:
            st.error(f"Błąd ładowania szczegółów: {e}")

    # ==========================================
    # 7. FORMULARZ (DODAJ / EDYTUJ / DUPLIKUJ)
    # ==========================================
    if st.session_state.get("pokaz_formularz") in ["NOWA", "EDYCJA", "DUPLIKUJ"]:
        st.markdown("<hr style='border-color: rgba(197, 168, 128, 0.1); margin: 20px 0;'>", unsafe_allow_html=True)
        tytul = "➕ Nowa Rezerwacja" if st.session_state.pokaz_formularz == "NOWA" else ("📄 Duplikowanie Rezerwacji" if st.session_state.pokaz_formularz == "DUPLIKUJ" else "✏️ Edycja Rezerwacji")
        st.markdown(f"<h3 style='color: #C5A880; font-family: \"Shippori Mincho\", serif;'>{tytul}</h3>", unsafe_allow_html=True)
        
        dane_edycja = {}
        if st.session_state.pokaz_formularz in ["EDYCJA", "DUPLIKUJ"] and st.session_state.wybrana_rezerwacja:
            dane_edycja = df_rampy[df_rampy['ID_Rezerwacji'] == st.session_state.wybrana_rezerwacja].iloc[0].to_dict()

        with st.form("form_rampy", clear_on_submit=True):
            fc1, fc2, fc3 = st.columns([1, 1, 1])
            with fc1:
                f_impreza = st.text_input("Nazwa Imprezy *", value=dane_edycja.get('Nazwa_Imprezy', ''))
                f_rampa = st.selectbox("Rampa", ["11", "12", "13", "14", "15"], index=["11", "12", "13", "14", "15"].index(dane_edycja.get('Rampa', '11')) if dane_edycja.get('Rampa') in ["11", "12", "13", "14", "15"] else 0)
                
                dt_str = str(dane_edycja.get('Data', st.session_state.rampy_data))
                try: val_data = datetime.strptime(dt_str, "%Y-%m-%d").date() if dt_str and dt_str not in ["nan", "None"] else st.session_state.rampy_data
                except: val_data = st.session_state.rampy_data
                f_data = st.date_input("Data rezerwacji", value=val_data)
                
                od_str = str(dane_edycja.get('Godzina_Od', '08:00')).strip()
                try: val_od = datetime.strptime(od_str, "%H:%M").time() if od_str and od_str not in ["nan", "None"] else datetime.strptime("08:00", "%H:%M").time()
                except: val_od = datetime.strptime("08:00", "%H:%M").time()
                f_od = st.time_input("Godzina Od", value=val_od)
                
                do_str = str(dane_edycja.get('Godzina_Do', '10:00')).strip()
                try: val_do = datetime.strptime(do_str, "%H:%M").time() if do_str and do_str not in ["nan", "None"] else datetime.strptime("10:00", "%H:%M").time()
                except: val_do = datetime.strptime("10:00", "%H:%M").time()
                f_do = st.time_input("Godzina Do", value=val_do)
                
            with fc2:
                f_pojazd = st.text_input("Pojazd (Rejestracja / Typ)", value=dane_edycja.get('Pojazd', ''))
                f_naczepa = st.text_input("Rejestracja Naczepy", value=dane_edycja.get('Naczepa', ''))
                f_typ_naczepy = st.text_input("Typ Naczepy", value=dane_edycja.get('Typ_Naczepy', ''))
                f_kierowca = st.text_input("Imię i Nazwisko Kierowcy", value=dane_edycja.get('Kierowca', ''))
                f_tel = st.text_input("Telefon Kierowcy", value=dane_edycja.get('Telefon', ''))
                f_email = st.text_input("E-mail", value=dane_edycja.get('Email', ''))
                
            with fc3:
                podj_baza = "" if st.session_state.pokaz_formularz == "DUPLIKUJ" else str(dane_edycja.get('Faktyczny_Podjazd', '')).strip()
                val_podj_d, val_podj_t = None, None
                
                if podj_baza and podj_baza not in ["nan", "None"]:
                    if len(podj_baza) > 5:
                        try:
                            dt_obj = datetime.strptime(podj_baza, "%Y-%m-%d %H:%M")
                            val_podj_d = dt_obj.date()
                            val_podj_t = dt_obj.time()
                        except: pass
                    else:
                        try:
                            val_podj_t = datetime.strptime(podj_baza, "%H:%M").time()
                            val_podj_d = datetime.strptime(str(dane_edycja.get('Data', st.session_state.rampy_data)), "%Y-%m-%d").date()
                        except: pass
                
                st.markdown("<div style='background: rgba(10, 20, 40, 0.5); padding: 15px; border-radius: 8px; border: 1px solid #1C2D4A;'>", unsafe_allow_html=True)
                st.markdown("<p style='color: #8C8477; font-weight: bold; margin-bottom: 5px;'>Status Operacji na Rampie</p>", unsafe_allow_html=True)
                
                dp_col1, dp_col2 = st.columns(2)
                f_podjazd_data = dp_col1.date_input("Data podjazdu", value=val_podj_d if val_podj_d else val_data)
                f_podjazd_czas = dp_col2.time_input("Godzina (Puste = czeka)", value=val_podj_t)
                usun_podjazd = st.checkbox("Wyczyść podjazd (Cofnij status)", value=(val_podj_t is None))
                
                f_trwa = st.selectbox("Czy trwa załadunek/rozładunek?", ["NIE", "TAK"], index=1 if str(dane_edycja.get('Trwa_Zaladunek', 'NIE')).upper() == "TAK" and st.session_state.pokaz_formularz != "DUPLIKUJ" else 0)
                f_koniec = st.selectbox("Czy zakończono całkowicie?", ["NIE", "TAK"], index=1 if str(dane_edycja.get('Zakonczono', 'NIE')).upper() == "TAK" and st.session_state.pokaz_formularz != "DUPLIKUJ" else 0)
                st.markdown("</div>", unsafe_allow_html=True)
                
                f_notatki = st.text_area("Dodatkowe notatki", value="" if st.session_state.pokaz_formularz == "DUPLIKUJ" else dane_edycja.get('Notatki', ''))
            
            sc1, sc2 = st.columns([1, 1])
            if sc1.form_submit_button("💾 ZAPISZ", type="primary", use_container_width=True):
                if not f_impreza:
                    st.error("Nazwa Imprezy jest obowiązkowa!")
                else:
                    final_podjazd = "" if usun_podjazd else (f"{f_podjazd_data.strftime('%Y-%m-%d')} {f_podjazd_czas.strftime('%H:%M')}" if f_podjazd_czas else "")
                    
                    if st.session_state.pokaz_formularz in ["NOWA", "DUPLIKUJ"]:
                        new_id = f"RMP-{int(time.time())}"
                        nowy_wiersz = [
                            new_id, f_rampa, str(f_data), f_od.strftime("%H:%M"), f_do.strftime("%H:%M"),
                            f_impreza, f_pojazd, f_kierowca, f_tel, f_email,
                            f_naczepa, f_typ_naczepy, final_podjazd, f_trwa, f_koniec, f_notatki
                        ]
                        db.append_data("DB_Rampy", nowy_wiersz)
                        st.success("Rezerwacja utworzona!")
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
                        st.success("Zaktualizowano rezerwację!")

                    st.session_state.pokaz_formularz = None
                    st.session_state.pop("rampy_calendar_comp", None)
                    st.rerun()
            if sc2.form_submit_button("✖ ANULUJ", use_container_width=True):
                st.session_state.pokaz_formularz = None
                st.rerun()
