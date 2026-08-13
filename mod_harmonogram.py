import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import re
import db

def normalize_date(d_str, return_as_str=False):
    """Zmienia dowolny tekst na obiekt datetime lub string formatu YYYY-MM-DD."""
    if pd.isna(d_str) or not str(d_str).strip():
        return None
    d_str = str(d_str).strip()
    try:
        # Obsługa listy dat po przecinku (bierzemy ostatnią)
        if "," in d_str:
            d_str = d_str.split(",")[-1].strip()
            
        if "." in d_str:
            dt = datetime.strptime(d_str, "%d.%m.%Y")
        else:
            # Ucina ewentualne godziny (bierzemy samą datę)
            dt = datetime.strptime(d_str.split(" ")[0], "%Y-%m-%d")
            
        return dt.strftime("%Y-%m-%d") if return_as_str else dt
    except:
        return None

def extract_end_date_from_notes(notatki, start_date):
    """Próbuje wyłuskać datę z tagu [Rozładunki: ...] w notatkach."""
    if pd.isna(notatki):
        return start_date
    notatki = str(notatki)
    match = re.search(r'\[Rozładunki:\s*([^\]]+)\]', notatki)
    if match:
        dates_str = match.group(1)
        extracted = normalize_date(dates_str, return_as_str=True)
        return extracted if extracted else start_date
    return start_date

