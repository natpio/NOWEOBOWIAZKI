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

def render(sh):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Raportownia</h1>
            <div class="module-subtitle">レポート ✦ ANALYTICS & FLEET REPORTING</div>
        </div>
    ''', unsafe_allow_html=True)

    st.markdown("<p style='color: #8C8477; font-size: 13px; margin-bottom: 25px;'>Zintegrowane centrum analityczne. Filtruj zlecenia według Eventów lub Przewoźników, aby na bieżąco kontrolować koszty i statusy.</p>", unsafe_allow_html=True)

    with st.spinner("Agregacja wszystkich zleceń (Aktywne + Cold Storage)..."):
        # 1. POBRANIE EVENTÓW
        df_ev_akt = db.fetch_data("DB_Eventy")
        df_ev_arch = db.fetch_data("DB_Eventy ARCHIWUM")
        df_ev = pd.concat([df_ev_akt, df_ev_arch], ignore_index=True)
        
        # 2. POBRANIE ZLECEŃ POBOCZNYCH
        df_pob_akt = db.fetch_data("Zlecenia Poboczne")
        df_pob_arch = db.fetch_data("Zlecenia Poboczne ARCHIWUM")
        df_pob = pd.concat([df_pob_akt, df_pob_arch], ignore_index=True)

    # --- STANDARYZACJA EVENTÓW ---
    if not df_ev.empty:
        df_ev['Base_Event'] = df_ev.get('Nazwa_Targow', '').apply(lambda x: str(x).split(" | ")[0].strip() if " | " in str(x) else str(x).strip())
        df_ev['Przewoznik'] = df_ev.get('Przewoznik', '').fillna('Nieokreślony').replace('', 'Nieokreślony')
        df_ev['Typ_Pojazdu'] = df_ev.get('Typ_Pojazdu', '').fillna('-').replace('', '-')
        df_ev['Koszt_EUR'] = df_ev.get('Koszt_Transportu_EUR', 0).apply(parse_cost)
        df_ev['Faza_Procesu'] = df_ev.get('Faza_Procesu', 'BRAK STATUSU')
        df_ev['Zakonczone'] = df_ev.get('Zakonczone_Arch', 'NIE')
        # Ujednolicenie dat
        df_ev['Data_Zaladunku'] = df_ev.get('Data_Zlecenia_Tr', '').fillna('-').replace('', '-')
        df_ev['Data_Rozladunku'] = df_ev.get('Data_Zakonczenia_Uslugi', '').fillna('-').replace('', '-')

    # --- STANDARYZACJA ZLECEŃ POBOCZNYCH (Dopasowanie kolumn pod Audyt) ---
    if not df_pob.empty:
        df_pob['ID_Zlecenia'] = df_pob.get('Nr Zlecenia', '')
        df_pob['Przewoznik'] = df_pob.get('Przewoźnik', '').fillna('Nieokreślony').replace('', 'Nieokreślony')
        df_pob['Base_Event'] = df_pob.get('Opis Ładunku / Trasy', '').astype(str) + " [POBOCZNE]" 
        df_pob['Nazwa_Targow'] = df_pob['Base_Event']
        df_pob['Typ_Pojazdu'] = '-'
        df_pob['Koszt_EUR'] = 0.0 # W zleceniach pobocznych nie wpisujecie kwot
        df_pob['Faza_Procesu'] = df_pob.get('Status', 'BRAK STATUSU')
        df_pob['Zakonczone'] = df_pob.get('Status', '').apply(lambda x: 'TAK' if str(x).upper() == 'ARCHIWUM' else 'NIE')
        df_pob['Nr_Faktury'] = df_pob.get('Nr Faktury', '')
        df_pob['Faktura_Oplacona'] = df_pob.get('Faktura', '')
        df_pob['Data_Platnosci'] = df_pob.get('Data Płatności', '')
        # Ujednolicenie dat
        df_pob['Data_Zaladunku'] = df_pob.get('Data Załadunku', '').fillna('-').replace('', '-')
        df_pob['Data_Rozladunku'] = df_pob.get('Data Rozładunku', '').fillna('-').replace('', '-')

    # --- POŁĄCZENIE WSZYSTKIEGO W JEDEN MEGA-REJESTR ---
    df_all = pd.concat([df_ev, df_pob], ignore_index=True)

    if df_all.empty:
        st.info("Brak jakichkolwiek zleceń w systemie (aktywnych i archiwalnych).")
        return

    # --- KPI NA GÓRZE ---
    total_aut = len(df_all)
    total_koszt = df_all['Koszt_EUR'].sum()
    total_eventow = df_all['Base_Event'].nunique()

    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card kpi-blue">
                <div class="kpi-header">Zrealizowane Eventy</div>
                <div class="kpi-value">{total_eventow}</div>
                <div class="kpi-icon-bg">🎪</div>
            </div>
            <div class="kpi-card kpi-gold">
                <div class="kpi-header">Suma Zleceń (Aut)</div>
                <div class="kpi-value">{total_aut}</div>
                <div class="kpi-icon-bg">🚛</div>
            </div>
            <div class="kpi-card kpi-red">
                <div class="kpi-header">Koszty Zewnętrzne</div>
                <div class="kpi-value">{total_koszt:,.2f} €</div>
                <div class="kpi-icon-bg">💶</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_event, tab_przewoznik, tab_ogolne = st.tabs([
        "🎪 Analiza wybranego Eventu", 
        "🚚 Audyt Przewoźnika (Faktury)", 
        "📈 Zbiorczy Dashboard"
    ])

    dzisiaj_str = datetime.datetime.now().strftime('%Y-%m-%d')

    # =======================================================
    # ZAKŁADKA 1: ANALIZA EVENTU (ILE AUT, KTO, KWOTY, NUMERY)
    # =======================================================
    with tab_event:
        st.markdown("<h4 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif;'>Wybierz event, aby sprawdzić kto i za ile na niego pojechał</h4>", unsafe_allow_html=True)
        
        lista_eventow = sorted(df_all['Base_Event'].unique().tolist())
        wybrany_event = st.selectbox("Wybierz event:", ["-- Wybierz z listy --"] + lista_eventow, key="sel_ev")

        if wybrany_event != "-- Wybierz z listy --":
            df_ev_view = df_all[df_all['Base_Event'] == wybrany_event].copy()
            koszt_ev = df_ev_view['Koszt_EUR'].sum()
            aut_ev = len(df_ev_view)

            st.markdown(f"""
            <div style='background: rgba(186, 73, 73, 0.1); border-left: 4px solid #BA4949; padding: 15px; margin-bottom: 20px; border-radius: 0 4px 4px 0;'>
                <h3 style='margin:0; color:#E2DCD3;'>Podsumowanie: {wybrany_event}</h3>
                <p style='margin:0; color:#A39B8F; font-size: 14px;'>Na ten event wysłano łącznie <strong style='color:#C5A880; font-size: 18px;'>{aut_ev} aut</strong>. Suma kosztów to <strong style='color:#BA4949; font-size: 18px;'>{koszt_ev:,.2f} €</strong>.</p>
            </div>
            """, unsafe_allow_html=True)

            view_ev = df_ev_view[['ID_Zlecenia', 'Przewoznik', 'Typ_Pojazdu', 'Data_Zaladunku', 'Data_Rozladunku', 'Faza_Procesu', 'Koszt_EUR']].copy()
            view_ev['Faza_Procesu'] = view_ev['Faza_Procesu'].apply(lambda x: str(x).upper())
            view_ev.columns = ['Numer Zlecenia', 'Przewoźnik', 'Auto', 'Data Załadunku', 'Data Rozładunku', 'Status Zlecenia', 'Koszt Netto (€)']
            
            st.dataframe(
                view_ev, 
                use_container_width=True, 
                hide_index=True, 
                column_config={"Koszt Netto (€)": st.column_config.NumberColumn(format="%.2f €")}
            )

            c_csv, c_xls, _ = st.columns([1, 1, 2])
            with c_csv:
                st.download_button("📥 Pobierz CSV", data=view_ev.to_csv(index=False).encode('utf-8'), file_name=f"Raport_{wybrany_event}_{dzisiaj_str}.csv", mime="text/csv", use_container_width=True)
            with c_xls:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as writer: view_ev.to_excel(writer, index=False, sheet_name='Event')
                st.download_button("📈 Pobierz Excel", data=buf.getvalue(), file_name=f"Raport_{wybrany_event}_{dzisiaj_str}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    # =======================================================
    # ZAKŁADKA 2: ZESTAWIENIE PRZEWOŹNIKA (AUDYT FAKTUR I STATUSÓW)
    # =======================================================
    with tab_przewoznik:
        st.markdown("<h4 style='color: #E2DCD3; font-family: \"Shippori Mincho\", serif;'>Audyt Zleceń i Faktur Przewoźnika</h4>", unsafe_allow_html=True)
        
        lista_przewoznikow = sorted(df_all['Przewoznik'].unique().tolist())
        wybrani_przewoznicy = st.multiselect("Wybierz jednego lub kilku przewoźników do zestawienia:", lista_przewoznikow, key="sel_przew_multi")

        if wybrani_przewoznicy:
            df_pr = df_all[df_all['Przewoznik'].isin(wybrani_przewoznicy)].copy()
            
            df_pr['Nr_Faktury'] = df_pr.get('Nr_Faktury', '').fillna('-').replace('', '-')
            df_pr['Faktura_Oplacona'] = df_pr.get('Faktura_Oplacona', 'NIE').fillna('NIE').replace('', 'NIE')
            df_pr['Data_Platnosci'] = df_pr.get('Data_Platnosci', '').fillna('-').replace('', '-')
            
            koszt_pr = df_pr['Koszt_EUR'].sum()
            dlug_pr = df_pr[df_pr['Faktura_Oplacona'] != 'TAK']['Koszt_EUR'].sum()
            
            nazwy_display = ", ".join(wybrani_przewoznicy) if len(wybrani_przewoznicy) <= 3 else f"{len(wybrani_przewoznicy)} wybranych firm"

            st.markdown(f"""
            <div style='background: rgba(197, 168, 128, 0.1); border-left: 4px solid #C5A880; padding: 15px; margin-bottom: 20px; border-radius: 0 4px 4px 0;'>
                <h3 style='margin:0; color:#E2DCD3;'>Audyt Finansowy: <span style='color:#C5A880; font-size: 20px;'>{nazwy_display}</span></h3>
                <p style='margin:0; color:#A39B8F; font-size: 14px;'>
                    Suma wszystkich wygenerowanych kosztów (w EUR): <strong style='color:#C5A880; font-size: 16px;'>{koszt_pr:,.2f} €</strong>.<br>
                    Kwota wciąż <b>NIEOPŁACONA</b> w systemie: <strong style='color:#BA4949; font-size: 18px;'>{dlug_pr:,.2f} €</strong>.
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Wyciągamy na wierzch nowe kolumny Dat załadunku i rozładunku
            view_pr = df_pr[['ID_Zlecenia', 'Przewoznik', 'Nazwa_Targow', 'Data_Zaladunku', 'Data_Rozladunku', 'Faza_Procesu', 'Koszt_EUR', 'Nr_Faktury', 'Faktura_Oplacona', 'Data_Platnosci']].copy()
            
            # Formatyzacja kolumn dla czytelności
            view_pr['Faza_Procesu'] = view_pr['Faza_Procesu'].apply(lambda x: str(x).upper())
            view_pr['Faktura_Oplacona'] = view_pr['Faktura_Oplacona'].apply(lambda x: "✅ TAK" if str(x).upper() == "TAK" else "❌ NIE")
            
            view_pr.columns = ['Numer Zlecenia', 'Przewoźnik', 'Event / Trasa', 'Data Załadunku', 'Data Rozładunku', 'Status Zlecenia', 'Kwota Netto (€)', 'Nr Faktury Zewn.', 'Opłacona?', 'Data Płatności']
            
            st.dataframe(
                view_pr, 
                use_container_width=True, 
                hide_index=True, 
                column_config={
                    "Kwota Netto (€)": st.column_config.NumberColumn(format="%.2f €"),
                    "Opłacona?": st.column_config.TextColumn(width="small")
                }
            )

            file_suffix = "_".join(wybrani_przewoznicy).replace(" ", "")[:30] if len(wybrani_przewoznicy) <= 2 else "Wielu_Przewoznikow"

            c_csv2, c_xls2, _ = st.columns([1, 1, 2])
            with c_csv2:
                st.download_button("📥 Pobierz do CSV (do analizy)", data=view_pr.to_csv(index=False).encode('utf-8'), file_name=f"Audyt_Faktur_{file_suffix}_{dzisiaj_str}.csv", mime="text/csv", key="csv2", use_container_width=True)
            with c_xls2:
                buf2 = io.BytesIO()
                with pd.ExcelWriter(buf2, engine='openpyxl') as writer: view_pr.to_excel(writer, index=False, sheet_name='Audyt')
                st.download_button("📈 Pobierz do Excela", data=buf2.getvalue(), file_name=f"Audyt_Faktur_{file_suffix}_{dzisiaj_str}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="xls2", use_container_width=True)

    # =======================================================
    # ZAKŁADKA 3: ZBIORCZY DASHBOARD (DLA ZARZĄDU)
    # =======================================================
    with tab_ogolne:
        st.info("💡 Zbiorcze zestawienie wszystkich wydatków. W tym widoku widzisz podsumowanie sumaryczne dla całego systemu (łącznie z archiwum i zleceniami pobocznymi).")
        col_og_1, col_og_2 = st.columns(2)
        
        with col_og_1:
            st.markdown("<h5 style='color:#C5A880;'>🏆 Zestawienie kosztowe Eventów</h5>", unsafe_allow_html=True)
            agg_ev = df_all.groupby('Base_Event').agg(Auta=('ID_Zlecenia','count'), Koszt=('Koszt_EUR','sum')).reset_index()
            agg_ev = agg_ev.sort_values('Koszt', ascending=False)
            agg_ev.columns = ['Nazwa Eventu', 'Ilość Aut / Zleceń', 'Łączny Koszt (€)']
            st.dataframe(agg_ev, use_container_width=True, hide_index=True, column_config={"Łączny Koszt (€)": st.column_config.NumberColumn(format="%.2f €")})
        
        with col_og_2:
            st.markdown("<h5 style='color:#C5A880;'>🏆 Zestawienie Przewoźników (Wolumen)</h5>", unsafe_allow_html=True)
            agg_pr = df_all.groupby('Przewoznik').agg(Zlecenia=('ID_Zlecenia','count'), Koszt=('Koszt_EUR','sum')).reset_index()
            agg_pr = agg_pr.sort_values('Zlecenia', ascending=False)
            agg_pr.columns = ['Przewoźnik', 'Ilość Zleceń', 'Zarobek u nas (€)']
            st.dataframe(agg_pr, use_container_width=True, hide_index=True, column_config={"Zarobek u nas (€)": st.column_config.NumberColumn(format="%.2f €")})
