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
        # Usuń spacje i zamień przecinki na kropki
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

    # Połączenie obydwu baz (z pominięciem błędów, jeśli archiwum jest puste)
    df_all = pd.concat([df_aktywne, df_arch], ignore_index=True)

    if df_all.empty:
        st.info("Brak jakichkolwiek zleceń w systemie (aktywnych i archiwalnych).")
        return

    # --- CZYSZCZENIE I STANDARYZACJA DANYCH ---
    # 1. Wyciągamy główną nazwę eventu (ucinamy wszystko po " | ")
    df_all['Base_Event'] = df_all.get('Nazwa_Targow', '').apply(
        lambda x: str(x).split(" | ")[0].strip() if " | " in str(x) else str(x).strip()
    )
    
    # 2. Identyfikacja trasy (W kółku vs Tylko dostawa)
    df_all['W_Kolku'] = df_all.get('Data_Zakonczenia_Uslugi', '').apply(is_round_trip)
    
    # 3. Typ floty
    df_all['Zewnetrzny'] = df_all.get('Typ_Transportu', '') == 'Zewnętrzny'
    df_all['Wlasny'] = df_all.get('Typ_Transportu', '') == 'Własny SQM'
    
    # 4. Koszty
    df_all['Koszt_EUR'] = df_all.get('Koszt_Transportu_EUR', 0).apply(parse_cost)

    # --- AGREGACJA (TABELA GŁÓWNA) ---
    raport_eventy = df_all.groupby('Base_Event').agg(
        Liczba_Aut=('ID_Zlecenia', 'count'),
        Auta_W_Kolku=('W_Kolku', 'sum'),
        Auta_Dostawa=('W_Kolku', lambda x: (~x).sum()),
        Flota_Zewnetrzna=('Zewnetrzny', 'sum'),
        Flota_SQM=('Wlasny', 'sum'),
        Koszt_Calkowity=('Koszt_EUR', 'sum')
    ).reset_index()

    # Sortowanie po największej liczbie aut
    raport_eventy = raport_eventy.sort_values(by='Liczba_Aut', ascending=False)

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

    tab_zbiorczy, tab_szczegoly = st.tabs(["📊 Zbiorcze Zestawienie Eventów", "🔍 Szczegóły Konkretnego Projektu"])

    with tab_zbiorczy:
        st.markdown("<h4 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif; margin-bottom: 15px;'>Zestawienie Wolumenu i Kosztów</h4>", unsafe_allow_html=True)
        
        # Formatowanie dataframe do wyświetlenia
        df_display = raport_eventy.copy()
        df_display.columns = ["Główny Event", "Suma Aut", "W kółku (Powrót)", "Tylko Dostawa", "Zewnętrzni", "Własna Flota", "Koszt Zewnętrzny (€)"]
        
        st.dataframe(
            df_display, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Koszt Zewnętrzny (€)": st.column_config.NumberColumn(format="%.2f €")
            }
        )

        col_csv, col_xls = st.columns(2)
        dzisiaj_str = datetime.datetime.now().strftime('%Y-%m-%d')
        
        with col_csv:
            csv_data = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Pobierz zestawienie (.CSV)",
                data=csv_data,
                file_name=f"Raport_Eventow_{dzisiaj_str}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_xls:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df_display.to_excel(writer, index=False, sheet_name='Raport_Wolumenowy')
            excel_data = excel_buffer.getvalue()
            
            st.download_button(
                label="📈 Pobierz zestawienie (.xlsx)",
                data=excel_data,
                file_name=f"Raport_Eventow_{dzisiaj_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

    with tab_szczegoly:
        st.markdown("<p style='color: #C5A880; font-size: 13px; font-weight: bold;'>Wybierz event, aby zobaczyć dokładną listę aut i kosztów, które się na niego złożyły:</p>", unsafe_allow_html=True)
        
        lista_eventow = raport_eventy['Base_Event'].tolist()
        wybrany_event = st.selectbox("Wybierz Event:", ["-- Wybierz --"] + lista_eventow, label_visibility="collapsed")
        
        if wybrany_event != "-- Wybierz --":
            df_szczegoly = df_all[df_all['Base_Event'] == wybrany_event].copy()
            
            st.markdown(f"<h3 style='color: #BA4949; margin-top: 15px;'>Rozbicie kosztów: {wybrany_event}</h3>", unsafe_allow_html=True)
            
            # Przygotowanie tabeli szczegółowej
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
                column_config={
                    "Koszt Netto (€)": st.column_config.NumberColumn(format="%.2f €")
                }
            )
            
            koszt_suma_detale = detale_widok['Koszt Netto (€)'].sum()
            st.markdown(f"""
                <div style='text-align: right; margin-top: 10px; font-size: 18px; color: #E2DCD3;'>
                    Łączny koszt transportu dla tego projektu: <b style='color: #BA4949;'>{koszt_suma_detale:,.2f} €</b>
                </div>
            """, unsafe_allow_html=True)