def render(sh):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Harmonogram Transportów</h1>
            <div class="module-subtitle">ガントチャート ✦ TRANSPORT TIMELINE (GANTT)</div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown("""
        <p style="color: #8C8477; font-size: 13px; margin-bottom: 25px;">Wizualizacja "z lotu ptaka" pokazująca, w jakich dniach zablokowani są konkretni Przewoźnicy oraz Kierowcy z Floty SQM.</p>
    """, unsafe_allow_html=True)
    
    with st.spinner("Pobieranie i agregacja danych kalendarzowych z 3 modułów..."):
        try:
            _, df_ev = db.load_data(sh, "DB_Eventy")
            _, df_zl = db.load_data(sh, "Zlecenia")
            _, df_zlp = db.load_data(sh, "Zlecenia Poboczne")
        except Exception as e:
            st.error(f"Błąd ładowania danych: {e}")
            return
            
    tasks = []
    
    # 1. DB_Eventy (Moduł Eventy / Flota)
    if not df_ev.empty:
        df_aktywne = df_ev[df_ev.get("Zakonczone_Arch", pd.Series()) != "TAK"]
        for _, row in df_aktywne.iterrows():
            start = normalize_date(row.get("Data_Zlecenia_Tr"), return_as_str=True)
            if not start: continue
                
            end = extract_end_date_from_notes(row.get("Notatki", ""), start)
            typ = str(row.get("Typ_Transportu", ""))
            
            if typ == "Własny SQM":
                kierowca = str(row.get("Kierowca", "")).strip()
                pojazd = str(row.get("Nr_Rejestracyjny", "")).strip()
                if kierowca: zasob = f"🧑‍✈️ SQM: {kierowca}"
                elif pojazd: zasob = f"🚛 AUTO SQM: {pojazd}"
                else: zasob = "🚛 FLOTA SQM (Nieokreślona)"
                kategoria = "Flota Własna SQM"
            else:
                przewoznik = str(row.get("Przewoznik", "")).strip()
                zasob = f"🏢 {przewoznik}" if przewoznik else "🏢 ZEWNĘTRZNY: Nieznany"
                kategoria = "Zewnętrzni Przewoźnicy"
                
            zlecenie = str(row.get("ID_Zlecenia", "")) or str(row.get("Nazwa_Targow", "Brak nazwy"))
            
            tasks.append({
                "Zlecenie": f"[EVENT] {zlecenie}",
                "Start": start,
                "Koniec": end,
                "Zasób": zasob,
                "Kategoria": kategoria
            })
            
    # 2. Zlecenia PRO (Główna tabela logistyki)
    if not df_zl.empty:
        for _, row in df_zl.iterrows():
            start = normalize_date(row.get("Data załadunku"), return_as_str=True)
            end = normalize_date(row.get("Data rozładunku"), return_as_str=True)
            
            if not start: continue
            if not end: end = start
                
            przewoznik = str(row.get("Zleceniobiorca", "")).strip()
            nr = str(row.get("Numer zlecenia", ""))
            
            tasks.append({
                "Zlecenie": f"[PRO] {nr}",
                "Start": start,
                "Koniec": end,
                "Zasób": f"🏢 {przewoznik}",
                "Kategoria": "Zewnętrzni Przewoźnicy"
            })
            
    # 3. Zlecenia Poboczne
    if not df_zlp.empty:
        df_zlp_akt = df_zlp[df_zlp.get("Status", pd.Series()) != "ARCHIWUM"]
        for _, row in df_zlp_akt.iterrows():
            nr = str(row.get("Nr Zlecenia", ""))
            
            # Pomijamy zlecenia, które już wpadły jako PRO lub EVT (żeby uniknąć dublowania pasków na osi)
            if str(nr).startswith("CRG") or str(nr).startswith("EVT"):
                continue 
                
            start = normalize_date(row.get("Data Załadunku"), return_as_str=True)
            end = normalize_date(row.get("Data Rozładunku"), return_as_str=True)
            
            if not start: continue
            if not end: end = start
            
            przewoznik = str(row.get("Przewoźnik", "")).strip()
            
            tasks.append({
                "Zlecenie": f"[POBOCZNE] {nr}",
                "Start": start,
                "Koniec": end,
                "Zasób": f"🏢 {przewoznik}",
                "Kategoria": "Zewnętrzni Przewoźnicy"
            })

    if not tasks:
        st.info("Brak aktywnych zleceń z przypisanymi datami, aby wygenerować harmonogram.")
        return

    df_gantt = pd.DataFrame(tasks)
    
    # --- PRZETWARZANIE DAT DLA SILNIKA PLOTLY I RAPORTÓW ---
    df_gantt['Start_DT'] = pd.to_datetime(df_gantt['Start'])
    df_gantt['Koniec_DT'] = pd.to_datetime(df_gantt['Koniec'])
    
    # Obliczanie fizycznej liczby dni zlecenia
    df_gantt['Liczba Dni'] = (df_gantt['Koniec_DT'] - df_gantt['Start_DT']).dt.days + 1
    
    # Trick graficzny dla Plotly
    df_gantt['Koniec_Viz'] = df_gantt['Koniec_DT'] + pd.Timedelta(days=1)
    
    # Zapis tekstowy dla tooltipów i tabeli raportowej
    df_gantt['Start_Str'] = df_gantt['Start_DT'].dt.strftime('%d.%m.%Y')
    df_gantt['Koniec_Str'] = df_gantt['Koniec_DT'].dt.strftime('%d.%m.%Y')
    
    # Wstępne sortowanie
    df_gantt = df_gantt.sort_values(by=["Kategoria", "Zasób", "Start_DT"], ascending=[True, False, True])

    # Interfejs filtrów
    st.markdown("### 🔍 Opcje widoku i Raportowanie")
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        wybrane_kategorie = st.multiselect(
            "Filtruj Kategorie:", 
            ["Flota Własna SQM", "Zewnętrzni Przewoźnicy"], 
            default=["Flota Własna SQM", "Zewnętrzni Przewoźnicy"]
        )
    with c_f2:
        wyszukaj_zasob = st.text_input("Szukaj Kierowcy / Przewoźnika (np. 'SQM', 'Jan Kowalski')", placeholder="Wpisz fragment nazwy...")
        
    if not wybrane_kategorie:
        st.warning("Wybierz przynajmniej jedną kategorię zasobów.")
        return
        
    df_filtered = df_gantt[df_gantt['Kategoria'].isin(wybrane_kategorie)]
    
    if wyszukaj_zasob:
        df_filtered = df_filtered[df_filtered['Zasób'].str.contains(wyszukaj_zasob, case=False, na=False)]

    if df_filtered.empty:
        st.warning("Brak wyników dla podanych filtrów.")
        return

    # --- ZAKŁADKI: WYKRES ORAZ TABELA RAPORTOWA ---
    tab_wykres, tab_raport = st.tabs(["📊 Wykres Wizualny", "🧾 Tabela i Zapotrzebowanie (Raport)"])

    # 1. WIDOK GRAFICZNY GANTTA
    with tab_wykres:
        fig = px.timeline(
            df_filtered, 
            x_start="Start_DT", 
            x_end="Koniec_Viz", 
            y="Zasób", 
            color="Kategoria",
            hover_name="Zlecenie",
            custom_data=["Start_Str", "Koniec_Str", "Liczba Dni"],
            color_discrete_map={
                "Flota Własna SQM": "#C5A880",       # SQM Gold
                "Zewnętrzni Przewoźnicy": "#3B82F6"  # Niebieski Corporate
            }
        )
        
        # Customizacja Dymka (Hover)
        fig.update_traces(
            hovertemplate="<b>%{hovertext}</b><br><br>Zajętość od: %{customdata[0]}<br>Zajętość do: %{customdata[1]}<br>Czas trwania: %{customdata[2]} dni<extra></extra>",
            width=0.4 # Estetyczna grubość paska
        )
        
        # Oś Y odwrócona, żeby "A" było na górze
        fig.update_yaxes(autorange="reversed") 
        
        # Inteligentna wysokość - kalendarz rośnie, jeśli dodasz dużo kierowców
        height_calc = max(400, len(df_filtered['Zasób'].unique()) * 40 + 120)
        
        fig.update_layout(
            plot_bgcolor='rgba(28, 26, 24, 0.6)',
            paper_bgcolor='rgba(18, 16, 14, 0)',
            font=dict(color='#E2DCD3', family='Inter'),
            margin=dict(l=10, r=20, t=30, b=20),
            xaxis=dict(
                showgrid=True, 
                gridcolor='rgba(197, 168, 128, 0.15)',
                tickformat="%d\n%b",
                title=""
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(197, 168, 128, 0.05)',
                title="",
                tickfont=dict(size=12, color='#E2DCD3')
            ),
            legend=dict(
                title="", 
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1
            ),
            height=height_calc
        )

        st.markdown('<div style="background: rgba(28, 26, 24, 0.8); backdrop-filter: blur(10px); padding: 15px; border-radius: 12px; border: 1px solid rgba(197, 168, 128, 0.3); box-shadow: 0 4px 20px rgba(0,0,0,0.5);">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    # 2. WIDOK TABELI RAPORTOWEJ I EKSPORTU
    with tab_raport:
        st.markdown("### 📝 Raport Zapotrzebowania na Flotę / Przewoźników")
        st.info("Ten widok pozwala wyeksportować dokładną, posortowaną chronologicznie listę dni roboczych, w których dany kierowca lub firma transportowa będzie w trasie.")
        
        # Przygotowanie eleganckiej tabeli do wyświetlenia
        df_raport = df_filtered[['Kategoria', 'Zasób', 'Zlecenie', 'Start_Str', 'Koniec_Str', 'Liczba Dni']].copy()
        df_raport.columns = ['Kategoria', 'Kierowca / Przewoźnik', 'Numer Zlecenia', 'Od (Data)', 'Do (Data)', 'Czas (Dni)']
        
        # Oczyszczenie przedrostków "🧑‍✈️ SQM:" z tabeli, żeby Excel był czysty
        df_raport['Kierowca / Przewoźnik'] = df_raport['Kierowca / Przewoźnik'].str.replace('🧑‍✈️ SQM: ', '')
        df_raport['Kierowca / Przewoźnik'] = df_raport['Kierowca / Przewoźnik'].str.replace('🚛 AUTO SQM: ', '')
        df_raport['Kierowca / Przewoźnik'] = df_raport['Kierowca / Przewoźnik'].str.replace('🏢 ', '')
        
        # Sortowanie na nowo
        df_raport['Sort_DT'] = pd.to_datetime(df_raport['Od (Data)'], format="%d.%m.%Y")
        df_raport = df_raport.sort_values(by=['Kategoria', 'Kierowca / Przewoźnik', 'Sort_DT']).drop(columns=['Sort_DT'])
        
        st.dataframe(df_raport, use_container_width=True, hide_index=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Sekcja pobierania
        col_csv, col_xls = st.columns(2)
        dzisiaj_str = datetime.today().strftime('%Y-%m-%d')
        
        with col_csv:
            csv_data = df_raport.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📊 Pobierz raport harmonogramu (.CSV)",
                data=csv_data,
                file_name=f"Harmonogram_Flota_{dzisiaj_str}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_xls:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df_raport.to_excel(writer, index=False, sheet_name='Harmonogram')
            excel_data = excel_buffer.getvalue()
            
            st.download_button(
                label="📈 Pobierz raport harmonogramu (.xlsx)",
                data=excel_data,
                file_name=f"Harmonogram_Flota_{dzisiaj_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
