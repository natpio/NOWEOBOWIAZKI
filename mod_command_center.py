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

    # Zbieranie nieopłaconych faktur ze wszystkich modułów
    nieoplacone = []
    if not df_ev.empty:
        ev_nie = df_ev[df_ev.get("Faktura_Oplacona", pd.Series()) == "NIE"]
        for _, r in ev_nie.iterrows(): 
            nieoplacone.append({"Moduł": "Event", "ID": r.get("ID_Zlecenia", ""), "Partner": r.get("Przewoznik", ""), "Kwota (€)": pd.to_numeric(r.get("Koszt_Transportu_EUR", 0), errors='coerce'), "Termin": r.get("Data_Platnosci", "")})
    if not df_sub.empty:
        sub_nie = df_sub[df_sub.get("Faktura_Oplacona", pd.Series()) == "NIE"]
        for _, r in sub_nie.iterrows(): 
            nieoplacone.append({"Moduł": "Subrent", "ID": r.get("ID_Subrentu", ""), "Partner": r.get("Dostawca", ""), "Kwota (€)": pd.to_numeric(r.get("Koszt_Calkowity_EUR", 0), errors='coerce'), "Termin": r.get("Data_Platnosci", "")})
    if not df_yt.empty:
        yt_nie = df_yt[df_yt.get("Faktura_Oplacona", pd.Series()) == "NIE"]
        for _, r in yt_nie.iterrows(): 
            nieoplacone.append({"Moduł": "Yestech", "ID": r.get("ID_Yestech", ""), "Partner": r.get("Przewoznik", ""), "Kwota (€)": pd.to_numeric(r.get("Koszt_Rzeczywisty", 0), errors='coerce'), "Termin": r.get("Data_Platnosci", "")})

    df_nieoplacone = pd.DataFrame(nieoplacone)
    liczba_faktur = len(df_nieoplacone)
    kwota_nieoplacona = df_nieoplacone["Kwota (€)"].sum() if not df_nieoplacone.empty else 0

    # --- TOP SEKCJA: KARTY KPI (Używamy st.columns dla stabilności) ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="dash-card kpi-advanced">
            <div class="kpi-adv-header">CMR do wystawienia <span class="icon">📝</span></div>
            <div class="kpi-adv-value">{braki_cmr}</div>
            <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {min(braki_cmr*10, 100)}%;"></div></div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="dash-card kpi-advanced">
            <div class="kpi-adv-header">Brakujące zwroty POD <span class="icon">📄</span></div>
            <div class="kpi-adv-value">{braki_pod}</div>
            <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {min(braki_pod*10, 100)}%; background: #f59e0b;"></div></div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="dash-card kpi-advanced">
            <div class="kpi-adv-header">Nieopłacone faktury <span class="icon">💰</span></div>
            <div class="kpi-adv-value">{liczba_faktur}</div>
            <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {min(liczba_faktur*5, 100)}%; background: #ef4444;"></div></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- ŚRODKOWA SEKCJA: MAPA I LISTA ALERTÓW ---
    col_map, col_alerts = st.columns([6, 4], gap="large")

    with col_map:
        st.markdown('<div class="dash-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="dash-title">Global Flow Map</h3>', unsafe_allow_html=True)
        
        fig_map = go.Figure()
        cities = {
            "Poznań": (52.4064, 16.9252), "Madryt": (40.4168, -3.7038),
            "Monachium": (48.1351, 11.5820), "Paryż": (48.8566, 2.3522),
            "Sztokholm": (59.3293, 18.0686), "Ankara": (39.9334, 32.8597)
        }

        for city, coords in cities.items():
            if city != "Poznań":
                fig_map.add_trace(go.Scattergeo(
                    lon=[cities["Poznań"][1], coords[1]], lat=[cities["Poznań"][0], coords[0]],
                    mode='lines', line=dict(width=1.5, color='#D4AF37'), opacity=0.5, hoverinfo='none'
                ))

        fig_map.add_trace(go.Scattergeo(
            lon=[coords[1] for coords in cities.values()], lat=[coords[0] for coords in cities.values()],
            hoverinfo='text', text=list(cities.keys()), mode='markers', marker=dict(size=8, color='#3b82f6')
        ))
        
        fig_map.add_trace(go.Scattergeo(
            lon=[cities["Poznań"][1]], lat=[cities["Poznań"][0]],
            hoverinfo='text', text=["SQM HUB (POZNAŃ)"], mode='markers', marker=dict(size=14, color='#D4AF37', symbol='star')
        ))

        fig_map.update_layout(
            geo=dict(
                scope='europe', projection_type='natural earth', showland=True, landcolor='rgba(30, 41, 59, 0.5)',
                showocean=True, oceancolor='rgba(0,0,0,0)', showcountries=True, countrycolor='rgba(255,255,255,0.1)',
                bgcolor='rgba(0,0,0,0)', center=dict(lat=49, lon=10), projection_scale=1.5
            ),
            margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False, height=300
        )
        st.plotly_chart(fig_map, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_alerts:
        st.markdown('<div class="dash-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="dash-title">Skrzynka Problemów (Issue Inbox)</h3>', unsafe_allow_html=True)
        
        alerty_html = ""
        
        # Alerty Subrentów
        df_sub_alert = df_sub[df_sub.get("Status_Subrentu", pd.Series()) == "4. Gotowe do zwrotu (Alert)"] if not df_sub.empty else pd.DataFrame()
        for _, row in df_sub_alert.iterrows():
            alerty_html += f"""
            <div class="alert-item alert-warning">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content"><strong>Pilny zwrot: {row.get('Co_Jedzie', '-')}</strong>Do: {row.get('Dostawca', '-')}</div>
            </div>"""

        # Alerty Braków POD
        if not df_ev.empty:
            df_ev_pod = df_ev[(df_ev.get("Zakonczone_Arch", pd.Series()) == "TAK") & (df_ev.get("CMR_Podpisane_POD", pd.Series()) == "NIE")]
            for _, row in df_ev_pod.head(4).iterrows():
                alerty_html += f"""
                <div class="alert-item alert-danger">
                    <div class="alert-icon">🛑</div>
                    <div class="alert-content"><strong>Brak POD: {row.get('Nazwa_Targow', '-')}</strong>Przewoźnik {row.get('Przewoznik', '-')}</div>
                </div>"""
        
        if alerty_html == "":
            alerty_html = "<div style='color: #10B981; padding: 20px 0;'>✅ Brak palących problemów operacyjnych.</div>"
            
        st.markdown(alerty_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- DOLNA SEKCJA: KONTROLA PŁATNOŚCI ---
    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.markdown(f'<h3 class="dash-title" style="color: #ef4444;">Faktury oczekujące na opłacenie (Razem: {kwota_nieoplacona:,.2f} €)</h3>', unsafe_allow_html=True)
    
    if not df_nieoplacone.empty:
        # Formatowanie kwoty dla lepszej czytelności
        st.dataframe(
            df_nieoplacone, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Kwota (€)": st.column_config.NumberColumn(format="%.2f €")
            }
        )
    else:
        st.info("✅ Wszystkie zarejestrowane faktury w systemie są opłacone.")
        
    st.markdown('</div>', unsafe_allow_html=True)
