import streamlit as st
import pandas as pd
import datetime
from db import load_data, save_data, generuj_smart_id

def render(sh):
    st.title("📦 Hub Wypożyczeń (Lifecycle)")
    
    worksheet_sub, df_sub = load_data(sh, "DB_Subrenty")
    worksheet_firmy, df_firmy = load_data(sh, "DB_Katalog_Firm")
    
    katalog_firm = df_firmy["Nazwa_Firmy"].dropna().unique().tolist() if not df_firmy.empty else []
    df_aktywne_sub = df_sub[df_sub.get("Zakonczone_Arch", pd.Series()) != "TAK"] if not df_sub.empty else df_sub
    
    na_stanie = len(df_aktywne_sub[df_aktywne_sub.get("Status_Subrentu", pd.Series()) == "3. Na stanie SQM (Pracuje)"]) if not df_aktywne_sub.empty else 0
    gotowe_do_zwrotu = len(df_aktywne_sub[df_aktywne_sub.get("Status_Subrentu", pd.Series()) == "4. Gotowe do zwrotu (Alert)"]) if not df_aktywne_sub.empty else 0
    
    st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card kpi-blue">
                <div class="kpi-header">Łącznie Aktywne</div>
                <div class="kpi-value">{len(df_aktywne_sub)}</div>
                <div class="kpi-icon-bg">📦</div>
            </div>
            <div class="kpi-card kpi-green">
                <div class="kpi-header">U nas na magazynie</div>
                <div class="kpi-value">{na_stanie}</div>
                <div class="kpi-icon-bg">✅</div>
            </div>
            <div class="kpi-card kpi-red">
                <div class="kpi-header">Do pilnego zwrotu</div>
                <div class="kpi-value">{gotowe_do_zwrotu}</div>
                <div class="kpi-icon-bg">⚠️</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_podglad, tab_nowy, tab_zwrot, tab_archiwum = st.tabs([
        "📊 Podgląd Cyklu", "➕ Dodaj (Inicjuj IN)", "🔄 Zwróć / Aktualizuj (OUT)", "📦 Archiwum"
    ])

    with tab_podglad:
        if not df_aktywne_sub.empty: 
            st.info("💡 Edytuj dane bezpośrednio w tabeli. Kliknij 'Zapisz zmiany', aby wysłać do chmury Google.")
            
            # Zostawiamy wszystkie kolumny odblokowane do edycji w locie
            edited_df_sub = st.data_editor(df_aktywne_sub, use_container_width=True, hide_index=True, key="edit_subrenty")
            
            if st.button("💾 Zapisz zmiany w tabeli", type="primary"):
                df_sub.update(edited_df_sub)
                save_data(worksheet_sub, df_sub)
                st.success("Pomyślnie zaktualizowano bazę danych Subrentów!")
                st.rerun()
        else:
            st.info("Brak aktywnych wypożyczeń sprzętu.")

    with tab_nowy:
        st.subheader("1. Faza: Inicjacja Wypożyczenia i Transport do SQM")
        with st.form("form_subrent_in", clear_on_submit=True):
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                co_jedzie = st.text_input("Co wypożyczamy? (Nazwa Sprzętu) *")
                wybor_firmy = st.selectbox("Dostawca (z książki) *", ["-- Dodaj nową firmę --"] + sorted(katalog_firm))
                nowa_firma = st.text_input("Nowa firma (jeśli brak na liście wyżej)")
            with s_col2:
                rodzaj_zlecenia = st.selectbox("Rodzaj", ["Dry Hire", "Cross-rent", "Zastępczy"])
                status_sub = st.selectbox("Status Początkowy", ["1. Zamówione (Oczekuje na IN)", "2. W drodze do SQM (IN)", "3. Na stanie SQM (Pracuje)"])

            st.markdown("### 📅 Terminarz Wynajmu")
            d_col1, d_col2 = st.columns(2)
            with d_col1: data_odbioru = st.date_input("Data rozpoczęcia wynajmu (Odbiór)")
            with d_col2: deadline_zwrotu = st.date_input("Deadline ZWROTU (do kiedy musi oddać)")
            
            st.markdown("### 🚚 Logistyka Odbioru (Etap IN)")
            i_col1, i_col2 = st.columns(2)
            with i_col1: transport_in_kto = st.text_input("Kto nam to przywozi? (np. Kurier DPD, Flota SQM)")
            with i_col2: transport_in_dok = st.text_input("Nr listu przewozowego / Dokument IN")

            if st.form_submit_button("🚀 Zainicjuj Subrent"):
                firma_docelowa = nowa_firma.strip() if wybor_firmy == "-- Dodaj nową firmę --" else wybor_firmy
                if not co_jedzie or not firma_docelowa:
                    st.error("❌ Musisz uzupełnić nazwę sprzętu oraz wskazać dostawcę!")
                else:
                    if firma_docelowa not in katalog_firm:
                        df_firmy = pd.concat([df_firmy, pd.DataFrame([{"Nazwa_Firmy": firma_docelowa}])], ignore_index=True)
                        save_data(worksheet_firmy, df_firmy)
                        
                    nowy_wiersz = {
                        "ID_Subrentu": "", "Rodzaj_Zlecenia": rodzaj_zlecenia, "Dostawca": firma_docelowa, "Co_Jedzie": co_jedzie,
                        "Data_Odbioru": str(data_odbioru), "Deadline_Zwrotu": str(deadline_zwrotu),
                        "Status_Subrentu": status_sub, "Transport_IN_Kto": transport_in_kto, "Transport_IN_Dokumenty": transport_in_dok,
                        "Transport_OUT_Kto": "", "Transport_OUT_Dokumenty": "", "Koszt_Calkowity_EUR": 0.0,
                        "Nr_Zlecenia_Zewn": "", "Nr_Faktury": "", "Data_Faktycznego_Zwrotu": "",
                        "Data_Platnosci": "", "Faktura_Oplacona": "", "PP_Otrzymane": "", "Zakonczone_Arch": "NIE"
                    }
                    df_sub = pd.concat([df_sub, pd.DataFrame([nowy_wiersz])], ignore_index=True)
                    df_sub = generuj_smart_id(df_sub, "Dostawca", "Co_Jedzie", "ID_Subrentu")
                    save_data(worksheet_sub, df_sub)
                    st.success(f"🎉 Zainicjowano wypożyczenie!")
                    st.rerun()

    with tab_zwrot:
        st.subheader("2. Faza: Aktualizacja statusu i ZWROT sprzętu")
        if not df_aktywne_sub.empty:
            wybrany_id = st.selectbox("Wybierz Aktywny Subrent", df_aktywne_sub["ID_Subrentu"].tolist())
            dane_sub = df_aktywne_sub[df_aktywne_sub["ID_Subrentu"] == wybrany_id].iloc[0]
            st.info(f"**Wybrano:** {dane_sub['Co_Jedzie']} (Dostawca: {dane_sub['Dostawca']}) | Deadline: {dane_sub['Deadline_Zwrotu']}")
            
            with st.form("form_subrent_out", clear_on_submit=False):
                obecny_status = dane_sub["Status_Subrentu"]
                opcje_statusu = [
                    "1. Zamówione (Oczekuje na IN)", "2. W drodze do SQM (IN)", "3. Na stanie SQM (Pracuje)",
                    "4. Gotowe do zwrotu (Alert)", "5. W drodze powrotnej (OUT)", "6. Zakończone i Rozliczone"
                ]
                idx_statusu = opcje_statusu.index(obecny_status) if obecny_status in opcje_statusu else 0
                nowy_status = st.selectbox("Aktualizuj Status Cyklu", opcje_statusu, index=idx_statusu)
                
                st.markdown("### 🚚 Logistyka Zwrotu (Etap OUT)")
                o_col1, o_col2, o_col3 = st.columns(3)
                with o_col1: t_out_kto = st.text_input("Kto organizuje zwrot?", value=dane_sub.get("Transport_OUT_Kto", ""))
                with o_col2: t_out_dok = st.text_input("Nr listu zwrotnego / CMR", value=dane_sub.get("Transport_OUT_Dokumenty", ""))
                with o_col3: data_zwrotu = st.date_input("Faktyczna Data Zwrotu", value=None)
                
                st.markdown("### 💰 Finanse i Zakończenie")
                f_col1, f_col2, f_col3 = st.columns(3)
                with f_col1: koszt = st.number_input("Koszt Całkowity Wypożyczenia (€)", min_value=0.0, value=float(dane_sub.get("Koszt_Calkowity_EUR", 0.0)), step=50.0)
                with f_col2: f_opl = st.selectbox("Faktura Opłacona?", ["", "NIE", "TAK"], index=["", "NIE", "TAK"].index(dane_sub.get("Faktura_Oplacona", "")) if dane_sub.get("Faktura_Oplacona", "") in ["", "NIE", "TAK"] else 0)
                with f_col3: nr_fak = st.text_input("Nr Faktury od Dostawcy", value=dane_sub.get("Nr_Faktury", ""))
                
                if st.form_submit_button("💾 Zapisz Zmiany / Zatwierdź Zwrot"):
                    idx = df_sub[df_sub['ID_Subrentu'] == wybrany_id].index[0]
                    df_sub.at[idx, 'Status_Subrentu'] = nowy_status
                    df_sub.at[idx, 'Transport_OUT_Kto'] = t_out_kto
                    df_sub.at[idx, 'Transport_OUT_Dokumenty'] = t_out_dok
                    if data_zwrotu: df_sub.at[idx, 'Data_Faktycznego_Zwrotu'] = str(data_zwrotu)
                    df_sub.at[idx, 'Koszt_Calkowity_EUR'] = float(koszt)
                    df_sub.at[idx, 'Faktura_Oplacona'] = f_opl
                    df_sub.at[idx, 'Nr_Faktury'] = nr_fak
                    if nowy_status == "6. Zakończone i Rozliczone":
                        df_sub.at[idx, 'Zakonczone_Arch'] = "TAK"
                        
                    save_data(worksheet_sub, df_sub)
                    st.success("Aktualizacja zapisana!")
                    st.rerun()
        else:
            st.info("Brak aktywnych rekordów do edycji.")

    with tab_archiwum:
        df_arch_sub = df_sub[df_sub.get("Zakonczone_Arch", pd.Series()) == "TAK"] if not df_sub.empty else pd.DataFrame()
        if not df_arch_sub.empty: st.dataframe(df_arch_sub, use_container_width=True, hide_index=True)
