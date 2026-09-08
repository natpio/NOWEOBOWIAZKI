import streamlit as st
import pandas as pd
import db
import io
import datetime

def parse_cost(val):
    """Bezpieczne parsowanie kosztów EUR (nawet z wpisami 'N/A' lub ze spacjami)"""
    try:
        val_str = str(val).strip().upper()
        if val_str in ["", "NAN", "NONE", "N/A", "FLOTA WŁASNA"]: return 0.0
        clean_val = val_str.replace(' ', '').replace(',', '.')
        return float(clean_val)
    except:
        return 0.0

def is_round_trip(val):
    """Sprawdza czy zlecenie miało datę powrotu (czyli 'w kółku')"""
    val_str = str(val).strip()
    return val_str not in ['', 'None', 'nan', 'NaT', 'Brak danych', 'N/A']

def render(sh):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Raportownia</h1>
            <div class="module-subtitle">レポート ✦ ANALYTICS & FLEET REPORTING</div>
        </div>
    ''', unsafe_allow_html=True)

    st.markdown("<p style='color: #8C8477; font-size: 13px; margin-bottom: 25px;'>Zintegrowane centrum analityczne. Łączy dane z bieżących operacji oraz archiwum (Cold Storage).</p>", unsafe_allow_html=True)

    with st.spinner("Agregacja danych ze wszystkich rejestrów..."):
        df_aktywne = db.fetch_data("DB_Eventy")
        df_arch = db.fetch_data("DB_Eventy ARCHIWUM")

    # Połączenie obydwu baz
    df_all = pd.concat([df_aktywne, df_arch], ignore_index=True)

    if df_all.empty:
        st.info("Brak jakichkolwiek zleceń w systemie (aktywnych i archiwalnych).")
        return

    # --- CZYSZCZENIE I STANDARYZACJA DANYCH ---
    df_all['Base_Event'] = df_all.get('Nazwa_Targow', '').apply(lambda x: str(x).split(" | ")[0].strip() if " | " in str(x) else str(x).strip())
    df_all['Przewoznik'] = df_all.get('Przewoznik', '').fillna('Nieokreślony').replace('', 'Nieokreślony')
    df_all['Typ_Pojazdu'] = df_all.get('Typ_Pojazdu', '').fillna('Nieokreślony').replace('', 'Nieokreślony')
    df_all['W_Kolku'] = df_all.get('Data_Zakonczenia_Uslugi', '').apply(is_round_trip)
    df_all['Zewnetrzny'] = df_all.get('Typ_Transportu', '') == 'Zewnętrzny'
    df_all['Wlasny'] = df_all.get('Typ_Transportu', '') == 'Własny SQM'
    df_all['Koszt_EUR'] = df_all.get('Koszt_Transportu_EUR', 0).apply(parse_cost)

    # --- AGREGACJA 1: PO EVENTACH ---
    raport_eventy = df_all.groupby('Base_Event').agg(
        Liczba_Aut=('ID_Zlecenia', 'count'),
        Auta_W_Kolku=('W_Kolku', 'sum'),
        Auta_Dostawa=('W_Kolku', lambda x: (~x).sum()),
        Flota_Zewnetrzna=('Zewnetrzny', 'sum'),
        Flota_SQM=('Wlasny', 'sum'),
        Koszt_Calkowity=('Koszt_EUR', 'sum')
    ).reset_index()
    raport_eventy = raport_eventy.sort_values(by='Liczba_Aut', ascending=False)

    # --- AGREGACJA 2: PO PRZEWOŹNIKACH ---
    raport_przewoznicy = df_all.groupby('Przewoznik').agg(
        Liczba_Zlecen=('ID_Zlecenia', 'count'),
        Obslugiwane_Eventy=('Base_Event', 'nunique'),
        Trasy_W_Kolku=('W_Kolku', 'sum'),
        Trasy_Drop=('W_Kolku', lambda x: (~x).sum()),
        Suma_Koszty=('Koszt_EUR', 'sum')
    ).reset_index()
    raport_przewoznicy = raport_przewoznicy.sort_values(by=['Suma_Koszty', 'Liczba_Zlecen'], ascending=[False, False])

    # --- AGREGACJA 3: RELACJE SZCZEGÓŁOWE (Kto, Gdzie, Czym) ---
    raport_relacje = df_all.groupby(['Przewoznik', 'Base_Event', 'Typ_Pojazdu', 'W_Kolku']).agg(
        Liczba_Kursow=('ID_Zlecenia', 'count'),
        Suma_Kosztow=('Koszt_EUR', 'sum')
    ).reset_index()
    raport_relacje['W_Kolku'] = raport_relacje['W_Kolku'].apply(lambda x: "🔄 W KÓŁKU" if x else "➡️ TYLKO DOSTAWA")
    raport_relacje = raport_relacje.sort_values(by=['Przewoznik', 'Base_Event', 'Liczba_Kursow'], ascending=[True, True, False])

    # --- KPI NA GÓRZE ---
    total_aut = int(raport_eventy['Liczba_Aut'].sum())
    total_koszt = raport_eventy['Koszt_Calkowity'].sum()
    total_eventow = len(raport_eventy)

    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card kpi-blue">
                <div class="kpi-header">Zrealizowane Eventy</div>
                <div class="kpi-value">{total_eventow}</div>
                <div class="kpi-icon-bg">🎪</div>
            </div>
            <div class="kpi-card kpi-gold">
                <div class="kpi-header">Wysłane Pojazdy</div>
                <div class="kpi-value">{total_aut}</div>
                <div class="kpi-icon-bg">🚛</div>
            </div>
            <div class="kpi-card kpi-red">
                <div class="kpi-header">Suma Kosztów Zewnętrznych</div>
                <div class="kpi-value">{total_koszt:,.2f} €</div>
                <div class="kpi-icon-bg">💶</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_eventy, tab_przewoznicy, tab_relacje, tab_szczegoly = st.tabs([
        "📊 Zbiorczo (Eventy)", 
        "🚚 Zbiorczo (Przewoźnicy)", 
        "🗺️ Relacje (Kto, Gdzie, Czym)",
        "🔍 Szczegóły Projektu"
    ])

    dzisiaj_str = datetime.datetime.now().strftime('%Y-%m-%d')

    with tab_eventy:
        st.markdown("<h4 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif; margin-bottom: 15px;'>Zestawienie Wolumenu i Kosztów per Event</h4>", unsafe_allow_html=True)
        
        df_disp_ev = raport_eventy.copy()
        df_disp_ev.columns = ["Główny Event", "Suma Aut", "W kółku (Powrót)", "Tylko Dostawa", "Zewnętrzni", "Własna Flota", "Koszt Zewnętrzny (€)"]
        
        st.dataframe(
            df_disp_ev, 
            use_container_width=True, 
            hide_index=True,
            column_config={"Koszt Zewnętrzny (€)": st.column_config.NumberColumn(format="%.2f €")}
        )

        c_csv_ev, c_xls_ev = st.columns(2)
        with c_csv_ev:
            st.download_button("📥 Pobierz zestawienie Eventów (.CSV)", data=df_disp_ev.to_csv(index=False).encode('utf-8'), file_name=f"Raport_Eventow_{dzisiaj_str}.csv", mime="text/csv", use_container_width=True)
        with c_xls_ev:
            buf_ev = io.BytesIO()
            with pd.ExcelWriter(buf_ev, engine='openpyxl') as writer: df_disp_ev.to_excel(writer, index=False, sheet_name='Raport_Eventow')
            st.download_button("📈 Pobierz zestawienie Eventów (.xlsx)", data=buf_ev.getvalue(), file_name=f"Raport_Eventow_{dzisiaj_str}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)

    with tab_przewoznicy:
        st.markdown("<h4 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif; margin-bottom: 15px;'>Zestawienie Partnerów i Wydatków</h4>", unsafe_allow_html=True)
        st.info("💡 Tabela pokazuje, z jakimi przewoźnikami współpracujesz najczęściej oraz jak rozkładają się koszty (EUR) na poszczególne firmy transportowe.")
        
        df_disp_przew = raport_przewoznicy.copy()
        df_disp_przew.columns = ["Firma Transportowa / Przewoźnik", "Liczba Zleceń", "Ilość Obsłużonych Eventów", "Tras w kółku", "Tras (Dostawy / Dropy)", "Wygenerowane Koszty (€)"]
        
        st.dataframe(
            df_disp_przew, 
            use_container_width=True, 
            hide_index=True,
            column_config={"Wygenerowane Koszty (€)": st.column_config.NumberColumn(format="%.2f €")}
        )

        c_csv_przew, c_xls_przew = st.columns(2)
        with c_csv_przew:
            st.download_button("📥 Pobierz zestawienie Przewoźników (.CSV)", data=df_disp_przew.to_csv(index=False).encode('utf-8'), file_name=f"Raport_Przewoznikow_{dzisiaj_str}.csv", mime="text/csv", use_container_width=True)
        with c_xls_przew:
            buf_przew = io.BytesIO()
            with pd.ExcelWriter(buf_przew, engine='openpyxl') as writer: df_disp_przew.to_excel(writer, index=False, sheet_name='Raport_Przewoznikow')
            st.download_button("📈 Pobierz zestawienie Przewoźników (.xlsx)", data=buf_przew.getvalue(), file_name=f"Raport_Przewoznikow_{dzisiaj_str}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)

    with tab_relacje:
        st.markdown("<h4 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif; margin-bottom: 15px;'>Szczegółowe Relacje Transportowe</h4>", unsafe_allow_html=True)
        st.info("📍 W tym miejscu sprawdzisz precyzyjnie, jakiej wielkości autem dany przewoźnik pojechał na konkretny event i czy była to pełna pętla, czy jedynie zrzutka (drop).")

        df_disp_rel = raport_relacje.copy()
        df_disp_rel.columns = ["Przewoźnik", "Event / Targi", "Typ Pojazdu (Wielkość)", "Rodzaj Trasy", "Liczba takich kursów", "Suma Kosztów za te kursy (€)"]

        st.dataframe(
            df_disp_rel, 
            use_container_width=True, 
            hide_index=True,
            column_config={"Suma Kosztów za te kursy (€)": st.column_config.NumberColumn(format="%.2f €")}
        )

        c_csv_rel, c_xls_rel = st.columns(2)
        with c_csv_rel:
            st.download_button("📥 Pobierz Relacje (.CSV)", data=df_disp_rel.to_csv(index=False).encode('utf-8'), file_name=f"Relacje_Przewoznikow_{dzisiaj_str}.csv", mime="text/csv", use_container_width=True)
        with c_xls_rel:
            buf_rel = io.BytesIO()
            with pd.ExcelWriter(buf_rel, engine='openpyxl') as writer: df_disp_rel.to_excel(writer, index=False, sheet_name='Relacje')
            st.download_button("📈 Pobierz Relacje (.xlsx)", data=buf_rel.getvalue(), file_name=f"Relacje_Przewoznikow_{dzisiaj_str}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)

    with tab_szczegoly:
        st.markdown("<p style='color: #C5A880; font-size: 13px; font-weight: bold;'>Wybierz event, aby zobaczyć dokładną listę aut i kosztów, które się na niego złożyły:</p>", unsafe_allow_html=True)
        
        lista_eventow = raport_eventy['Base_Event'].tolist()
        wybrany_event = st.selectbox("Wybierz Event:", ["-- Wybierz --"] + lista_eventow, label_visibility="collapsed")
        
        if wybrany_event != "-- Wybierz --":
            df_szczegoly = df_all[df_all['Base_Event'] == wybrany_event].copy()
            
            st.markdown(f"<h3 style='color: #BA4949; margin-top: 15px;'>Rozbicie kosztów: {wybrany_event}</h3>", unsafe_allow_html=True)
            
            detale_widok = df_szczegoly[[
                'ID_Zlecenia', 'Nazwa_Targow', 'Typ_Pojazdu', 'Przewoznik', 
                'W_Kolku', 'Data_Zlecenia_Tr', 'Data_Zakonczenia_Uslugi', 'Koszt_EUR'
            ]].copy()
            
            detale_widok['W_Kolku'] = detale_widok['W_Kolku'].apply(lambda x: "🔄 W KÓŁKU" if x else "➡️ DOSTAWA")
            
            detale_widok.columns = [
                "ID Zlecenia", "Dopisek (Sub-projekt)", "Auto", "Przewoźnik", 
                "Rodzaj Trasy", "Wyjazd", "Powrót", "Koszt Netto (€)"
            ]
            
            st.dataframe(
                detale_widok,
                use_container_width=True,
                hide_index=True,
                column_config={"Koszt Netto (€)": st.column_config.NumberColumn(format="%.2f €")}
            )
            
            koszt_suma_detale = detale_widok['Koszt Netto (€)'].sum()
            st.markdown(f"""
                <div style='text-align: right; margin-top: 10px; font-size: 18px; color: #E2DCD3;'>
                    Łączny koszt transportu dla tego projektu: <b style='color: #BA4949;'>{koszt_suma_detale:,.2f} €</b>
                </div>
            """, unsafe_allow_html=True)
