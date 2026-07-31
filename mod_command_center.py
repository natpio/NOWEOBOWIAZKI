# mod_command_center.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import load_data
import datetime

def render(sh):
    # Pobranie danych ze wszystkich modułów
    _, df_ev = load_data(sh, "DB_Eventy")
    _, df_sub = load_data(sh, "DB_Subrenty")
    _, df_yt = load_data(sh, "DB_Yestech")

    # --- OBLICZENIA KPI ---
    df_aktywne_ev = df_ev[df_ev.get("Zakonczone_Arch", pd.Series()) != "TAK"] if not df_ev.empty else pd.DataFrame()
    braki_cmr = len(df_aktywne_ev[df_aktywne_ev.get("CMR_Gotowe", pd.Series()) == "NIE"])
    braki_pod = len(df_aktywne_ev[df_aktywne_ev.get("CMR_Podpisane_POD", pd.Series()) == "NIE"])
    braki_faktury = len(df_aktywne_ev[df_aktywne_ev.get("Faktura_Oplacona", pd.Series()) == "NIE"])

    # --- TOP SEKCJA: KARTY KPI ---
    st.markdown("""
        <div class="dashboard-grid top-kpi">
            <div class="dash-card kpi-advanced">
                <div class="kpi-adv-header">CMR do wystawienia <span class="icon">📝</span></div>
                <div class="kpi-adv-value">{0}</div>
                <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {4}%;"></div></div>
                <button class="kpi-btn-action">Przejdź do Eventów</button>
            </div>
            <div class="dash-card kpi-advanced">
                <div class="kpi-adv-header">Brakujące zwroty POD <span class="icon">📄</span></div>
                <div class="kpi-adv-value">{1}</div>
                <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {5}%; background: #f59e0b;"></div></div>
                <button class="kpi-btn-action">Monituj Przewoźników</button>
            </div>
            <div class="dash-card kpi-advanced">
                <div class="kpi-adv-header">Nieopłacone faktury <span class="icon">💰</span></div>
                <div class="kpi-adv-value">{2}</div>
                <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {6}%; background: #ef4444;"></div></div>
                <button class="kpi-btn-action">Panel Finansowy</button>
            </div>
        </div>
    """.format(braki_cmr, braki_pod, braki_faktury, 0, min(braki_cmr*5, 100), min(braki_pod*5, 100), min(braki_faktury*5, 100)), unsafe_allow_html=True)

    # --- ŚRODKOWA SEKCJA: MAPA I LISTA ALERTÓW ---
    col_map, col_alerts = st.columns([65, 35], gap="large")

    with col_map:
        st.markdown('<div class="dash-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown('<h3 class="dash-title">Integrated Global Flow</h3>', unsafe_allow_html=True)
        
        # Generowanie mapy Plotly Scattergeo
        fig_map = go.Figure()

        # Współrzędne operacyjne SQM Hub i destynacji
        cities = {
            "Poznań": (52.4064, 16.9252),
            "Madryt": (40.4168, -3.7038),
            "Monachium": (48.1351, 11.5820),
            "Paryż": (48.8566, 2.3522),
            "Sztokholm": (59.3293, 18.0686),
            "Ankara": (39.9334, 32.8597)
        }

        # Rysowanie linii połączeń
        for city, coords in cities.items():
            if city != "Poznań":
                fig_map.add_trace(go.Scattergeo(
                    lon=[cities["Poznań"][1], coords[1]],
                    lat=[cities["Poznań"][0], coords[0]],
                    mode='lines', line=dict(width=2, color='#D4AF37'),
                    opacity=0.6, hoverinfo='none'
                ))

        # Rysowanie punktów miast
        fig_map.add_trace(go.Scattergeo(
            lon=[coords[1] for coords in cities.values()],
            lat=[coords[0] for coords in cities.values()],
            hoverinfo='text', text=list(cities.keys()),
            mode='markers', marker=dict(size=8, color='#3b82f6', line=dict(width=2, color='white'))
        ))
        
        # Wyróżnienie Hubu (Poznań)
        fig_map.add_trace(go.Scattergeo(
            lon=[cities["Poznań"][1]], lat=[cities["Poznań"][0]],
            hoverinfo='text', text=["SQM HUB (POZNAŃ)"],
            mode='markers', marker=dict(size=14, color='#D4AF37', symbol='star')
        ))

        fig_map.update_layout(
            geo=dict(
                scope='europe', projection_type='natural earth',
                showland=True, landcolor='rgba(30, 41, 59, 0.5)',
                showocean=True, oceancolor='rgba(15, 23, 42, 0.0)',
                showcountries=True, countrycolor='rgba(255,255,255,0.1)',
                bgcolor='rgba(0,0,0,0)'
            ),
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False, height=350
        )
        st.plotly_chart(fig_map, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_alerts:
        st.markdown('<div class="dash-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown('<h3 class="dash-title">Skrzynka Problemów (Issue Inbox)</h3>', unsafe_allow_html=True)
        
        # Generowanie alertów na żywo
        alerty_html = ""
        dzisiaj = datetime.date.today()
        
        # 1. Alerty Subrentów
        df_sub_alert = df_sub[df_sub.get("Status_Subrentu", pd.Series()) == "4. Gotowe do zwrotu (Alert)"] if not df_sub.empty else pd.DataFrame()
        for _, row in df_sub_alert.iterrows():
            alerty_html += f"""
            <div class="alert-item alert-warning">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <strong>Pilny zwrot sprzętu: {row.get('Co_Jedzie', 'Nieznany')}</strong><br>
                    Do: {row.get('Dostawca', '-')} (Deadline: {row.get('Deadline_Zwrotu', '-')})
                </div>
            </div>"""

        # 2. Alerty Braków POD dla zakończonych transportów
        if not df_ev.empty:
            df_ev_pod = df_ev[(df_ev.get("Zakonczone_Arch", pd.Series()) == "TAK") & (df_ev.get("CMR_Podpisane_POD", pd.Series()) == "NIE")]
            for _, row in df_ev_pod.head(3).iterrows():
                alerty_html += f"""
                <div class="alert-item alert-danger">
                    <div class="alert-icon">🛑</div>
                    <div class="alert-content">
                        <strong>Brak POD: {row.get('Nazwa_Targow', '-')}</strong><br>
                        Przewoźnik {row.get('Przewoznik', '-')} nie dostarczył dokumentów.
                    </div>
                </div>"""
        
        if alerty_html == "":
            alerty_html = "<div style='color: #10B981; text-align: center; margin-top: 50px; font-size: 18px;'>✅ Wszystko pod kontrolą! Brak palących problemów.</div>"
            
        st.markdown(alerty_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- DOLNA SEKCJA: SANKEY DIAGRAM ---
    st.markdown('<div class="dash-card" style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<h3 class="dash-title">Global Financial Flow (€)</h3>', unsafe_allow_html=True)
    
    # Obliczenia do Sankeya
    yestech_rev = pd.to_numeric(df_yt['Wycena_Dla_Basi'], errors='coerce').sum() if not df_yt.empty and 'Wycena_Dla_Basi' in df_yt.columns else 45000
    yestech_cost = pd.to_numeric(df_yt['Koszt_Rzeczywisty'], errors='coerce').sum() if not df_yt.empty and 'Koszt_Rzeczywisty' in df_yt.columns else 12000
    subrent_cost = pd.to_numeric(df_sub['Koszt_Calkowity_EUR'], errors='coerce').sum() if not df_sub.empty and 'Koszt_Calkowity_EUR' in df_sub.columns else 28000
    eventy_cost = pd.to_numeric(df_ev['Koszt_Transportu_EUR'], errors='coerce').sum() if not df_ev.empty and 'Koszt_Transportu_EUR' in df_ev.columns else 56000
    
    eventy_rev = eventy_cost * 1.5 # Symulacja przychodu na bazie kosztu
    total_rev = yestech_rev + eventy_rev
    zysk = total_rev - (yestech_cost + subrent_cost + eventy_cost)

    fig_sankey = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 15, thickness = 20,
            line = dict(color = "rgba(255,255,255,0.1)", width = 0.5),
            label = ["YESTECH Przychód", "Eventy Budżet", "Całkowity Przychód", "Transport Zewn.", "Subrenty Sprzętu", "ZYSK NETTO"],
            color = ["#3b82f6", "#3b82f6", "#10b981", "#ef4444", "#ef4444", "#D4AF37"]
        ),
        link = dict(
            source = [0, 1, 2, 2, 2], 
            target = [2, 2, 3, 4, 5],
            value = [yestech_rev, eventy_rev, eventy_cost + yestech_cost, subrent_cost, zysk],
            color = ["rgba(59, 130, 246, 0.4)", "rgba(59, 130, 246, 0.4)", "rgba(239, 68, 68, 0.4)", "rgba(239, 68, 68, 0.4)", "rgba(212, 175, 55, 0.4)"]
        ))])

    fig_sankey.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#F8FAFC', size=12), height=280
    )
    st.plotly_chart(fig_sankey, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)
