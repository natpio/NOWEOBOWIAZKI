import streamlit as st
import pandas as pd

def render(sh):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Command Center</h1>
            <div class="module-subtitle">コマンドセンター ✦ GŁÓWNY PANEL STEROWANIA</div>
        </div>
    ''', unsafe_allow_html=True)

    try:
        ws_zlecenia = sh.worksheet("Zlecenia Poboczne")
        df_zlecenia = pd.DataFrame(ws_zlecenia.get_all_records())
    except Exception as e:
        st.warning(f"Brak danych lub arkusza 'Zlecenia Poboczne'. ({e})")
        df_zlecenia = pd.DataFrame()

    aktywne_zlecenia = pd.DataFrame()
    if not df_zlecenia.empty and 'Status' in df_zlecenia.columns:
        aktywne_zlecenia = df_zlecenia[df_zlecenia['Status'] != 'ARCHIWUM']

    total_active = len(aktywne_zlecenia)
    
    brak_cmr = len(aktywne_zlecenia[aktywne_zlecenia.get("CMR") == "NIE"]) if not aktywne_zlecenia.empty else 0
    brak_pod = len(aktywne_zlecenia[aktywne_zlecenia.get("POD") == "NIE"]) if not aktywne_zlecenia.empty else 0
    brak_fv = len(aktywne_zlecenia[aktywne_zlecenia.get("Faktura") == "NIE"]) if not aktywne_zlecenia.empty else 0
    
    suma_problemow = brak_cmr + brak_pod + brak_fv

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="dash-card">
            <div class="kpi-advanced">
                <div class="kpi-adv-header">
                    <span>Aktywne Operacje (Poboczne)</span>
                    <span class="icon">🚛</span>
                </div>
                <div class="kpi-adv-value">{total_active}</div>
                <div class="kpi-progress-bar"><div class="kpi-progress" style="width: 100%;"></div></div>
                <div style="font-size: 10px; color: #8C8477;">Bieżące zlecenia w realizacji</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="dash-card">
            <div class="kpi-advanced">
                <div class="kpi-adv-header">
                    <span>Otwarte Kwestie Dokumentacyjne</span>
                    <span class="icon">📑</span>
                </div>
                <div class="kpi-adv-value">{brak_cmr + brak_pod}</div>
                <div class="kpi-progress-bar"><div class="kpi-progress" style="width: 75%; background: #C77F4A;"></div></div>
                <div style="font-size: 10px; color: #8C8477;">Braki CMR oraz POD z tras</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="dash-card">
            <div class="kpi-advanced">
                <div class="kpi-adv-header">
                    <span>Zadłużenie / Brak Płatności</span>
                    <span class="icon">💰</span>
                </div>
                <div class="kpi-adv-value">{brak_fv}</div>
                <div class="kpi-progress-bar"><div class="kpi-progress" style="width: 40%; background: #BA4949;"></div></div>
                <div style="font-size: 10px; color: #8C8477;">Wymagają domknięcia księgowego</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<h3 class='dash-title'>🚨 Skrzynka Problemów (Issue Inbox)</h3>", unsafe_allow_html=True)
    
    alerts_html = ""
    
    if not aktywne_zlecenia.empty:
        for index, row in aktywne_zlecenia.iterrows():
            nr = row.get("Nr Zlecenia", "Nieznany")
            przew = row.get("Przewoźnik", "Nieznany przewoźnik")
            
            if row.get("CMR") == "NIE":
                alerts_html += f"""
                <div class="alert-item alert-danger">
                    <div class="alert-icon">📄</div>
                    <div class="alert-content">
                        <strong>Krytyczny brak dokumentu CMR!</strong>
                        Zlecenie poboczne <b>{nr}</b> ({przew}) nie posiada przypisanego listu przewozowego.
                    </div>
                </div>"""
                
            if row.get("POD") == "NIE":
                alerts_html += f"""
                <div class="alert-item alert-warning">
                    <div class="alert-icon">📋</div>
                    <div class="alert-content">
                        <strong>Brak zwrotu dokumentów dostawy (POD)</strong>
                        Przewoźnik <b>{przew}</b> nie dostarczył potwierdzenia rozładunku dla zlecenia <b>{nr}</b>.
                    </div>
                </div>"""
                
            if row.get("Faktura") == "NIE":
                alerts_html += f"""
                <div class="alert-item" style="border-left: 3px solid #C5A880; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);">
                    <div class="alert-icon" style="opacity: 0.8;">💳</div>
                    <div class="alert-content">
                        <strong style="color: #E2DCD3;">Nieopłacona Faktura Transportowa</strong>
                        Zlecenie <b>{nr}</b> oczekuje na spływ lub zaksięgowanie faktury.
                    </div>
                </div>"""

    if not alerts_html:
        alerts_html = """
        <div class="alert-item" style="border-left: 3px solid #77A385; background: rgba(119, 163, 133, 0.05); border: 1px solid rgba(119, 163, 133, 0.1);">
            <div class="alert-icon" style="opacity: 1;">🍵</div>
            <div class="alert-content">
                <strong style="color: #77A385;">Wszystko w porządku (Czysta karta)</strong>
                Brak aktywnych problemów dokumentacyjnych i finansowych. Pełen spokój.
            </div>
        </div>
        """
    
    col_alerts, col_info = st.columns([2, 1])
    
    with col_alerts:
        st.markdown(f'''
            <div class="dash-card" style="max-height: 450px; overflow-y: auto; padding-right: 15px;">
                {alerts_html}
            </div>
        ''', unsafe_allow_html=True)
        
    with col_info:
        st.markdown(f'''
            <div class="dash-card">
                <div class="dash-title">Status Operacyjny</div>
                <div style="color: #8C8477; font-size: 12px; line-height: 1.6;">
                    System stale analizuje statusy zleceń wprowadzonych w zakładce <b>Zlecenia Poboczne</b>. 
                    <br><br>
                    Alerty klasyfikowane są na podstawie ważności:<br>
                    <span style="color: #BA4949;">■ Krytyczne</span> (Brak CMR)<br>
                    <span style="color: #C77F4A;">■ Ostrzeżenia</span> (Brak POD)<br>
                    <span style="color: #C5A880;">■ Administracyjne</span> (Faktury)<br><br>
                    Łączna liczba wymaganych akcji: <b>{suma_problemow}</b>
                </div>
            </div>
        ''', unsafe_allow_html=True)
