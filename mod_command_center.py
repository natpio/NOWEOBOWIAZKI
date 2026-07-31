import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from db import load_data

def render(sh):
    # ==========================================
    # 1. POBIERANIE DANYCH
    # ==========================================
    _, df_ev = load_data(sh, "DB_Eventy")
    _, df_sub = load_data(sh, "DB_Subrenty")
    _, df_yt = load_data(sh, "DB_Yestech")

    df_aktywne_ev = df_ev[df_ev.get("Zakonczone_Arch", pd.Series()) != "TAK"] if not df_ev.empty else pd.DataFrame()
    braki_cmr = len(df_aktywne_ev[df_aktywne_ev.get("CMR_Gotowe", pd.Series()) == "NIE"])
    braki_pod = len(df_aktywne_ev[df_aktywne_ev.get("CMR_Podpisane_POD", pd.Series()) == "NIE"])

    nieoplacone = []
    if not df_ev.empty:
        ev_nie = df_ev[df_ev.get("Faktura_Oplacona", pd.Series()) == "NIE"]
        for _, r in ev_nie.iterrows(): 
            kwota = pd.to_numeric(r.get("Koszt_Transportu_EUR", 0), errors='coerce')
            if kwota > 0:
                nieoplacone.append({"Moduł": "Event", "ID": r.get("ID_Zlecenia", ""), "Partner": r.get("Przewoznik", ""), "Kwota (€)": kwota, "Termin": r.get("Data_Platnosci", "")})
    if not df_sub.empty:
        sub_nie = df_sub[df_sub.get("Faktura_Oplacona", pd.Series()) == "NIE"]
        for _, r in sub_nie.iterrows(): 
            kwota = pd.to_numeric(r.get("Koszt_Calkowity_EUR", 0), errors='coerce')
            if kwota > 0:
                nieoplacone.append({"Moduł": "Subrent", "ID": r.get("ID_Subrentu", ""), "Partner": r.get("Dostawca", ""), "Kwota (€)": kwota, "Termin": r.get("Data_Platnosci", "")})
    if not df_yt.empty:
        yt_nie = df_yt[df_yt.get("Faktura_Oplacona", pd.Series()) == "NIE"]
        for _, r in yt_nie.iterrows(): 
            kwota = pd.to_numeric(r.get("Koszt_Rzeczywisty", 0), errors='coerce')
            if kwota > 0:
                nieoplacone.append({"Moduł": "Yestech", "ID": r.get("ID_Yestech", ""), "Partner": r.get("Przewoznik", ""), "Kwota (€)": kwota, "Termin": r.get("Data_Platnosci", "")})

    df_nieoplacone = pd.DataFrame(nieoplacone)
    liczba_faktur = len(df_nieoplacone)
    kwota_nieoplacona = df_nieoplacone["Kwota (€)"].sum() if not df_nieoplacone.empty else 0

    # ==========================================
    # 2. TOP: ADVANCED KPI CARDS
    # ==========================================
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

    # ==========================================
    # 3. MIDDLE: CUSTOM FLOW & ISSUE INBOX
    # ==========================================
    col_flow, col_alerts = st.columns([7, 3], gap="large")

    with col_flow:
        st.markdown('<h3 class="dash-title">Integrated Global Flow</h3>', unsafe_allow_html=True)
        
        # Wstrzykujemy czysty HTML, który zablokuje rozjeżdżanie się elementów
        custom_flow_html = f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
            body {{
                margin: 0; padding: 0; font-family: 'Inter', sans-serif;
                background-color: transparent; color: #F8FAFC;
            }}
            .flow-container {{
                display: flex; gap: 20px;
                background: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px; padding: 20px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            }}
            .map-section {{ 
                flex: 1.2; border-right: 1px solid rgba(255,255,255,0.1); 
                padding-right: 20px; display: flex; flex-direction: column; justify-content: center;
            }}
            .process-section {{ flex: 2; display: flex; gap: 15px; align-items: stretch; }}
            
            .stage-box {{
                flex: 1; background: rgba(15, 23, 42, 0.5);
                border-radius: 8px; padding: 15px;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            .stage-title {{ font-size: 12px; color: #94A3B8; text-transform: uppercase; margin-bottom: 15px; font-weight: 700; }}
            
            /* Grid dla logotypów / firm */
            .logo-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
            .logo-item {{ 
                background: rgba(255,255,255,0.9); height: 32px; border-radius: 4px; 
                display: flex; align-items: center; justify-content: center; 
                color: #0f172a; font-size: 10px; font-weight: 800; 
            }}
            .logo-item.alert {{ border: 2px solid #ef4444; }}
            .logo-item.dark {{ background: rgba(255,255,255,0.1); color: #94A3B8; border: 1px dashed rgba(255,255,255,0.2); }}
            
            /* Karta Aktywnej Floty */
            .fleet-card {{
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                border: 1px solid rgba(212, 175, 55, 0.4);
                border-radius: 8px; padding: 12px; margin-top: 10px;
            }}
            .status-green {{ color: #10B981; font-weight: 700; font-size: 11px; margin-left: 5px; }}
            .map-img {{ width: 100%; border-radius: 8px; opacity: 0.6; filter: hue-rotate(200deg) brightness(0.8); }}
        </style>

        <div class="flow-container">
            <div class="map-section">
                <!-- Wizualizacja zarysu mapy (zastępcza grafika dla efektu wizualnego z projektu) -->
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Europe_orthographic_Caucasus_Urals_boundary.svg/400px-Europe_orthographic_Caucasus_Urals_boundary.svg.png" class="map-img">
            </div>
            
            <div class="process-section">
                <div class="stage-box">
                    <div class="stage-title">Inicjacja</div>
                    <div class="logo-grid">
                        <div class="logo-item">FRANTRANS</div>
                        <div class="logo-item">AeroCargo</div>
                        <div class="logo-item alert">L-Acoustics</div>
                        <div class="logo-item">YESTECH</div>
                    </div>
                </div>
                
                <div class="stage-box" style="border-bottom: 3px solid #D4AF37;">
                    <div class="stage-title">W drodze (SQM Fleet)</div>
                    <div class="fleet-card">
                        <div style="font-size: 11px; color: #94A3B8; margin-bottom: 6px;">
                            Aktywne FTL: <strong>1</strong>
                        </div>
                        <div style="font-size: 11px; color: #cbd5e1; margin-bottom: 4px;">
                            Kierowca: Kowalski <span class="status-green">✔</span>
                        </div>
                        <div style="font-size: 11px; color: #cbd5e1;">
                            CMR Status: <span class="status-green">Wystawiono ✔</span>
                        </div>
                    </div>
                </div>
                
                <div class="stage-box">
                    <div class="stage-title">Zamknięte</div>
                    <div class="logo-grid">
                        <div class="logo-item dark">POD ✔</div>
                        <div class="logo-item dark">POD ✔</div>
                        <div class="logo-item dark">POD ✔</div>
                        <div class="logo-item dark">POD ✔</div>
                    </div>
                </div>
            </div>
        </div>
        """
        components.html(custom_flow_html, height=250)

    with col_alerts:
        st.markdown('<div class="dash-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="dash-title">Lista Problemów (Issue Inbox)</h3>', unsafe_allow_html=True)
        
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
            alerty_html = "<div style='color: #10B981; padding: 20px 0; font-size: 14px;'>✅ Wszystko pod kontrolą. Brak palących problemów operacyjnych.</div>"
            
        st.markdown(alerty_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # 4. BOTTOM: PŁATNOŚCI
    # ==========================================
    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.markdown(f'<h3 class="dash-title" style="color: #ef4444;">Faktury oczekujące na opłacenie u partnerów (Razem: {kwota_nieoplacona:,.2f} €)</h3>', unsafe_allow_html=True)
    
    if not df_nieoplacone.empty:
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
