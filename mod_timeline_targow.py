import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re
import db

def parse_date(d_str):
    if pd.isna(d_str) or not str(d_str).strip() or str(d_str).strip() in ['nan', 'None']: 
        return None
    try:
        d_clean = str(d_str).strip().split()[0]
        if "." in d_clean:
            return datetime.strptime(d_clean, "%d.%m.%Y").date()
        return datetime.strptime(d_clean, "%Y-%m-%d").date()
    except:
        return None

def extract_rozladunek(notatki, fallback):
    if pd.isna(notatki): 
        return fallback
    match = re.search(r'\[Rozładunki:\s*([^\]]+)\]', str(notatki))
    if match:
        dates = match.group(1).split(",")
        d = parse_date(dates[-1].strip()) 
        if d: return d
    return fallback

def extract_demontaz(notatki, fallback_s, fallback_k):
    d_s, d_k = fallback_s, fallback_k
    if pd.isna(notatki): return d_s, d_k
    
    match_new = re.search(r'\[DEM:\s*([^\]]+)\]', str(notatki))
    match_old = re.search(r'DEM:\s*([^|\]]+)', str(notatki))
    
    match = match_new if match_new else match_old
    if match:
        dem_raw = match.group(1).strip()
        dates = [d.strip() for d in dem_raw.split(",")]
        if len(dates) > 0 and dates[0] and dates[0] != 'None':
            parsed_s = parse_date(dates[0])
            if parsed_s: 
                d_s = parsed_s
                d_k = parsed_s 
        if len(dates) > 1 and dates[1] and dates[1] != 'None':
            parsed_e = parse_date(dates[1])
            if parsed_e: 
                d_k = parsed_e
    return d_s, d_k

