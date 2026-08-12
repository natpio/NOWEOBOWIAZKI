import streamlit as st
import pandas as pd
import datetime
import db
from db import load_data, generuj_smart_id

def render(sh):
    # 1. NAGŁÓWEK MODUŁU (STYL ZEN)
    st.markdown("""
        <h2 style='color: #E2DCD3; margin-bottom: 0px; font-weight: 400; font-size: 24px;'>Moduł Operacyjny: Subrenty</h2>
        <div style='color: #8C8477; font-size: 11px; letter-spacing: 2px; margin-bottom: 25px;'>オペレーションモジュール: サブレント</div>
    """, unsafe_allow_html=True)
    
    # 2. POBIERANIE DANYCH
    worksheet_sub, df_sub = load_data(sh, "DB_Subrenty")
    worksheet_firmy, df_firmy = load_data(sh, "DB_Katalog_Firm")
    
    katalog_firm = df_firmy["Nazwa_Firmy"].dropna().unique().tolist() if not df_firmy.empty else []
    df_aktywne_sub = df_sub[df_sub.get("Zakonczone_Arch", pd.Series()) != "TAK"].copy() if not df_sub.empty else df_sub.copy()
    
    # 3. OBLICZANIE KPI
    na_stanie = len(df_aktywne_sub[df_aktywne_sub.get("Status_Subrentu", pd.Series()) == "3. Na stanie SQM (Pracuje)"]) if not df_aktywne_sub.empty else 0
    gotowe_do_zwrotu = len(df_aktywne_sub[df_aktywne_sub.get("Status_Subrentu", pd.Series()) == "4. Gotowe do zwrotu (Alert)"]) if not df_aktywne_sub.empty else 0
    
    # Renderowanie kart KPI
    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-header">Łącznie Aktywne</div>
                <div class="kpi-sub-jp">アクティブな総数</div>
                <div class="kpi-value">{len(df_aktywne_sub)}</div>
                <div class="kpi-icon-bg">📦</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">U nas na magazynie</div>
                <div class="kpi-sub-jp">倉庫の在庫</div>
                <div class="kpi-value">{na_stanie}</div>
                <div class="kpi-icon-bg">✅</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">Do pilnego zwrotu</div>
                <div class="kpi-sub-jp">緊急返却</div>
                <div class="kpi-value">{gotowe_do_zwrotu}</div>
                <div class="kpi-icon-bg">⚠️</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 4. ZAKŁADKI MODUŁU
    tab_podglad, tab_nowy, tab_zwrot, tab_archiwum = st.tabs([
        "📊 Podgląd Cyklu", "➕ Dodaj (Inicjuj IN)", "🔄 Zwróć / Aktualizuj (OUT)", "📦 Archiwum"
    ])

    with tab_podglad:
        if not df_aktywne_sub.empty: 
            st.info("💡 Edytuj dane bezpośrednio w tabeli. Kliknij 'Zapisz zmiany', aby bezpiecznie wysłać je do chmury Google.")
            
            # Tabela edytowalna
            edited_df_sub = st.data_editor(df_aktywne_sub, use_container_width=True, hide_index=True, key="edit_subrenty")
            
            if st.button("💾 Zapisz zmiany w tabeli", type="primary"):
                roznice = df_aktywne_sub.ne(edited_df_sub).any(axis=1)
                zmienione_indeksy = df_aktywne_sub[roznice].index
                
                if len(zmienione_indeksy) > 0:
                    with st.spinner("Zapisywanie punktowych zmian..."):
                        for idx in zmienione_indeksy:
                            gs_row = int(edited_df_sub.loc[idx, 'sheet_row'])
                            db.update_single_row_safe("DB_Subrenty", gs_row, edited_df_sub.loc[idx])
                            
                    st.success(f"Pomyślnie zaktualizowano {len(zmienione_indeksy)} rekord(ów) w bazie danych Subrentów!")
                    st.rerun()
                else:
                    st.warning("Nie wykryto żadnych zmian w tabeli.")
        else:
            st.info("Brak aktywnych wypożyczeń sprzętu.")

    with tab_nowy:
        st.markdown("<h4 style='color: #D4AF37; margin-top: 0;'>1. Faza: Inicjacja Wypożyczenia i Transport do SQM</h4>", unsafe_allow_html=True)
        with st.form("form_subrent_in", clear_on_submit=True):
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                co_jedzie = st.text_input("Co wypożyczamy? (Nazwa Sprzętu) *")
                wybor_firmy = st.selectbox("Dostawca (z książki) *", ["-- Dodaj nową firmę --"] + sorted(katalog_firm))
                nowa_firma = st.text_input("Nowa firma (jeśli brak na liście wyżej)")
            with s_col2:
                rodzaj_zlecenia = st.selectbox("Rodzaj", ["Dry Hire", "Cross-rent", "Zastępczy"])
                status_sub = st.selectbox("Status Początkowy", ["1. Zamówione (Oczekuje na IN)", "2. W drodze do SQM (IN)", "3. Na stanie SQM (Pracuje)"])

            st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
            st.markdown("<p style='color:#D4AF37; font-weight:700; margin-bottom:15px; font-size: 14px;'>📅 Terminarz Wynajmu</p>", unsafe_allow_html=True)
            d_col1, d_col2 = st.columns(2)
            with d_col1: data_odbioru = st.date_input("Data rozpoczęcia wynajmu (Odbiór)")
            with d_col2: deadline_zwrotu = st.date_input("Deadline ZWROTU (do kiedy musi oddać)")
            
            st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
            st.markdown("<p style='color:#D4AF37; font-weight:700; margin-bottom:15px; font-size: 14px;'>🚚 Logistyka Odbioru (Etap IN)</p>", unsafe_allow_html=True)
            i_col1, i_col2 = st.columns(2)
            with i_col1: transport_in_kto = st.text_input("Kto nam to przywozi? (np. Kurier DPD, Flota SQM)")
            with i_col2: transport_in_dok = st.text_input("Nr listu przewozowego / Dokument IN")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🚀 Zainicjuj Subrent"):
                firma_docelowa = nowa_firma.strip() if wybor_firmy == "-- Dodaj nową firmę --" else wybor_firmy
                if not co_jedzie or not firma_docelowa:
                    st.error("❌ Musisz uzupełnić nazwę sprzętu oraz wskazać dostawcę!")
                else:
                    # 1. Zapis nowej firmy (jeśli dotyczy)
                    if firma_docelowa not in katalog_firm:
                        kolumny_firm = [k for k in df_firmy.columns if k != 'sheet_row']
                        nowa_firma_dict = {"Nazwa_Firmy": firma_docelowa}
                        wiersz_firmy = [str(nowa_firma_dict.get(k, "")) for k in kolumny_firm]
                        db.append_data("DB_Katalog_Firm", wiersz_firmy)
                        
                    nowy_wiersz = {
                        "ID_Subrentu": "", "Rodzaj_Zlecenia": rodzaj_zlecenia, "Dostawca": firma_docelowa, "Co_Jedzie": co_jedzie,
                        "Data_Odbioru": str(data_odbioru), "Deadline_Zwrotu": str(deadline_zwrotu),
                        "Status_Subrentu": status_sub, "Transport_IN_Kto": transport_in_kto, "Transport_IN_Dokumenty": transport_in_dok,
                        "Transport_OUT_Kto": "", "Transport_OUT_Dokumenty": "", "Koszt_Calkowity_EUR": "0.0",
                        "Nr_Zlecenia_Zewn": "", "Nr_Faktury": "", "Data_Faktycznego_Zwrotu": "",
                        "Data_Platnosci": "", "Faktura_Oplacona": "", "PP_Otrzymane": "", "Zakonczone_Arch": "NIE"
                    }
                    
                    df_temp = pd.concat([df_sub, pd.DataFrame([nowy_wiersz])], ignore_index=True)
                    df_temp = generuj_smart_id(df_temp, "Dostawca", "Co_Jedzie", "ID_Subrentu")
                    nowy_wiersz_z_id = df_temp.iloc[-1]
                    
                    kolumny_sub = [k for k in df_sub.columns if k != 'sheet_row']
                    # Twarde rzutowanie na STR zabezpieczające błędy API
                    wiersz_lista = [str(nowy_wiersz_z_id.get(k, "")) for k in kolumny_sub]
                    
                    db.append_data("DB_Subrenty", wiersz_lista)
                    
                    st.success(f"🎉 Zainicjowano wypożyczenie (Bezpieczny zapis)!")
                    st.rerun()

    with tab_zwrot:
        st.markdown("<h4 style='color: #D4AF37; margin-top: 0;'>2. Faza: Aktualizacja statusu i ZWROT sprzętu</h4>", unsafe_allow_html=True)
        if not df_aktywne_sub.empty:
            wybrany_id = st.selectbox("Wybierz Aktywny Subrent", df_aktywne_sub["ID_Subrentu"].tolist())
            dane_sub = df_aktywne_sub[df_aktywne_sub["ID_Subrentu"] == wybrany_id].iloc[0]
            st.info(f"**Wybrano:** {dane_sub['Co_Jedzie']} (Dostawca: {dane_sub['Dostawca']}) | Deadline: {dane_sub['Deadline_Zwrotu']}")
            
            with st.form("form_subrent_out", clear_on_submit=False):
                obecny_status = str(dane_sub["Status_Subrentu"])
                opcje_statusu = [
                    "1. Zamówione (Oczekuje na IN)", "2. W drodze do SQM (IN)", "3. Na stanie SQM (Pracuje)",
                    "4. Gotowe do zwrotu (Alert)", "5. W drodze powrotnej (OUT)", "6. Zakończone i Rozliczone"
                ]
                idx_statusu = opcje_statusu.index(obecny_status) if obecny_status in opcje_statusu else 0
                nowy_status = st.selectbox("Aktualizuj Status Cyklu", opcje_statusu, index=idx_statusu)
                
                st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                st.markdown("<p style='color:#D4AF37; font-weight:700; margin-bottom:15px; font-size: 14px;'>🚚 Logistyka Zwrotu (Etap OUT)</p>", unsafe_allow_html=True)
                o_col1, o_col2, o_col3 = st.columns(3)
                with o_col1: t_out_kto = st.text_input("Kto organizuje zwrot?", value=str(dane_sub.get("Transport_OUT_Kto", "")))
                with o_col2: t_out_dok = st.text_input("Nr listu zwrotnego / CMR", value=str(dane_sub.get("Transport_OUT_Dokumenty", "")))
                with o_col3: data_zwrotu = st.date_input("Faktyczna Data Zwrotu", value=None)
                
                st.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                st.markdown("<p style='color:#D4AF37; font-weight:700; margin-bottom:15px; font-size: 14px;'>💰 Finanse i Zakończenie</p>", unsafe_allow_html=True)
                f_col1, f_col2, f_col3 = st.columns(3)
                with f_col1: koszt = st.number_input("Koszt Całkowity Wypożyczenia (€)", min_value=0.0, value=float(dane_sub.get("Koszt_Calkowity_EUR", 0.0)) if str(dane_sub.get("Koszt_Calkowity_EUR", "0")).replace('.','',1).isdigit() else 0.0, step=50.0)
                with f_col2: f_opl = st.selectbox("Faktura Opłacona?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_sub.get("Faktura_Oplacona", "")) if dane_sub.get("Faktura_Oplacona", "") in ["", "NIE", "TAK"] else 0)
                with f_col3: nr_fak = st.text_input("Nr Faktury od Dostawcy", value=str(dane_sub.get("Nr_Faktury", "")))
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("💾 Zapisz Zmiany / Zatwierdź Zwrot"):
                    idx = df_sub[df_sub['ID_Subrentu'] == wybrany_id].index[0]
                    
                    # BEZPIECZNE TWARDE RZUTOWANIE NA STRING
                    df_sub.at[idx, 'Status_Subrentu'] = str(nowy_status)
                    df_sub.at[idx, 'Transport_OUT_Kto'] = str(t_out_kto)
                    df_sub.at[idx, 'Transport_OUT_Dokumenty'] = str(t_out_dok)
                    if data_zwrotu: df_sub.at[idx, 'Data_Faktycznego_Zwrotu'] = str(data_zwrotu)
                    
                    df_sub.at[idx, 'Koszt_Calkowity_EUR'] = str(koszt) 
                    df_sub.at[idx, 'Faktura_Oplacona'] = str(f_opl)
                    df_sub.at[idx, 'Nr_Faktury'] = str(nr_fak)
                    
                    if nowy_status == "6. Zakończone i Rozliczone":
                        df_sub.at[idx, 'Zakonczone_Arch'] = "TAK"
                        
                    gs_row = int(df_sub.at[idx, 'sheet_row'])
                    db.update_single_row_safe("DB_Subrenty", gs_row, df_sub.loc[idx])
                    
                    st.success("Aktualizacja zapisana punktowo!")
                    st.rerun()
        else:
            st.info("Brak aktywnych rekordów do edycji.")

    with tab_archiwum:
        df_arch_sub = df_sub[df_sub.get("Zakonczone_Arch", pd.Series()) == "TAK"] if not df_sub.empty else pd.DataFrame()
        if not df_arch_sub.empty: 
            st.dataframe(df_arch_sub, use_container_width=True, hide_index=True)
        else:
            st.info("Brak zarchiwizowanych subrentów.")
