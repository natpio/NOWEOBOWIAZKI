import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import load_data
import datetime

def render(sh):
    col_title, col_currency = st.columns([5, 1])
    with col_title: st.markdown('<h2 style="margin: 0; padding-top: 10px;">📊 Centrum Finansowe</h2>', unsafe_allow_html=True)
    with col_currency: st.selectbox("Waluta", ["Waluta: EUR €"], label_visibility="collapsed")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Pobieranie danych z arkuszy
    _, df_ev = load_data(sh, "DB_Eventy")
    _, df_yt = load_data(sh, "DB_Yestech")
    _, df_sub = load_data(sh, "DB_Subrenty")
    _, df_poboczne = load_data(sh, "Zlecenia Poboczne")
    
    dzisiaj = pd.Timestamp.today().normalize()
    
    spoznione_ev, spoznione_yt = pd.DataFrame(), pd.DataFrame()
    if not df_ev.empty and "Data_Platnosci" in df_ev.columns:
        df_ev['Data_DT'] = pd.to_datetime(df_ev['Data_Platnosci'], errors='coerce')
        spoznione_ev = df_ev[(df_ev['Data_DT'] < dzisiaj) & (df_ev['Faktura_Oplacona'] != "TAK")]
    if not df_yt.empty and "Data_Platnosci" in df_yt.columns:
        df_yt['Data_DT'] = pd.to_datetime(df_yt['Data_Platnosci'], errors='coerce')
        spoznione_yt = df_yt[(df_yt['Data_DT'] < dzisiaj) & (df_yt['Faktura_Oplacona'] != "TAK")]
        
    spoznione_count = len(spoznione_ev) + len(spoznione_yt)
    
    braki_ev = pd.DataFrame()
    if not df_ev.empty and "Zakonczone_Arch" in df_ev.columns:
        braki_ev = df_ev[(df_ev['Zakonczone_Arch'] == 'TAK') & ((df_ev['CMR_Podpisane_POD'] == 'NIE') | (df_ev['Nr_Faktury'] == ''))]
    braki_count = len(braki_ev)

    tab_alerty, tab_ksiegowosc, tab_koszty, tab_rentownosc = st.tabs([
        "🚨 Alerty i Braki", "🧾 Raport dla Księgowości", "💶 Wydatki per Partner", "📈 Rentowność YESTECH"
    ])

    # ==========================================
    # KARTA 1: ALERTY
    # ==========================================
    with tab_alerty:
        t_spozn = "Brak przeterminowanych płatności!" if spoznione_count == 0 else f"Wykryto {spoznione_count} spóźnień!"
        c_spozn = "text-green" if spoznione_count == 0 else "text-red"
        
        t_braki = "Brak blokad rozliczeń!" if braki_count == 0 else f"Wykryto {braki_count} blokad!"
        c_braki = "text-gray" if braki_count == 0 else "text-yellow"

        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card kpi-red">
                <div class="kpi-header">Przeterminowane płatności</div>
                <div class="kpi-value">{spoznione_count}</div>
                <div class="kpi-subtext {c_spozn}">{t_spozn}</div>
                <div class="kpi-icon-bg">💰</div>
            </div>
            <div class="kpi-card kpi-yellow">
                <div class="kpi-header">Blokady Rozliczeń (Brak POD/Faktury)</div>
                <div class="kpi-value">{braki_count}</div>
                <div class="kpi-subtext {c_braki}">{t_braki}</div>
                <div class="kpi-icon-bg">📄</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">Monthly Financial Flow</div>', unsafe_allow_html=True)
        miesiace = ['01.2026', '02.2026', '03.2026', '04.2026', '05.2026', '06.2026']
        przychody = [600, 850, 750, 680, 700, 750]
        koszty = [200, 250, 220, 180, 240, 150]
        zysk = [400, 600, 530, 500, 460, 600]

        fig = go.Figure()
        fig.add_trace(go.Bar(x=miesiace, y=przychody, name='Przychody', marker_color='#3B82F6', width=0.25))
        fig.add_trace(go.Bar(x=miesiace, y=koszty, name='Koszty', marker_color='#10B981', width=0.25))
        fig.add_trace(go.Scatter(x=miesiace, y=zysk, name='Zysk', mode='lines+markers', line=dict(color='#8B5CF6', width=2)))

        fig.update_layout(
            plot_bgcolor='rgba(255,255,255,0.7)', paper_bgcolor='rgba(255,255,255,0.5)',
            font=dict(color='#0A192F'), margin=dict(l=0, r=0, t=10, b=0), height=250,
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            xaxis=dict(showgrid=False, linecolor='#CBD5E1', tickfont=dict(color='#0A192F')),
            yaxis=dict(showgrid=True, gridcolor='#E2E8F0', zerolinecolor='#CBD5E1', tickfont=dict(color='#0A192F')),
            barmode='group'
        )
        st.markdown('<div style="background: rgba(255,255,255,0.85); backdrop-filter: blur(10px); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.5);">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div><br>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">Ostatnie Płatności i Blokady</div>', unsafe_allow_html=True)
        if spoznione_count == 0 and braki_count == 0:
            st.markdown("""
            <table style="width:100%; border-collapse: collapse; background: rgba(255,255,255,0.85); backdrop-filter: blur(5px); border: 1px solid #E2E8F0; border-bottom: none; border-radius: 8px 8px 0 0;">
                <tr style="color: #0A192F; font-size: 13px; border-bottom: 2px solid rgba(10, 25, 47, 0.2); text-align: left;">
                    <th style="padding: 12px;">ID Płatności</th><th style="padding: 12px;">Klient</th><th style="padding: 12px;">Kwota</th><th style="padding: 12px;">Status</th><th style="padding: 12px;">Powód Blokady</th>
                </tr>
            </table>
            <div class="empty-table-msg">Brak aktywnych pozycji</div>
            """, unsafe_allow_html=True)
        else:
            if not spoznione_ev.empty: st.dataframe(spoznione_ev[['ID_Zlecenia', 'Przewoznik', 'Koszt_Transportu_EUR', 'Data_Platnosci']], use_container_width=True)
            if not braki_ev.empty: st.dataframe(braki_ev[['ID_Zlecenia', 'Przewoznik', 'CMR_Podpisane_POD', 'Nr_Faktury']], use_container_width=True)

    # ==========================================
    # KARTA 2: RAPORT DLA KSIĘGOWOŚCI
    # ==========================================
    with tab_ksiegowosc:
        st.markdown("""
            <div style="background: rgba(197, 168, 128, 0.05); border: 1px solid rgba(197, 168, 128, 0.3); padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="color: #C5A880; margin: 0 0 5px 0;">🧾 Inteligentny Raport Księgowy</h4>
                <p style="color: #A39B8F; font-size: 13px; margin: 0;">Zestawienie wszystkich nadchodzących lub zaległych płatności z modułów operacyjnych.</p>
            </div>
        """, unsafe_allow_html=True)
        
        lista_zobowiazan = []
        
        # 1. Agregacja z DB_Eventy
        if not df_ev.empty:
            df_unpaid_ev = df_ev[df_ev.get('Faktura_Oplacona', pd.Series()) != "TAK"]
            for _, row in df_unpaid_ev.iterrows():
                try: koszt = float(str(row.get("Koszt_Transportu_EUR", "0")).replace(',', '.').replace(' ', ''))
                except: koszt = 0.0
                
                # Tylko zlecenia zewnętrzne i takie, które mają wygenerowany koszt
                if koszt > 0 or row.get("Typ_Transportu") == "Zewnętrzny":
                    # Szukanie daty wykonania usługi (Rozładunku)
                    data_wyk = str(row.get("Data_Zakonczenia_Uslugi", "")).strip()
                    if not data_wyk or data_wyk == "nan":
                        notatki = str(row.get("Notatki", ""))
                        if "[Rozładunki:" in notatki:
                            try: data_wyk = notatki.split("[Rozładunki:")[1].split("]")[0].split(",")[-1].strip()
                            except: data_wyk = "Brak danych"
                        else:
                            data_wyk = "Brak danych"
                            
                    nr_fak = str(row.get("Nr_Faktury", "")).strip()
                    
                    lista_zobowiazan.append({
                        "Typ Zlecenia": "Event PRO",
                        "Nazwa Eventu / Zlecenia": str(row.get("Nazwa_Targow", "")),
                        "Kontrahent": str(row.get("Przewoznik", "")),
                        "Data Wykonania Usługi": data_wyk,
                        "Data Płatności": str(row.get("Data_Platnosci", "")),
                        "Kwota": f"{koszt} EUR",
                        "Czy jest POD": str(row.get("CMR_Podpisane_POD", "")),
                        "Nr Faktury": nr_fak if nr_fak not in ["", "nan", "None", "N/A"] else "⚠️ BRAK FAKTURY"
                    })

        # 2. Agregacja z Zleceń Pobocznych
        if not df_poboczne.empty:
            df_unpaid_pob = df_poboczne[df_poboczne.get('Faktura', pd.Series()) != "TAK"]
            for _, row in df_unpaid_pob.iterrows():
                lista_zobowiazan.append({
                    "Typ Zlecenia": "Zlecenie Poboczne",
                    "Nazwa Eventu / Zlecenia": str(row.get("Opis Ładunku / Trasy", "")),
                    "Kontrahent": str(row.get("Przewoźnik", "")),
                    "Data Wykonania Usługi": str(row.get("Data Rozładunku", "")),
                    "Data Płatności": str(row.get("Data Płatności", "")),
                    "Kwota": "Wg faktury (Brak wpisu)",
                    "Czy jest POD": str(row.get("POD", "")),
                    "Nr Faktury": "⚠️ BRAK FAKTURY"
                })

        # 3. Agregacja z Subrentów
        if not df_sub.empty:
            df_unpaid_sub = df_sub[df_sub.get('Faktura_Oplacona', pd.Series()) != "TAK"]
            for _, row in df_unpaid_sub.iterrows():
                try: koszt = float(str(row.get("Koszt_Calkowity_EUR", "0")).replace(',', '.').replace(' ', ''))
                except: koszt = 0.0
                
                if koszt > 0 or row.get("Status_Subrentu") == "6. Zakończone i Rozliczone":
                    nr_fak = str(row.get("Nr_Faktury", "")).strip()
                    lista_zobowiazan.append({
                        "Typ Zlecenia": "Subrent Sprzętu",
                        "Nazwa Eventu / Zlecenia": str(row.get("Co_Jedzie", "")),
                        "Kontrahent": str(row.get("Dostawca", "")),
                        "Data Wykonania Usługi": str(row.get("Data_Faktycznego_Zwrotu", "")),
                        "Data Płatności": str(row.get("Data_Platnosci", "")),
                        "Kwota": f"{koszt} EUR",
                        "Czy jest POD": "N/A",
                        "Nr Faktury": nr_fak if nr_fak not in ["", "nan", "None", "N/A"] else "⚠️ BRAK FAKTURY"
                    })

        df_raport = pd.DataFrame(lista_zobowiazan)
        
        if not df_raport.empty:
            # Tworzenie kolumny Daty do obliczeń i sortowania
            df_raport['_Data_DT'] = pd.to_datetime(df_raport['Data Płatności'], format="%d.%m.%Y", errors='coerce')
            df_raport.loc[df_raport['_Data_DT'].isna(), '_Data_DT'] = pd.to_datetime(df_raport['Data Płatności'], errors='coerce')
            
            # Obliczanie dni opóźnienia
            def oblicz_opoznienie(dt):
                if pd.isna(dt): return "Brak daty płatności"
                dni = (dzisiaj - dt).days
                if dni > 0: return f"🔴 {dni} dni PO TERMINIE"
                elif dni == 0: return "🟡 Płatność na dzisiaj"
                else: return f"🟢 Zapas {-dni} dni"
                
            df_raport.insert(5, 'Opóźnienie Płatności', df_raport['_Data_DT'].apply(oblicz_opoznienie))
            df_raport = df_raport.sort_values(by='_Data_DT', ascending=True, na_position='last')
            
            # Finalny widok
            kolumny_docelowe = [
                "Typ Zlecenia", "Nazwa Eventu / Zlecenia", "Kontrahent", "Data Wykonania Usługi", 
                "Data Płatności", "Opóźnienie Płatności", "Czy jest POD", "Nr Faktury", "Kwota"
            ]
            df_widok = df_raport[kolumny_docelowe]
            
            st.dataframe(df_widok, use_container_width=True, hide_index=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            csv_data = df_widok.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Pobierz Gotowy Raport dla Księgowości (.CSV)",
                data=csv_data,
                file_name=f"Raport_Ksiegowy_{dzisiaj.strftime('%Y-%m-%d')}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
        else:
            st.success("🎉 Raport Księgowy jest pusty. Brak jakichkolwiek zaległych rozliczeń operacyjnych!")

    # ==========================================
    # KARTA 3: WYDATKI
    # ==========================================
    with tab_koszty:
        st.subheader("Zestawienie kosztów u partnerów zewnętrznych")
        k_col1, k_col2 = st.columns(2)
        with k_col1:
            st.markdown("**🚚 Transport (Eventy)**")
            if not df_ev.empty and "Koszt_Transportu_EUR" in df_ev.columns:
                df_ev['Koszt_Transportu_EUR'] = pd.to_numeric(df_ev['Koszt_Transportu_EUR'], errors='coerce').fillna(0)
                koszty_ev = df_ev.groupby("Przewoznik")["Koszt_Transportu_EUR"].sum().reset_index()
                koszty_ev = koszty_ev[koszty_ev["Koszt_Transportu_EUR"] > 0].sort_values(by="Koszt_Transportu_EUR", ascending=False)
                if not koszty_ev.empty: st.dataframe(koszty_ev, use_container_width=True, hide_index=True)
                else: st.info("Brak zarejestrowanych kosztów w Eventach.")
        with k_col2:
            st.markdown("**📦 Sprzęt (Subrenty)**")
            if not df_sub.empty and "Koszt_Calkowity_EUR" in df_sub.columns:
                df_sub['Koszt_Calkowity_EUR'] = pd.to_numeric(df_sub['Koszt_Calkowity_EUR'], errors='coerce').fillna(0)
                koszty_sub = df_sub.groupby("Dostawca")["Koszt_Calkowity_EUR"].sum().reset_index()
                koszty_sub = koszty_sub[koszty_sub["Koszt_Calkowity_EUR"] > 0].sort_values(by="Koszt_Calkowity_EUR", ascending=False)
                if not koszty_sub.empty: st.dataframe(koszty_sub, use_container_width=True, hide_index=True)
                else: st.info("Brak zarejestrowanych kosztów w Subrentach.")

    # ==========================================
    # KARTA 4: RENTOWNOŚĆ
    # ==========================================
    with tab_rentownosc:
        st.subheader("Wycena vs. Rzeczywistość (Eksport Basi)")
        if not df_yt.empty and "Wycena_Dla_Basi" in df_yt.columns and "Koszt_Rzeczywisty" in df_yt.columns:
            df_yt['Wycena_Dla_Basi'] = pd.to_numeric(df_yt['Wycena_Dla_Basi'], errors='coerce').fillna(0)
            df_yt['Koszt_Rzeczywisty'] = pd.to_numeric(df_yt['Koszt_Rzeczywisty'], errors='coerce').fillna(0)
            df_yt['Bilans (Zysk/Strata) €'] = df_yt['Wycena_Dla_Basi'] - df_yt['Koszt_Rzeczywisty']
            
            rentownosc = df_yt[['ID_Yestech', 'Destynacja', 'Wycena_Dla_Basi', 'Koszt_Rzeczywisty', 'Bilans (Zysk/Strata) €']]
            def color_bilans(val):
                if val > 0: return 'color: #10B981; font-weight: bold'
                elif val < 0: return 'color: #EF4444; font-weight: bold'
                return ''
            st.dataframe(rentownosc.style.map(color_bilans, subset=['Bilans (Zysk/Strata) €']), use_container_width=True, hide_index=True)
            suma_zysk = rentownosc['Bilans (Zysk/Strata) €'].sum()
            
            st.markdown(f"""
            <div class="kpi-card kpi-gold" style="width: 50%; margin-top: 20px;">
                <div class="kpi-header">Łączny bilans na projektach YESTECH</div>
                <div class="kpi-value">{suma_zysk:.2f} €</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Brak danych w bazie YESTECH.")
