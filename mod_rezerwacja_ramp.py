import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
from streamlit_calendar import calendar
import db

def render(sh):
    # ==========================================
    # 1. NAPRAWA WYDAJNOŚCI I STYLIZACJA
    # ==========================================
    st.markdown("""
        <style>
        div[data-testid="stTextInput"] input, 
        div[data-testid="stTextArea"] textarea, 
        div[data-testid="stNumberInput"] input {
            backdrop-filter: none !important;
            background-color: #0A1428 !important; 
            transform: translateZ(0) !important; 
            will-change: transform !important;
            border: 1px solid #1C2D4A !important;
        }
        
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
        
        .top-bar-btn button {
            background-color: #12100E !important; border: 1px solid rgba(197, 168, 128, 0.3) !important;
            color: #C5A880 !important; font-weight: bold !important; font-family: 'Bebas Neue', sans-serif !important; letter-spacing: 1px !important;
        }
        .top-bar-btn button:hover { background-color: #1C1A18 !important; color: #FDFBF7 !important; border-color: #C5A880 !important; }
        </style>
    """, unsafe_allow_html=True)

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
    # 2. BAZA DANYCH I INICJALIZACJA
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
    # 3. GÓRNY PASEK NAWIGACYJNY (Bez przełącznika)
    # ==========================================
    st.markdown('<div class="top-bar-btn">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns([0.5, 2, 0.5, 1.2, 3.5, 2], vertical_alignment="center")
    
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
        st.markdown('</div>', unsafe_allow_html=True) 
        if st.button("➕ NOWA REZERWACJA", type="primary", use_container_width=True):
            st.session_state.pokaz_formularz = "NOWA"
            st.session_state.wybrana_rezerwacja = None
            st.rerun()

    # OSTRZEŻENIE O WEEKENDZIE
    if st.session_state.rampy_data.weekday() >= 5:
        st.markdown("""
            <div style="background: rgba(186, 73, 73, 0.1); border: 1px solid #BA4949; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; color: #FDFBF7; display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 20px;">⚠️</span>
                <div>
                    <strong style="color: #BA4949; font-family: 'Bebas Neue', sans-serif; letter-spacing: 1px; font-size: 16px;">MAGAZYN ZAMKNIĘTY (WEEKEND)</strong><br>
                    <span style="font-size: 13px; color: #E2DCD3;">Soboty i niedziele są dniami wolnymi. Dodawaj tu rezerwacje tylko, jeśli operacja została wcześniej uzgodniona z obsługą magazynu.</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ==========================================
    # 4. SILNIK KALENDARZA
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
            
            # Formatyzacja daty podjazdu na bilecie (wykrywa czy auto czeka od wczoraj)
            podj_display = ""
            if podjazd_db and podjazd_db not in ["nan", "None", ""]:
                if len(podjazd_db) > 5: # Zawiera datę i czas (YYYY-MM-DD HH:MM)
                    p_date, p_time = podjazd_db.split(" ")[0], podjazd_db.split(" ")[1]
                    if p_date != str(row['Data']):
                        podj_display = f"{p_date[8:10]}.{p_date[5:7]} {p_time}" # DD.MM HH:MM
                    else:
                        podj_display = p_time
                else:
                    podj_display = podjazd_db

            impreza = str(row.get('Nazwa_Imprezy', ''))
            pojazd = str(row.get('Pojazd', ''))
            kierowca = str(row.get('Kierowca', ''))
            
            if zakonczono:
                kolor_ramki = "#718096"
                status_txt = "⬛ Zakończono"
            elif trwa_zaladunek:
                kolor_ramki = "#3B82F6"
                status_txt = "⏳ Trwa załadunek..."
            elif podj_display:
                kolor_ramki = "#10B981"
                status_txt = f"✔ Podjechał: {podj_display}"
            else:
                kolor_ramki = "#C5A880"
                status_txt = "🕒 Podjechał: –"

            tytul_eventu = f"{impreza.upper()}\n{pojazd}\n{kierowca}\n\n{status_txt}"

            events.append({
                "id": str(row.get('ID_Rezerwacji', '')),
                "resourceId": str(row.get('Rampa', '')),
                "start": f"{row['Data']}T{row.get('Godzina_Od', '00:00')}:00",
                "end": f"{row['Data']}T{row.get('Godzina_Do', '01:00')}:00",
                "title": tytul_eventu,
                "borderColor": kolor_ramki,
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
            background-color: #12100E !important;
            border-bottom: 2px solid rgba(197, 168, 128, 0.2) !important;
            font-family: 'Bebas Neue', sans-serif !important;
            font-size: 20px !important;
            letter-spacing: 2px !important;
            color: #E2DCD3 !important;
            padding: 12px 0 !important;
        }
        
        .fc-timegrid-slot { height: 50px !important; border-bottom: 1px dashed rgba(197, 168, 128, 0.1) !important; }
        .fc-timegrid-slot-label {
            font-size: 13px !important; color: #C5A880 !important; font-weight: 600 !important;
            border-right: 1px solid rgba(197, 168, 128, 0.1) !important;
            vertical-align: top !important; padding-top: 5px !important;
        }
        .fc-theme-standard td, .fc-theme-standard th { border-color: rgba(197, 168, 128, 0.15) !important; }
        .fc-timegrid-col { background: rgba(5, 10, 21, 0.4) !important; }
        
        .fc-event {
            background-color: #FDFBF7 !important;
            border-left: 5px dashed var(--fc-border-color) !important;
            border-right: 5px dashed var(--fc-border-color) !important;
            border-top: 1px solid rgba(0,0,0,0.1) !important;
            border-bottom: 1px solid rgba(0,0,0,0.1) !important;
            border-radius: 4px !important;
            box-shadow: 2px 4px 10px rgba(0,0,0,0.4) !important;
            padding: 6px !important;
            cursor: grab !important;
        }
        .fc-event:active { cursor: grabbing !important; }
        .fc-event-main { padding: 0 !important; height: 100% !important; }
        
        .fc-event-title {
            white-space: pre-wrap !important; 
            font-size: 12px !important;
            font-weight: 600 !important;
            line-height: 1.4 !important;
            color: #1A2530 !important;
        }
    """

    st.markdown('<div style="background: rgba(18, 16, 14, 0.9); padding: 15px; border-radius: 8px; border: 1px solid rgba(197, 168, 128, 0.2); margin-top: 15px;">', unsafe_allow_html=True)
    
    cal_state = calendar(
        events=events, 
        options=calendar_options, 
        custom_css=cal_css,
        callbacks=["eventClick", "eventChange"], 
        key="rampy_calendar_comp"
    )
    st.markdown('</div>', unsafe_allow_html=True)

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
    # 6. PANEL SZCZEGÓŁÓW
    # ==========================================
    if st.session_state.get("wybrana_rezerwacja") and st.session_state.get("pokaz_formularz") != "NOWA":
        rez_id = st.session_state.wybrana_rezerwacja
        try:
            row = df_rampy[df_rampy['ID_Rezerwacji'] == rez_id].iloc[0]
            
            # Formatowanie wyświetlania daty podjazdu (Rozdziela YYYY-MM-DD HH:MM na odrębne linijki)
            podjazd_db = str(row.get('Faktyczny_Podjazd', '')).strip()
            if podjazd_db and podjazd_db not in ["nan", "None", ""]:
                if len(podjazd_db) > 5:
                    p_date, p_time = podjazd_db.split(" ")[0], podjazd_db.split(" ")[1]
                    podj_data_disp = f"📅 {p_date}"
                    podj_czas_disp = f"🕒 {p_time}"
                else:
                    podj_data_disp = f"📅 {row.get('Data', '-')}"
                    podj_czas_disp = f"🕒 {podjazd_db}"
            else:
                podj_data_disp = "📅 –"
                podj_czas_disp = "🕒 –"

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
                            <div style="font-weight: 600; color: #10B981; margin-top: 5px;">{podj_data_disp}</div>
                            <div style="font-weight: 600; color: #10B981; margin-top: 2px;">{podj_czas_disp}</div>
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
                st.markdown(html_panel, unsafe_allow_html=True)
                
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
        
        dane_edycja = {}
        if st.session_state.pokaz_formularz == "EDYCJA" and st.session_state.wybrana_rezerwacja:
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
                st.markdown("<div style='background: rgba(10, 20, 40, 0.5); padding: 15px; border-radius: 8px; border: 1px solid #1C2D4A;'>", unsafe_allow_html=True)
                st.markdown("<p style='color: #8C8477; font-weight: bold; margin-bottom: 5px;'>Status Operacji na Rampie</p>", unsafe_allow_html=True)
                
                podj_baza = str(dane_edycja.get('Faktyczny_Podjazd', '')).strip()
                val_podj_d, val_podj_t = None, None
                
                if podj_baza and podj_baza not in ["nan", "None"]:
                    if len(podj_baza) > 5: # YYYY-MM-DD HH:MM
                        try:
                            dt_obj = datetime.strptime(podj_baza, "%Y-%m-%d %H:%M")
                            val_podj_d = dt_obj.date()
                            val_podj_t = dt_obj.time()
                        except: pass
                    else: # Tylko HH:MM
                        try:
                            val_podj_t = datetime.strptime(podj_baza, "%H:%M").time()
                            val_podj_d = datetime.strptime(str(dane_edycja.get('Data', st.session_state.rampy_data)), "%Y-%m-%d").date()
                        except: pass
                
                dp_col1, dp_col2 = st.columns(2)
                f_podjazd_data = dp_col1.date_input("Data podjazdu", value=val_podj_d if val_podj_d else val_data)
                f_podjazd_czas = dp_col2.time_input("Godzina (Puste = czeka)", value=val_podj_t)
                usun_podjazd = st.checkbox("Wyczyść podjazd (Cofnij status)", value=(val_podj_t is None))
                
                f_trwa = st.selectbox("Czy trwa załadunek/rozładunek?", ["NIE", "TAK"], index=1 if str(dane_edycja.get('Trwa_Zaladunek', 'NIE')).upper() == "TAK" else 0)
                f_koniec = st.selectbox("Czy zakończono całkowicie?", ["NIE", "TAK"], index=1 if str(dane_edycja.get('Zakonczono', 'NIE')).upper() == "TAK" else 0)
                st.markdown("</div>", unsafe_allow_html=True)
                
                f_notatki = st.text_area("Dodatkowe notatki", value=dane_edycja.get('Notatki', ''))
            
            sc1, sc2 = st.columns([1, 1])
            if sc1.form_submit_button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                if not f_impreza:
                    st.error("Nazwa Imprezy jest obowiązkowa!")
                else:
                    final_podjazd = "" if usun_podjazd else (f"{f_podjazd_data.strftime('%Y-%m-%d')} {f_podjazd_czas.strftime('%H:%M')}" if f_podjazd_czas else "")
                    
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
