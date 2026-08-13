import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import re
import db

def normalize_date(d_str, return_as_str=False):
    if pd.isna(d_str) or not str(d_str).strip():
        return None
    d_str = str(d_str).strip()
    try:
        if "," in d_str:
            d_str = d_str.split(",")[-1].strip()
        if "." in d_str:
            dt = datetime.strptime(d_str, "%d.%m.%Y")
        else:
            dt = datetime.strptime(d_str.split(" ")[0], "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d") if return_as_str else dt
    except:
        return None

def extract_end_date_from_notes(notatki, start_date):
    if pd.isna(notatki):
        return start_date
    notatki = str(notatki)
    match = re.search(r'\[Rozładunki:\s*([^\]]+)\]', notatki)
    if match:
        dates_str = match.group(1)
        extracted = normalize_date(dates_str, return_as_str=True)
        return extracted if extracted else start_date
    return start_date

def draw_gantt_chart(df_plot, kolor_paska):
    """Nowy, wysoce czytelny render wykresu Gantta z grubymi paskami i tekstem."""
    
    # Dynamiczna wysokość dająca dużo przestrzeni na tekst (60px na wiersz)
    unikalne_zasoby = len(df_plot['Zasób'].unique())
    height_calc = max(200, unikalne_zasoby * 60 + 100) 
    
    fig = px.timeline(
        df_plot, 
        x_start="Start_DT", 
        x_end="Koniec_Viz", 
        y="Zasób", 
        text="Zlecenie", # Magiczna właściwość - wrzuca nazwy bezpośrednio w paski!
        hover_name="Zlecenie",
        custom_data=["Start_Str", "Koniec_Str", "Liczba Dni"],
        color_discrete_sequence=[kolor_paska]
    )
    
    # Customizacja grubości pasków i tekstu
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br><br>Zajętość od: %{customdata[0]}<br>Zajętość do: %{customdata[1]}<br>Czas trwania: %{customdata[2]} dni<extra></extra>",
        width=0.75,  # Pogrubione paski
        textposition='inside', # Tekst wymuszony wewnątrz paska
        textfont=dict(size=12, color='white', family="Inter", weight="bold"),
        insidetextanchor='middle'
    )
    
    fig.update_yaxes(
        autorange="reversed", 
        title="",
        tickfont=dict(size=13, color='#E2DCD3', family='Inter', weight="bold"),
        showgrid=True,
        gridcolor='rgba(255, 255, 255, 0.03)'
    )
    
    fig.update_xaxes(
        showgrid=True, 
        gridwidth=1,
        gridcolor='rgba(255, 255, 255, 0.15)', # Wyraźniejsza pionowa siatka
        tickformat="%d.%m",
        title="",
        tickfont=dict(size=12, color='#A39B8F'),
        side="top" # Oś czasu przeniesiona na górę dla łatwiejszego czytania
    )
    
    # Wyłączona przezroczystość - solidne tło zapewnia maksymalny kontrast!
    fig.update_layout(
        plot_bgcolor='#1C1A18', 
        paper_bgcolor='#12100E',
        font=dict(color='#E2DCD3', family='Inter'),
        margin=dict(l=10, r=20, t=40, b=10),
        showlegend=False,
        height=height_calc
    )
    return fig

