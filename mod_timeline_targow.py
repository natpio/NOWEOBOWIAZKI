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
        # Obsługa formatów YYYY-MM-DD i DD.MM.YYYY
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
        d = parse_date(dates[0])
        if d: return d
    return fallback

def render(sh):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Timeline Eventów</h1>
            <div class="module-subtitle">イベントのタイムライン ✦ PROJECT LIFECYCLE GANTT</div>
        </div>
    ''', unsafe_allow_html=True)

    st.markdown("<p style='color: #8C8477; font-size: 13px; margin-bottom: 20px;'>Graficzne odzwierciedlenie cyklu życia targów. Pasek każdego projektu jest podzielony na odrębne fazy kolorystyczne. Uzupełnij daty na dole ekranu, aby wykres był kompletny.</p>", unsafe_allow_html=True)

    # 1. Pobieranie danych
    with st.spinner("Ładowanie osi czasu..."):
        _, df_ev = db.load_data(sh, "DB_Eventy")
        _, df_etapy = db.load_data(sh, "DB_Event_Etapy")

        # Automatyczne utworzenie struktury nowej bazy, jeśli jeszcze nie istnieje
        if df_etapy.empty and len(df_etapy.columns) <= 1:
            headers = ["ID_Zlecenia", "Targi_Start", "Targi_Koniec", "Demontaz_Start", "Demontaz_Koniec"]
            sh.worksheet("DB_Event_Etapy").append_row(headers)
            st.cache_data.clear()
            _, df_etapy = db.load_data(sh, "DB_Event_Etapy")

    # 2. Filtrowanie aktywnych eventów
    df_aktywne = df_ev[df_ev.get("Zakonczone_Arch", pd.Series()) != "TAK"].copy() if not df_ev.empty else pd.DataFrame()

    if df_aktywne.empty:
        st.info("Brak aktywnych eventów w bazie.")
        return

    # 3. Transformacja danych do kaskadowego wykresu Gantta
    gantt_data = []

    for _, row in df_aktywne.iterrows():
        id_zlecenia = str(row.get("ID_Zlecenia", ""))
        nazwa = str(row.get("Nazwa_Targow", id_zlecenia))
        
        zaladunek = parse_date(row.get("Data_Zlecenia_Tr"))
        powrot = parse_date(row.get("Data_Zakonczenia_Uslugi"))
        rozladunek = extract_rozladunek(row.get("Notatki"), zaladunek)

        if not zaladunek: continue

        # Pobieranie dodatkowych etapów z DB_Event_Etapy
        etapy_row = df_etapy[df_etapy["ID_Zlecenia"] == id_zlecenia] if not df_etapy.empty and "ID_Zlecenia" in df_etapy.columns else pd.DataFrame()
        
        targi_s, targi_k, demontaz_s, demontaz_k = None, None, None, None
        if not etapy_row.empty:
            r_et = etapy_row.iloc[0]
            targi_s = parse_date(r_et.get("Targi_Start"))
            targi_k = parse_date(r_et.get("Targi_Koniec"))
            demontaz_s = parse_date(r_et.get("Demontaz_Start"))
            demontaz_k = parse_date(r_et.get("Demontaz_Koniec"))

        # FAZA 1: Transport & Montaż (Niebieski)
        end_ph1 = rozladunek if rozladunek else (targi_s if targi_s else zaladunek)
        if end_ph1 < zaladunek: end_ph1 = zaladunek
        gantt_data.append({"Zlecenie": nazwa, "Faza": "1. Transport & Montaż", "Start": zaladunek, "Koniec": end_ph1})

        # FAZA 2: Dni Klienta (Czerwony)
        if targi_s and targi_k:
            start_ph2 = max(end_ph1, targi_s)
            gantt_data.append({"Zlecenie": nazwa, "Faza": "2. Dni Targowe (Event)", "Start": start_ph2, "Koniec": targi_k})
            end_ph2 = targi_k
        else:
            end_ph2 = end_ph1

        # FAZA 3: Demontaż (Złoty)
        if demontaz_s and demontaz_k:
            start_ph3 = max(end_ph2, demontaz_s)
            gantt_data.append({"Zlecenie": nazwa, "Faza": "3. Demontaż", "Start": start_ph3, "Koniec": demontaz_k})
            end_ph3 = demontaz_k
        else:
            end_ph3 = end_ph2

        # FAZA 4: Powrót (Zielony)
        if powrot and powrot >= end_ph3:
            gantt_data.append({"Zlecenie": nazwa, "Faza": "4. Powrót na bazę", "Start": end_ph3, "Koniec": powrot})

    # 4. Renderowanie wykresu Plotly
    if gantt_data:
        df_gantt = pd.DataFrame(gantt_data)
        df_gantt['Start'] = pd.to_datetime(df_gantt['Start'])
        df_gantt['Koniec'] = pd.to_datetime(df_gantt['Koniec'])
        
        # Optyczne poszerzenie paska o 1 dzień, aby jednodniowe etapy były widoczne jako kwadraty
        df_gantt['Koniec_Viz'] = df_gantt.apply(lambda x: x['Koniec'] + timedelta(days=1) if x['Start'] == x['Koniec'] else x['Koniec'] + timedelta(days=1), axis=1)

        color_map = {
            "1. Transport & Montaż": "#3B82F6",    # Blue
            "2. Dni Targowe (Event)": "#BA4949",   # Crimson/Red
            "3. Demontaż": "#C5A880",              # Gold
            "4. Powrót na bazę": "#10B981"         # Emerald Green
        }

        unikalne_zlecenia = len(df_gantt['Zlecenie'].unique())
        height_calc = max(300, unikalne_zlecenia * 55 + 150)

        fig = px.timeline(
            df_gantt, 
            x_start="Start", 
            x_end="Koniec_Viz", 
            y="Zlecenie", 
            color="Faza",
            color_discrete_map=color_map,
            text="Faza",
            hover_name="Zlecenie"
        )

        fig.update_traces(
            width=0.7,
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(size=12, color='white', family="Inter", weight="bold"),
            marker_line_width=1,
            marker_line_color='rgba(0,0,0,0.5)'
        )

        # Dodanie pionowej, przerywanej linii oznaczającej "Dzisiaj"
        fig.add_vline(
            x=datetime.now(), 
            line_width=2, 
            line_dash="dash", 
            line_color="#E2DCD3", 
            annotation_text="📍 DZISIAJ", 
            annotation_position="top",
            annotation_font_color="#C5A880",
            annotation_font_weight="bold"
        )

        fig.update_yaxes(
            autorange="reversed", 
            title="",
            tickfont=dict(size=14, color='#E2DCD3', family='Inter', weight="bold"),
            gridcolor='rgba(255, 255, 255, 0.05)'
        )

        fig.update_xaxes(
            showgrid=True, 
            gridcolor='rgba(255, 255, 255, 0.1)',
            tickformat="%d.%m",
            title="",
            tickfont=dict(size=12, color='#A39B8F'),
            side="top"
        )

        fig.update_layout(
            plot_bgcolor='#1C1A18', 
            paper_bgcolor='#12100E',
            font=dict(color='#E2DCD3', family='Inter'),
            margin=dict(l=10, r=20, t=60, b=10),
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5,
                title="", font=dict(color="#A39B8F", size=13)
            ),
            height=height_calc
        )
        
        st.markdown('<div style="border: 1px solid rgba(197, 168, 128, 0.4); border-radius: 8px; padding: 10px; background-color: #12100E; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Brak wystarczających dat do wygenerowania osi czasu.")

    # 5. Formularz uzupełniania brakujących etapów dla aktywnych eventów
    st.markdown("<hr style='border-color: rgba(197, 168, 128, 0.2); margin: 35px 0 20px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #C5A880; font-family: \"Shippori Mincho\", serif;'>⚙️ Uzupełnij etapy dla logistyki</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8C8477; font-size: 13px;'>Puste daty w tych polach są pomijane na wykresie. Wypełnij je, aby wykres nabrał kolorów.</p>", unsafe_allow_html=True)

    with st.form("form_etapy_targow"):
        opcje_eventow = (df_aktywne["ID_Zlecenia"] + " | " + df_aktywne["Nazwa_Targow"]).tolist()
        wybrany_ev = st.selectbox("Wybierz event do uzupełnienia dat:", ["Wybierz..."] + opcje_eventow)
        
        c1, c2 = st.columns(2)
        
        if wybrany_ev != "Wybierz...":
            ev_id = wybrany_ev.split(" | ")[0]
            akt_row = df_etapy[df_etapy["ID_Zlecenia"] == ev_id] if not df_etapy.empty and "ID_Zlecenia" in df_etapy.columns else pd.DataFrame()
            
            d_t_s = parse_date(akt_row.iloc[0].get("Targi_Start")) if not akt_row.empty else datetime.now().date()
            d_t_k = parse_date(akt_row.iloc[0].get("Targi_Koniec")) if not akt_row.empty else datetime.now().date()
            d_d_s = parse_date(akt_row.iloc[0].get("Demontaz_Start")) if not akt_row.empty else datetime.now().date()
            d_d_k = parse_date(akt_row.iloc[0].get("Demontaz_Koniec")) if not akt_row.empty else datetime.now().date()
        else:
            d_t_s, d_t_k, d_d_s, d_d_k = datetime.now().date(), datetime.now().date(), datetime.now().date(), datetime.now().date()
            
        with c1:
            st.markdown("<div style='background: rgba(186, 73, 73, 0.1); padding: 15px; border-radius: 6px; border: 1px solid rgba(186, 73, 73, 0.3);'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color: #BA4949; margin-top: 0;'>🎪 Dni Targowe (Dzień Klienta)</h4>", unsafe_allow_html=True)
            targi_start = st.date_input("Rozpoczęcie targów:", value=d_t_s)
            targi_koniec = st.date_input("Zakończenie targów:", value=d_t_k)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c2:
            st.markdown("<div style='background: rgba(197, 168, 128, 0.1); padding: 15px; border-radius: 6px; border: 1px solid rgba(197, 168, 128, 0.3);'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color: #C5A880; margin-top: 0;'>🛠️ Demontaż</h4>", unsafe_allow_html=True)
            demontaz_start = st.date_input("Rozpoczęcie demontażu:", value=d_d_s)
            demontaz_koniec = st.date_input("Zakończenie demontażu:", value=d_d_k)
            st.markdown("</div>", unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("💾 Zapisz Etapy do Kalendarza", type="primary", use_container_width=True):
            if wybrany_ev != "Wybierz...":
                ev_id = wybrany_ev.split(" | ")[0]
                
                if not df_etapy.empty and ev_id in df_etapy["ID_Zlecenia"].values:
                    idx = df_etapy[df_etapy["ID_Zlecenia"] == ev_id].index[0]
                    df_etapy.at[idx, "Targi_Start"] = str(targi_start)
                    df_etapy.at[idx, "Targi_Koniec"] = str(targi_koniec)
                    df_etapy.at[idx, "Demontaz_Start"] = str(demontaz_start)
                    df_etapy.at[idx, "Demontaz_Koniec"] = str(demontaz_koniec)
                    gs_row = int(df_etapy.at[idx, "sheet_row"])
                    db.update_single_row_safe("DB_Event_Etapy", gs_row, df_etapy.loc[idx])
                else:
                    nowy_wiersz = [ev_id, str(targi_start), str(targi_koniec), str(demontaz_start), str(demontaz_koniec)]
                    db.append_data("DB_Event_Etapy", nowy_wiersz)
                st.success("Zaktualizowano wykres osi czasu!")
                st.rerun()
            else:
                st.error("Wybierz event z listy, aby zapisać jego etapy.")