def render(sh):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Timeline Eventów</h1>
            <div class="module-subtitle">イベントのタイムライン ✦ PROJECT LIFECYCLE GANTT</div>
        </div>
    ''', unsafe_allow_html=True)

    st.markdown("<p style='color: #8C8477; font-size: 13px; margin-bottom: 20px;'>Wizualizacja " + '"PRO 999"'+ ". Kaskadowy układ projektów z wykorzystaniem wirtualnych mapowań osi czasu.</p>", unsafe_allow_html=True)

    with st.spinner("Ładowanie osi czasu i słowników..."):
        try:
            ws_ev, df_ev = db.load_data(sh, "DB_Eventy")
            df_etapy = db.fetch_data("DB_Event_Etapy")
        except Exception as e:
            st.error(f"Błąd ładowania danych: {e}")
            return

    df_aktywne = df_ev[df_ev.get("Zakonczone_Arch", pd.Series()) != "TAK"].copy() if not df_ev.empty else pd.DataFrame()

    if df_aktywne.empty:
        st.info("Brak aktywnych eventów w bazie.")
        return

    df_aktywne["Nazwa_Targow"] = df_aktywne["Nazwa_Targow"].astype(str).str.strip()
    
    def get_base_event(name):
        return name.split(" | ", 1)[0].strip() if " | " in name else name.strip()
        
    def get_dopisek(name):
        return name.split(" | ", 1)[1].strip() if " | " in name else ""

    df_aktywne["Base_Event"] = df_aktywne["Nazwa_Targow"].apply(get_base_event)
    df_aktywne["Dopisek"] = df_aktywne["Nazwa_Targow"].apply(get_dopisek)

    gantt_data = []
    grouped = df_aktywne.groupby("Base_Event")

    for nazwa_bazy, group in grouped:
        if not nazwa_bazy or nazwa_bazy in ["nan", "None", ""]: 
            continue
            
        etapy_row = df_etapy[df_etapy.iloc[:, 0].astype(str).str.strip() == nazwa_bazy] if not df_etapy.empty else pd.DataFrame()
        
        klient_s, klient_k, demontaz_s, demontaz_k = None, None, None, None
        if not etapy_row.empty:
            r_et = etapy_row.iloc[0]
            cols = df_etapy.columns.tolist()
            klient_s = parse_date(r_et.get(cols[1])) if len(cols) > 1 else None
            klient_k = parse_date(r_et.get(cols[2])) if len(cols) > 2 else None
            demontaz_s = parse_date(r_et.get(cols[3])) if len(cols) > 3 else None
            demontaz_k = parse_date(r_et.get(cols[4])) if len(cols) > 4 else None

        # 1. Główny wiersz eventu (Parent)
        # UID (Unique ID) jest ukryte przed użytkownikiem, ale to ono układa oś Y.
        p_uid = f"PARENT_{nazwa_bazy}"
        p_label = f"<b style='color: #E2DCD3; font-size: 14px;'>📌 {nazwa_bazy.upper()}</b>"
        sort_base = f"{nazwa_bazy.upper()}_0"

        if klient_s and klient_k:
            gantt_data.append({
                "UID": p_uid, "Y_Label": p_label, "SortKey": sort_base,
                "Faza": "2. Dni Targowe (Event)", "Start": klient_s, "Koniec": klient_k,
                "BarText": "DNI KLIENTA", 
                "HoverEvent": nazwa_bazy, "HoverID": "-", "HoverCarr": "-", "HoverDopisek": "-", "HoverFaza": "Dni Targowe"
            })
            
        if demontaz_s and demontaz_k:
            gantt_data.append({
                "UID": p_uid, "Y_Label": p_label, "SortKey": sort_base,
                "Faza": "3. Demontaż (Słownik)", "Start": demontaz_s, "Koniec": demontaz_k,
                "BarText": "DEMONTAŻ", 
                "HoverEvent": nazwa_bazy, "HoverID": "-", "HoverCarr": "-", "HoverDopisek": "-", "HoverFaza": "Demontaż"
            })

        # 2. Wiersze dla poszczególnych aut (Child)
        for _, row in group.iterrows():
            nr = str(row.get("ID_Zlecenia", ""))
            przewoznik = str(row.get("Przewoznik", "")).strip()
            nazwa_wyswietlana = przewoznik if przewoznik else nr
            
            auto_parts = str(row.get("Typ_Pojazdu", "")).split()
            auto = auto_parts[0] if auto_parts else "Pojazd"
            dopisek = str(row.get("Dopisek", ""))
            
            c_uid = f"CHILD_{nazwa_bazy}_{nr}"
            c_label = f"<span style='color: #A39B8F; font-size: 13px;'>&nbsp;&nbsp;&nbsp;&nbsp;↳ {nazwa_wyswietlana} [{auto}]</span>"
            sort_auto = f"{nazwa_bazy.upper()}_1_{nazwa_wyswietlana}_{nr}"
            
            zaladunek = parse_date(row.get("Data_Zlecenia_Tr"))
            powrot = parse_date(row.get("Data_Zakonczenia_Uslugi"))
            rozladunek = extract_rozladunek(row.get("Notatki"), klient_s)
            
            dem_auto_s, dem_auto_k = extract_demontaz(row.get("Notatki"), demontaz_s, demontaz_k)

            if not zaladunek: continue

            # Faza 1: DOSTAWA
            end_ph1 = rozladunek if rozladunek else (klient_s if klient_s else zaladunek)
            if end_ph1 < zaladunek: end_ph1 = zaladunek
            
            gantt_data.append({
                "UID": c_uid, "Y_Label": c_label, "SortKey": sort_auto,
                "Faza": "1. Transport & Montaż", "Start": zaladunek, "Koniec": end_ph1,
                "BarText": dopisek if dopisek else "DOSTAWA",
                "HoverEvent": nazwa_bazy, "HoverID": nr, "HoverCarr": nazwa_wyswietlana, "HoverDopisek": dopisek, "HoverFaza": "1. Transport & Montaż"
            })
            
            # Faza 3: DEMONTAŻ AUTO
            if not dem_auto_s: dem_auto_s = klient_k if klient_k else end_ph1
            if not dem_auto_k: dem_auto_k = dem_auto_s
                
            start_ph3 = dem_auto_s
            end_ph3 = dem_auto_k
            
            if start_ph3 and end_ph3:
                if start_ph3 < end_ph1: start_ph3 = end_ph1
                if end_ph3 < start_ph3: end_ph3 = start_ph3
                
                gantt_data.append({
                    "UID": c_uid, "Y_Label": c_label, "SortKey": sort_auto,
                    "Faza": "3. Demontaż (Auto)", "Start": start_ph3, "Koniec": end_ph3,
                    "BarText": dopisek if dopisek else "DEMONTAŻ",
                    "HoverEvent": nazwa_bazy, "HoverID": nr, "HoverCarr": nazwa_wyswietlana, "HoverDopisek": dopisek, "HoverFaza": "3. Demontaż i Załadunek"
                })

            # Faza 4: POWRÓT
            if powrot:
                start_ph4 = end_ph3 if (end_ph3 and end_ph3 > end_ph1) else end_ph1
                if start_ph4 > powrot: start_ph4 = powrot
                
                gantt_data.append({
                    "UID": c_uid, "Y_Label": c_label, "SortKey": sort_auto,
                    "Faza": "4. Powrót na bazę", "Start": start_ph4, "Koniec": powrot,
                    "BarText": "POWRÓT",
                    "HoverEvent": nazwa_bazy, "HoverID": nr, "HoverCarr": nazwa_wyswietlana, "HoverDopisek": dopisek, "HoverFaza": "4. Powrót na bazę"
                })

    if gantt_data:
        df_gantt = pd.DataFrame(gantt_data)
        df_gantt['Start'] = pd.to_datetime(df_gantt['Start'])
        df_gantt['Koniec'] = pd.to_datetime(df_gantt['Koniec'])
        
        # Poszerzenie paska, by jednodniowe eventy były kwadratami
        df_gantt['Koniec_Viz'] = df_gantt.apply(lambda x: x['Koniec'] + timedelta(days=1) if x['Start'] == x['Koniec'] else x['Koniec'] + timedelta(days=1), axis=1)

        # Logiczne sortowanie 
        df_gantt = df_gantt.sort_values(by=['SortKey', 'Start'])
        
        # Wyciągamy z posortowanego Dataframe unikalne ukryte UID oraz ich etykiety do wyświetlenia (bez zmiany kolejności)
        unique_ordered = df_gantt[['UID', 'Y_Label']].drop_duplicates()
        ordered_uids = unique_ordered['UID'].tolist()
        ordered_labels = unique_ordered['Y_Label'].tolist()

        color_map = {
            "1. Transport & Montaż": "#3B82F6",    
            "2. Dni Targowe (Event)": "#BA4949",   
            "3. Demontaż (Słownik)": "#5A544A",    
            "3. Demontaż (Auto)": "#C5A880",       
            "4. Powrót na bazę": "#10B981"         
        }

        height_calc = max(300, len(ordered_uids) * 45 + 150)

        fig = px.timeline(
            df_gantt, 
            x_start="Start", 
            x_end="Koniec_Viz", 
            y="UID",  # Używamy UKRYTEGO ID do prawidłowego i bezkolizyjnego grupowania!
            color="Faza",
            color_discrete_map=color_map,
            custom_data=["HoverEvent", "HoverID", "HoverCarr", "HoverDopisek", "HoverFaza", "BarText"]
        )

        # Profesjonalny, bogaty tooltip dla użytkownika (Hover Data)
        hovertemplate_html = (
            "<b style='font-size:14px;'>%{customdata[0]}</b><br><br>"
            "<b>Zlecenie:</b> %{customdata[1]}<br>"
            "<b>Przewoźnik:</b> %{customdata[2]}<br>"
            "<b>Dopisek:</b> %{customdata[3]}<br>"
            "<b>Faza:</b> %{customdata[4]}<br>"
            "<extra></extra>"
        )

        fig.update_traces(
            marker_line_width=1,
            marker_line_color='rgba(0,0,0,0.5)',
            hovertemplate=hovertemplate_html
        )

        # Magia nr 2: Wrzucamy czysty, dedykowany tekst do wnętrza paska (bez ID)
        for i, d in enumerate(fig.data):
            d.text = d.customdata[:, 5]
            d.textposition = 'inside'
            d.insidetextanchor = 'middle'
            d.textfont = dict(size=11, color='white', family="Inter", weight="bold")

        fig.add_vline(x=datetime.now(), line_width=2, line_dash="dash", line_color="#E2DCD3", annotation_text="📍 DZISIAJ", annotation_position="top", annotation_font_color="#C5A880", annotation_font_weight="bold")

        # Magia nr 3: Mówimy Plotly "Zignoruj to co masz na osi Y (brzydkie UID). Wyświetl zamiast nich sformatowane tagi HTML!"
        fig.update_yaxes(
            tickmode='array',
            tickvals=ordered_uids,
            ticktext=ordered_labels,
            autorange="reversed", 
            title="", 
            gridcolor='rgba(255, 255, 255, 0.05)'
        )
        
        fig.update_xaxes(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)', tickformat="%d.%m", title="", tickfont=dict(size=12, color='#A39B8F'), side="top")
        fig.update_layout(plot_bgcolor='#1C1A18', paper_bgcolor='#12100E', font=dict(color='#E2DCD3', family='Inter'), margin=dict(l=10, r=20, t=60, b=10), legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, title="", font=dict(color="#A39B8F", size=13)), height=height_calc)
        
        st.markdown('<div style="border: 1px solid rgba(197, 168, 128, 0.4); border-radius: 8px; padding: 10px; background-color: #12100E; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Brak wystarczających dat do wygenerowania osi czasu. Sprawdź, czy w Eventach (lub Słownikach) są poprawnie uzupełnione daty załadunku, rozładunku i targów.")