def render(sh):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Harmonogram Transportów</h1>
            <div class="module-subtitle">ガントチャート ✦ TRANSPORT TIMELINE (GANTT)</div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown("""
        <p style="color: #8C8477; font-size: 13px; margin-bottom: 25px;">Wizualizacja "z lotu ptaka" z wyraźnym podziałem na kategorię sprzętu i przewoźników. Nazwy zleceń widoczne są bezpośrednio na wykresie.</p>
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
                elif pojazd: zasob = f"🚛 SQM AUTO: {pojazd}"
                else: zasob = "🚛 FLOTA SQM (Nieokreślona)"
                kategoria = "Flota Własna SQM"
            else:
                przewoznik = str(row.get("Przewoznik", "")).strip()
                zasob = f"🏢 {przewoznik}" if przewoznik else "🏢 ZEWNĘTRZNY: Nieznany"
                kategoria = "Zewnętrzni (Eventy/PRO)"
                
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
                "Kategoria": "Zewnętrzni (Eventy/PRO)"
            })
            
    # 3. Zlecenia Poboczne
    if not df_zlp.empty:
        df_zlp_akt = df_zlp[df_zlp.get("Status", pd.Series()) != "ARCHIWUM"]
        for _, row in df_zlp_akt.iterrows():
            nr = str(row.get("Nr Zlecenia", ""))
            
            # Pomijamy zlecenia, które już wpadły jako PRO lub EVT
            if str(nr).startswith("CRG") or str(nr).startswith("EVT"):
                continue 
                
            start = normalize_date(row.get("Data Załadunku"), return_as_str=True)
            end = normalize_date(row.get("Data Rozładunku"), return_as_str=True)
            
            if not start: continue
            if not end: end = start
            
            przewoznik = str(row.get("Przewoźnik", "")).strip()
            
            tasks.append({
                "Zlecenie": f"[POB] {nr}",
                "Start": start,
                "Koniec": end,
                "Zasób": f"🏢 {przewoznik}",
                "Kategoria": "Zewnętrzni (Poboczne)"
            })

    if not tasks:
        st.info("Brak aktywnych zleceń z przypisanymi datami, aby wygenerować harmonogram.")
        return

    df_gantt = pd.DataFrame(tasks)
    
    # --- PRZETWARZANIE DAT ---
    df_gantt['Start_DT'] = pd.to_datetime(df_gantt['Start'])
    df_gantt['Koniec_DT'] = pd.to_datetime(df_gantt['Koniec'])
    
    # Obliczanie fizycznej liczby dni zlecenia
    df_gantt['Liczba Dni'] = (df_gantt['Koniec_DT'] - df_gantt['Start_DT']).dt.days + 1
    
    # Trick graficzny dla Plotly (+1 dzień dla pełnej szerokości paska w ostatnim dniu)
    df_gantt['Koniec_Viz'] = df_gantt['Koniec_DT'] + pd.Timedelta(days=1)
    
    df_gantt['Start_Str'] = df_gantt['Start_DT'].dt.strftime('%d.%m.%Y')
    df_gantt['Koniec_Str'] = df_gantt['Koniec_DT'].dt.strftime('%d.%m.%Y')
    
    df_gantt = df_gantt.sort_values(by=["Kategoria", "Zasób", "Start_DT"], ascending=[True, False, True])

    # --- ZAKŁADKI GŁÓWNE MODUŁU ---
    tab_eventy, tab_poboczne, tab_raport = st.tabs([
        "🎪 Eventy, PRO i Flota", 
        "🚚 Zlecenia Poboczne", 
        "🧾 Tabela i Zapotrzebowanie (Raport)"
    ])

    # ==========================================
    # ZAKŁADKA 1: EVENTY I FLOTA WŁASNA
    # ==========================================
    with tab_eventy:
        st.markdown("<p style='font-size: 13px; color: #8C8477;'>Wyszukaj konkretnego kierowcę lub firmę:</p>", unsafe_allow_html=True)
        wyszukaj_ev = st.text_input("Szukaj:", placeholder="np. 'SQM', 'Jan Kowalski', 'FRANTRANS'", key="ev_search", label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 1.1 Pod-wykres: TYLKO FLOTA SQM
        df_sqm = df_gantt[df_gantt['Kategoria'] == "Flota Własna SQM"].copy()
        if wyszukaj_ev: df_sqm = df_sqm[df_sqm['Zasób'].str.contains(wyszukaj_ev, case=False, na=False)]
            
        if not df_sqm.empty:
            st.markdown("<h4 style='color: #C5A880; font-family: \"Shippori Mincho\", serif;'>🟡 Nasi Kierowcy i Pojazdy SQM</h4>", unsafe_allow_html=True)
            fig_sqm = draw_gantt_chart(df_sqm, kolor_paska="#C5A880") # Złoty
            st.plotly_chart(fig_sqm, use_container_width=True, config={'displayModeBar': False})
            st.markdown("<br>", unsafe_allow_html=True)

        # 1.2 Pod-wykres: TYLKO ZEWNĘTRZNI EVENTY/PRO
        df_zewn = df_gantt[df_gantt['Kategoria'] == "Zewnętrzni (Eventy/PRO)"].copy()
        if wyszukaj_ev: df_zewn = df_zewn[df_zewn['Zasób'].str.contains(wyszukaj_ev, case=False, na=False)]
            
        if not df_zewn.empty:
            st.markdown("<h4 style='color: #3B82F6; font-family: \"Shippori Mincho\", serif;'>🔵 Przewoźnicy Zewnętrzni (Duże Eventy)</h4>", unsafe_allow_html=True)
            fig_zewn = draw_gantt_chart(df_zewn, kolor_paska="#3B82F6") # Niebieski
            st.plotly_chart(fig_zewn, use_container_width=True, config={'displayModeBar': False})
        
        if df_sqm.empty and df_zewn.empty:
            st.warning("Brak wyników dla podanej frazy w tej zakładce.")

    # ==========================================
    # ZAKŁADKA 2: ZLECENIA POBOCZNE
    # ==========================================
    with tab_poboczne:
        df_pob = df_gantt[df_gantt['Kategoria'] == "Zewnętrzni (Poboczne)"].copy()
        
        if not df_pob.empty:
            wyszukaj_pob = st.text_input("Szukaj Przewoźnika:", placeholder="Wpisz fragment nazwy...", key="pob_search", label_visibility="collapsed")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if wyszukaj_pob: df_pob = df_pob[df_pob['Zasób'].str.contains(wyszukaj_pob, case=False, na=False)]
                
            if not df_pob.empty:
                st.markdown("<h4 style='color: #10B981; font-family: \"Shippori Mincho\", serif;'>🟢 Podwykonawcy (Zlecenia Poboczne)</h4>", unsafe_allow_html=True)
                fig_pob = draw_gantt_chart(df_pob, kolor_paska="#10B981") # Szmaragdowy
                st.plotly_chart(fig_pob, use_container_width=True, config={'displayModeBar': False})
            else:
                st.warning("Brak wyników dla podanej frazy.")
        else:
            st.info("Brak aktywnych Zleceń Pobocznych z datami.")

    # ==========================================
    # ZAKŁADKA 3: RAPORT I EKSPORT
    # ==========================================
    with tab_raport:
        st.markdown("### 📝 Raport Zapotrzebowania na Flotę / Przewoźników")
        st.info("Ten widok pozwala wyeksportować dokładną, posortowaną chronologicznie listę dni roboczych, w których dany kierowca lub firma transportowa będzie w trasie.")
        
        zakres_raportu = st.radio(
            "Wybierz zakres generowanego raportu:", 
            ["Wszystko (Zbiorczy)", "Tylko Flota Własna SQM", "Tylko Eventy i PRO", "Tylko Zlecenia Poboczne"], 
            horizontal=True
        )
        
        if zakres_raportu == "Tylko Flota Własna SQM":
            df_raport_baza = df_gantt[df_gantt['Kategoria'] == "Flota Własna SQM"]
        elif zakres_raportu == "Tylko Eventy i PRO":
            df_raport_baza = df_gantt[df_gantt['Kategoria'].isin(["Flota Własna SQM", "Zewnętrzni (Eventy/PRO)"])]
        elif zakres_raportu == "Tylko Zlecenia Poboczne":
            df_raport_baza = df_gantt[df_gantt['Kategoria'] == "Zewnętrzni (Poboczne)"]
        else:
            df_raport_baza = df_gantt
            
        df_raport = df_raport_baza[['Kategoria', 'Zasób', 'Zlecenie', 'Start_Str', 'Koniec_Str', 'Liczba Dni']].copy()
        df_raport.columns = ['Kategoria', 'Kierowca / Przewoźnik', 'Numer Zlecenia', 'Od (Data)', 'Do (Data)', 'Czas (Dni)']
        
        df_raport['Kierowca / Przewoźnik'] = df_raport['Kierowca / Przewoźnik'].str.replace('🧑‍✈️ SQM: ', '')
        df_raport['Kierowca / Przewoźnik'] = df_raport['Kierowca / Przewoźnik'].str.replace('🚛 AUTO SQM: ', '')
        df_raport['Kierowca / Przewoźnik'] = df_raport['Kierowca / Przewoźnik'].str.replace('🏢 ', '')
        
        df_raport['Sort_DT'] = pd.to_datetime(df_raport['Od (Data)'], format="%d.%m.%Y")
        df_raport = df_raport.sort_values(by=['Kategoria', 'Kierowca / Przewoźnik', 'Sort_DT']).drop(columns=['Sort_DT'])
        
        st.dataframe(df_raport, use_container_width=True, hide_index=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_csv, col_xls = st.columns(2)
        dzisiaj_str = datetime.today().strftime('%Y-%m-%d')
        
        with col_csv:
            csv_data = df_raport.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📊 Pobierz raport harmonogramu (.CSV)",
                data=csv_data,
                file_name=f"Harmonogram_{dzisiaj_str}.csv",
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
                file_name=f"Harmonogram_{dzisiaj_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
