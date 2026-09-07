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
        d = parse_date(dates[-1].strip()) # Bierzemy ostatni rozładunek
        if d: return d
    return fallback

def render(sh):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Timeline Eventów</h1>
            <div class="module-subtitle">イベントのタイムライン ✦ PROJECT LIFECYCLE GANTT</div>
        </div>
    ''', unsafe_allow_html=True)

    st.markdown("<p style='color: #8C8477; font-size: 13px; margin-bottom: 20px;'>Graficzne odzwierciedlenie cyklu życia targów. System automatycznie grupuje auta i ładunki przypisane do tego samego wydarzenia.</p>", unsafe_allow_html=True)

    # 1. Pobieranie danych
    with st.spinner("Ładowanie osi czasu..."):
        try:
            ws_ev, df_ev = db.load_data(sh, "DB_Eventy")
            ws_etapy, df_etapy = db.load_data(sh, "DB_Event_Etapy")
        except Exception as e:
            st.error(f"Błąd ładowania danych: {e}")
            return

        # Automatyczne utworzenie struktury nowej bazy
        if df_etapy.empty and len(df_etapy.columns) <= 1:
            headers = ["Nazwa_Targow", "Targi_Start", "Targi_Koniec", "Demontaz_Start", "Demontaz_Koniec"]
            ws_etapy.clear()
            ws_etapy.append_row(headers)
            st.cache_data.clear()
            _, df_etapy = db.load_data(sh, "DB_Event_Etapy")

    # 2. Filtrowanie aktywnych eventów
    df_aktywne = df_ev[df_ev.get("Zakonczone_Arch", pd.Series()) != "TAK"].copy() if not df_ev.empty else pd.DataFrame()

    if df_aktywne.empty:
        st.info("Brak aktywnych eventów w bazie.")
        return

    # Normalizacja nazw targów
    df_aktywne["Nazwa_Targow"] = df_aktywne["Nazwa_Targow"].astype(str).str.strip()

    # 3. Transformacja danych do kaskadowego wykresu Gantta
    gantt_data = []

    # GRUPOWANIE PO NAZWIE TARGÓW
    grouped = df_aktywne.groupby("Nazwa_Targow")

    for nazwa, group in grouped:
        if not nazwa or nazwa in ["nan", "None", ""]: 
            continue
            
        # Pobieranie wspólnych etapów dla tych konkretnych targów
        etapy_row = df_etapy[df_etapy.iloc[:, 0].astype(str).str.strip() == nazwa] if not df_etapy.empty else pd.DataFrame()
        
        targi_s, targi_k, demontaz_s, demontaz_k = None, None, None, None
        if not etapy_row.empty:
            r_et = etapy_row.iloc[0]
            cols = df_etapy.columns.tolist()
            targi_s = parse_date(r_et.get(cols[1])) if len(cols) > 1 else None
            targi_k = parse_date(r_et.get(cols[2])) if len(cols) > 2 else None
            demontaz_s = parse_date(r_et.get(cols[3])) if len(cols) > 3 else None
            demontaz_k = parse_date(r_et.get(cols[4])) if len(cols) > 4 else None

        # --- BLOKI WSPÓLNE (Dni Targowe i Demontaż) ---
        # Dodawane tylko raz per wydarzenie (Event)
        if targi_s and targi_k:
            gantt_data.append({
                "Zlecenie": nazwa, 
                "Faza": "2. Dni Targowe (Event)", 
                "Start": targi_s, 
                "Koniec": targi_k,
                "Szczegoly": "DZIEŃ KLIENTA"
            })
            
        if demontaz_s and demontaz_k:
            gantt_data.append({
                "Zlecenie": nazwa, 
                "Faza": "3. Demontaż", 
                "Start": demontaz_s, 
                "Koniec": demontaz_k,
                "Szczegoly": "DEMONTAŻ"
            })

        # --- BLOKI NIEZALEŻNE (Dla każdego pojazdu w ramach eventu) ---
        for _, row in group.iterrows():
            nr = str(row.get("ID_Zlecenia", ""))
            
            # Bezpieczne pobieranie typu pojazdu (ZABEZPIECZENIE PRZED INDEX ERROR)
            auto_parts = str(row.get("Typ_Pojazdu", "")).split()
            auto = auto_parts[0] if auto_parts else "Pojazd"
            
            zaladunek = parse_date(row.get("Data_Zlecenia_Tr"))
            powrot = parse_date(row.get("Data_Zakonczenia_Uslugi"))
            rozladunek = extract_rozladunek(row.get("Notatki"), targi_s)

            if not zaladunek: continue

            # Faza 1: Transport IN (Załadunek -> Rozładunek lub Start Targów)
            end_ph1 = rozladunek if rozladunek else (targi_s if targi_s else zaladunek)
            if end_ph1 < zaladunek: end_ph1 = zaladunek
            
            gantt_data.append({
                "Zlecenie": nazwa, 
                "Faza": "1. Transport & Montaż", 
                "Start": zaladunek, 
                "Koniec": end_ph1,
                "Szczegoly": f"{nr} [{auto}]"
            })

            # Faza 4: Transport OUT (Powrót)
            if powrot:
                # Kiedy auto wyjeżdża z powrotem? Po demontażu, po targach lub po prostu po załadunku.
                start_ph4 = demontaz_k if demontaz_k else (targi_k if targi_k else end_ph1)
                # Zapobieganie błędom logiki (cofa się w czasie)
                if start_ph4 > powrot: start_ph4 = powrot
                
                gantt_data.append({
                    "Zlecenie": nazwa, 
                    "Faza": "4. Powrót na bazę", 
                    "Start": start_ph4, 
                    "Koniec": powrot,
                    "Szczegoly": f"{nr} [{auto}]"
                })

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
        # Wykres rośnie wraz z ilością unikalnych targów
        height_calc = max(300, unikalne_zlecenia * 85 + 150)

        fig = px.timeline(
            df_gantt, 
            x_start="Start", 
            x_end="Koniec_Viz", 
            y="Zlecenie", 
            color="Faza",
            color_discrete_map=color_map,
            custom_data=["Faza", "Szczegoly"],
            hover_name="Szczegoly"
        )

        fig.update_traces(
            width=0.75,
            hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]}<br>Od: %{x[0]}<br>Do: %{x[1]}<extra></extra>",
            marker_line_width=1,
            marker_line_color='rgba(0,0,0,0.5)'
        )

        # Magia: Wrzucamy fizycznie napis z kolumny "Szczegoly" do środka paska
        for i, d in enumerate(fig.data):
            d.text = d.customdata[:, 1]
            d.textposition = 'inside'
            d.insidetextanchor = 'middle'
            d.textfont = dict(size=11, color='white', family="Inter", weight="bold")

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
            tickfont=dict(size=16, color='#E2DCD3', family='Inter', weight="bold"),
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

    # 5. Formularz uzupełniania brakujących etapów
    st.markdown("<hr style='border-color: rgba(197, 168, 128, 0.2); margin: 35px 0 20px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #C5A880; font-family: \"Shippori Mincho\", serif;'>⚙️ Uzupełnij etapy dla targów</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8C8477; font-size: 13px;'>Ustaw daty raz dla wydarzenia. Puste pola powodują pominięcie etapu na wykresie.</p>", unsafe_allow_html=True)

    with st.form("form_etapy_targow"):
        opcje_targow = sorted(df_aktywne["Nazwa_Targow"].unique().tolist())
        wybrany_ev = st.selectbox("Wybierz event (Nazwa Targów) do zsynchronizowania dat:", ["Wybierz..."] + opcje_targow)
        
        c1, c2 = st.columns(2)
        
        if wybrany_ev != "Wybierz...":
            akt_row = df_etapy[df_etapy.iloc[:, 0].astype(str).str.strip() == wybrany_ev] if not df_etapy.empty else pd.DataFrame()
            cols = df_etapy.columns.tolist() if not df_etapy.empty else ["Nazwa_Targow", "Targi_Start", "Targi_Koniec", "Demontaz_Start", "Demontaz_Koniec"]
            
            d_t_s = parse_date(akt_row.iloc[0].get(cols[1])) if not akt_row.empty and len(cols) > 1 else datetime.now().date()
            d_t_k = parse_date(akt_row.iloc[0].get(cols[2])) if not akt_row.empty and len(cols) > 2 else datetime.now().date()
            d_d_s = parse_date(akt_row.iloc[0].get(cols[3])) if not akt_row.empty and len(cols) > 3 else datetime.now().date()
            d_d_k = parse_date(akt_row.iloc[0].get(cols[4])) if not akt_row.empty and len(cols) > 4 else datetime.now().date()
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
                if not df_etapy.empty and wybrany_ev in df_etapy.iloc[:, 0].values:
                    idx = df_etapy[df_etapy.iloc[:, 0] == wybrany_ev].index[0]
                    cols = df_etapy.columns.tolist()
                    df_etapy.at[idx, cols[1]] = str(targi_start)
                    df_etapy.at[idx, cols[2]] = str(targi_koniec)
                    df_etapy.at[idx, cols[3]] = str(demontaz_start)
                    df_etapy.at[idx, cols[4]] = str(demontaz_koniec)
                    gs_row = int(df_etapy.at[idx, "sheet_row"])
                    db.update_single_row_safe("DB_Event_Etapy", gs_row, df_etapy.loc[idx])
                else:
                    nowy_wiersz = [wybrany_ev, str(targi_start), str(targi_koniec), str(demontaz_start), str(demontaz_koniec)]
                    db.append_data("DB_Event_Etapy", nowy_wiersz)
                st.success(f"Zaktualizowano wykres osi czasu dla: {wybrany_ev}!")
                st.rerun()
            else:
                st.error("Wybierz targi z listy, aby zapisać ich etapy.")
