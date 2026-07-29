import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import load_data

def render(sh):
    col_title, col_currency = st.columns([5, 1])
    with col_title: st.markdown('<h2 style="margin: 0; padding-top: 10px;">📊 Centrum Finansowe</h2>', unsafe_allow_html=True)
    with col_currency: st.selectbox("Waluta", ["Waluta: EUR €"], label_visibility="collapsed")
    st.markdown("<br>", unsafe_allow_html=True)
    
    _, df_ev = load_data(sh, "DB_Eventy")
    _, df_yt = load_data(sh, "DB_Yestech")
    _, df_sub = load_data(sh, "DB_Subrenty")
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

    tab_alerty, tab_koszty, tab_rentownosc = st.tabs(["🚨 Alerty i Braki", "💶 Wydatki per Partner", "📈 Rentowność YESTECH"])

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
                <div class="kpi-btn">Pokaż szczegóły</div>
                <div class="kpi-icon-bg">💰</div>
            </div>
            <div class="kpi-card kpi-yellow">
                <div class="kpi-header">Blokady Rozliczeń (Brak POD/Faktury)</div>
                <div class="kpi-value">{braki_count}</div>
                <div class="kpi-subtext {c_braki}">{t_braki}</div>
                <div class="kpi-btn">Pokaż szczegóły</div>
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
