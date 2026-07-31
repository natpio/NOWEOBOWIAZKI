import streamlit as st
import pandas as pd
import datetime
import base64
import os
import streamlit.components.v1 as components
from db import load_data

# ==========================================
# FUNKCJE POMOCNICZE (BACKEND & PRZETWARZANIE)
# ==========================================

def get_base64_image(filepath):
    """Konwertuje lokalny plik graficzny na string Base64 do użycia w HTML."""
    try:
        if os.path.exists(filepath):
            with open(filepath, "rb") as img_file:
                return f"data:image/png;base64,{base64.b64encode(img_file.read()).decode()}"
    except Exception as e:
        print(f"Błąd ładowania obrazu {filepath}: {e}")
    return ""

def process_financials(df_ev, df_sub, df_yt):
    """Zaawansowane przetwarzanie i wiekowanie (aging) nieopłaconych faktur."""
    nieoplacone = []
    dzisiaj = pd.Timestamp.today().normalize()
    
    def extract_invoices(df, module_name, id_col, partner_col, cost_col):
        if df.empty: return
        df_nie = df[df.get("Faktura_Oplacona", pd.Series()) == "NIE"]
        for _, r in df_nie.iterrows():
            kwota = pd.to_numeric(r.get(cost_col, 0), errors='coerce')
            termin_str = r.get("Data_Platnosci", "")
            
            # Obliczanie przeterminowania
            status_platnosci = "W terminie"
            dni_opoznienia = 0
            if termin_str and termin_str != "N/A" and termin_str != "":
                try:
                    termin_date = pd.to_datetime(termin_str).normalize()
                    if termin_date < dzisiaj:
                        dni_opoznienia = (dzisiaj - termin_date).days
                        status_platnosci = f"Przeterminowana ({dni_opoznienia} dni)"
                except:
                    status_platnosci = "Błąd daty"

            if kwota > 0:
                nieoplacone.append({
                    "Moduł": module_name, 
                    "ID Operacji": r.get(id_col, ""), 
                    "Kontrahent": r.get(partner_col, ""), 
                    "Kwota (€)": kwota, 
                    "Termin": termin_str,
                    "Status": status_platnosci,
                    "Dni_Opoznienia": dni_opoznienia
                })

    extract_invoices(df_ev, "Eventy", "ID_Zlecenia", "Przewoznik", "Koszt_Transportu_EUR")
    extract_invoices(df_sub, "Subrenty", "ID_Subrentu", "Dostawca", "Koszt_Calkowity_EUR")
    extract_invoices(df_yt, "Yestech", "ID_Yestech", "Przewoznik", "Koszt_Rzeczywisty")

    df_wynik = pd.DataFrame(nieoplacone)
    if not df_wynik.empty:
        df_wynik = df_wynik.sort_values(by="Dni_Opoznienia", ascending=False)
        
    return df_wynik

def generate_alerts(df_ev, df_sub, df_fin):
    """Agreguje i priorytetyzuje operacyjne problemy (Issue Inbox)."""
    alerty = []
    
    # 1. Alerty Krytyczne: Brakujące POD w zakończonych zleceniach
    if not df_ev.empty:
        df_ev_pod = df_ev[(df_ev.get("Zakonczone_Arch", pd.Series()) == "TAK") & (df_ev.get("CMR_Podpisane_POD", pd.Series()) == "NIE")]
        for _, row in df_ev_pod.iterrows():
            alerty.append({
                "typ": "krytyczny", "ikona": "🛑",
                "tytul": f"Brak zwrotu POD: {row.get('Nazwa_Targow', 'Nieznany')}",
                "opis": f"Przewoźnik {row.get('Przewoznik', '-')} nie odesłał dokumentów po zakończonym evencie."
            })
            
    # 2. Alerty Finansowe: Przeterminowane faktury (>14 dni)
    if not df_fin.empty:
        powazne_dlugi = df_fin[df_fin["Dni_Opoznienia"] > 14]
        for _, row in powazne_dlugi.head(3).iterrows():
            alerty.append({
                "typ": "krytyczny", "ikona": "💸",
                "tytul": f"Zaległa płatność: {row['Kontrahent']}",
                "opis": f"Faktura przeterminowana o {row['Dni_Opoznienia']} dni na kwotę {row['Kwota (€)']} €."
            })

    # 3. Alerty Ostrzegawcze: Sprzęt do zwrotu
    if not df_sub.empty:
        df_sub_alert = df_sub[df_sub.get("Status_Subrentu", pd.Series()) == "4. Gotowe do zwrotu (Alert)"]
        for _, row in df_sub_alert.iterrows():
            alerty.append({
                "typ": "ostrzezenie", "ikona": "⚠️",
                "tytul": f"Pilny zwrot na magazynie: {row.get('Co_Jedzie', '-')}",
                "opis": f"Musisz odesłać sprzęt do {row.get('Dostawca', '-')} (Deadline: {row.get('Deadline_Zwrotu', '-')})."
            })
            
    return alerty

# ==========================================
# GŁÓWNA FUNKCJA RENDERUJĄCA WIDOK
# ==========================================

def render(sh):
    # --- POBIERANIE DANYCH ---
    _, df_ev = load_data(sh, "DB_Eventy")
    _, df_sub = load_data(sh, "DB_Subrenty")
    _, df_yt = load_data(sh, "DB_Yestech")

    # --- OBLICZENIA LOGISTYCZNE ---
    df_aktywne_ev = df_ev[df_ev.get("Zakonczone_Arch", pd.Series()) != "TAK"] if not df_ev.empty else pd.DataFrame()
    braki_cmr = len(df_aktywne_ev[df_aktywne_ev.get("CMR_Gotowe", pd.Series()) == "NIE"])
    braki_pod = len(df_aktywne_ev[df_aktywne_ev.get("CMR_Podpisane_POD", pd.Series()) == "NIE"])

    df_finanse = process_financials(df_ev, df_sub, df_yt)
    liczba_faktur = len(df_finanse) if not df_finanse.empty else 0
    kwota_suma = df_finanse["Kwota (€)"].sum() if not df_finanse.empty else 0

    lista_alertow = generate_alerts(df_ev, df_sub, df_finanse)

    # --- ŁADOWANIE GRAFIK DO ZMIENNYCH BASE64 ---
    img_van_b64 = get_base64_image("van.png")
    img_ftl_b64 = get_base64_image("ftl.png")

    # ==========================================
    # SEKCJA 1: ADVANCED KPI CARDS (Natywne kolumny)
    # ==========================================
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="dash-card kpi-advanced" style="padding: 25px;">
            <div class="kpi-adv-header" style="font-size: 15px;">CMR do wystawienia (Aktywne) <span class="icon">📝</span></div>
            <div class="kpi-adv-value" style="font-size: 48px; color: #F8FAFC;">{braki_cmr}</div>
            <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {min(braki_cmr*10, 100)}%;"></div></div>
            <div style="font-size: 12px; color: #64748B; margin-top: 10px;">Wymaga natychmiastowej akcji magazynu</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="dash-card kpi-advanced" style="padding: 25px;">
            <div class="kpi-adv-header" style="font-size: 15px;">Brakujące zwroty POD (Zamknięte) <span class="icon">📄</span></div>
            <div class="kpi-adv-value" style="font-size: 48px; color: #F8FAFC;">{braki_pod}</div>
            <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {min(braki_pod*10, 100)}%; background: #f59e0b;"></div></div>
            <div style="font-size: 12px; color: #64748B; margin-top: 10px;">Monitoruj zewnętrznych przewoźników</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="dash-card kpi-advanced" style="padding: 25px;">
            <div class="kpi-adv-header" style="font-size: 15px;">Nieopłacone faktury zewnętrzne <span class="icon">💰</span></div>
            <div class="kpi-adv-value" style="font-size: 48px; color: #F8FAFC;">{liczba_faktur}</div>
            <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {min(liczba_faktur*5, 100)}%; background: #ef4444;"></div></div>
            <div style="font-size: 12px; color: #ef4444; font-weight: 700; margin-top: 10px;">Zaległości na łączną kwotę: {kwota_suma:,.2f} €</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # SEKCJA 2: PIXEL-PERFECT GLOBAL FLOW (MICRO-FRONTEND)
    # ==========================================
    st.markdown('<h3 class="dash-title" style="margin-bottom: 20px;">Integrated Global Flow & Operacje</h3>', unsafe_allow_html=True)
    
    # Poniższy blok to kompletny mikro-frontend z własnym layoutem Flexbox, animacjami i SVG
    custom_mega_flow_html = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        body {{
            margin: 0; padding: 0; font-family: 'Inter', sans-serif;
            background-color: transparent; color: #F8FAFC;
        }}
        
        /* Główny kontener - odwzorowanie projektu */
        .mega-container {{
            display: flex; gap: 24px;
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px; padding: 24px;
            box-shadow: inset 0 0 40px rgba(0,0,0,0.5), 0 10px 30px rgba(0,0,0,0.3);
            box-sizing: border-box;
            width: 100%; height: 340px;
        }}
        
        /* Lewa strona - Mapa ze ścieżkami SVG */
        .map-zone {{
            flex: 0 0 35%; position: relative;
            background: radial-gradient(circle at center, rgba(30, 41, 59, 0.8) 0%, rgba(2, 6, 23, 0.9) 100%);
            border-radius: 12px; border: 1px solid rgba(255,255,255,0.02);
            display: flex; flex-direction: column; overflow: hidden;
        }}
        .map-header {{
            position: absolute; top: 15px; left: 20px; z-index: 10;
            font-size: 14px; font-weight: 700; color: #e2e8f0; letter-spacing: 0.5px;
        }}
        .map-bg {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: url('https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Europe_orthographic_Caucasus_Urals_boundary.svg/600px-Europe_orthographic_Caucasus_Urals_boundary.svg.png') no-repeat center 80%;
            background-size: 150%; opacity: 0.15; filter: grayscale(100%) brightness(1.5);
        }}
        
        /* Punkty i animacje na mapie */
        .dot {{
            position: absolute; width: 8px; height: 8px; background: #3b82f6;
            border-radius: 50%; box-shadow: 0 0 10px #3b82f6; z-index: 5;
        }}
        .dot.hub {{ background: #D4AF37; width: 12px; height: 12px; box-shadow: 0 0 15px #D4AF37; z-index: 6; }}
        .pulse {{
            position: absolute; width: 30px; height: 30px; background: rgba(212, 175, 55, 0.4);
            border-radius: 50%; top: -9px; left: -9px; z-index: 4;
            animation: radar 2s infinite ease-out;
        }}
        @keyframes radar {{
            0% {{ transform: scale(0.1); opacity: 1; }}
            100% {{ transform: scale(2.5); opacity: 0; }}
        }}
        
        /* Prawa strona - 3 Kolumny Procesów */
        .process-zone {{
            flex: 1; display: flex; gap: 16px;
        }}
        .process-col {{
            flex: 1; display: flex; flex-direction: column;
        }}
        .col-header {{
            font-size: 13px; color: #94A3B8; text-transform: uppercase; font-weight: 700;
            margin-bottom: 15px; padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex; justify-content: space-between; align-items: center;
        }}
        .col-header span.badge {{ background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 10px; font-size: 10px; }}
        
        /* Styl "Inicjacja" - Kafelki firm */
        .partner-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .partner-card {{
            background: #ffffff; height: 50px; border-radius: 6px;
            display: flex; align-items: center; justify-content: center;
            color: #0f172a; font-weight: 800; font-size: 11px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            border-bottom: 3px solid #cbd5e1;
        }}
        .partner-card.alert {{ border-bottom: 3px solid #ef4444; color: #ef4444; }}
        
        /* Styl "W drodze" - Karta Floty SQM z grafikami */
        .fleet-box {{
            background: linear-gradient(145deg, #1e293b, #0f172a);
            border: 1px solid rgba(212, 175, 55, 0.4);
            border-radius: 10px; padding: 16px; height: 100%; box-sizing: border-box;
            position: relative; overflow: hidden;
            box-shadow: 0 10px 20px rgba(0,0,0,0.4);
        }}
        .fleet-header {{ color: #F8FAFC; font-weight: 700; font-size: 14px; margin-bottom: 15px; border-bottom: 1px dashed rgba(255,255,255,0.1); padding-bottom: 10px;}}
        .fleet-images {{ display: flex; gap: 10px; margin-bottom: 15px; justify-content: space-around; }}
        .fleet-img-container {{ width: 45%; height: 60px; background: rgba(0,0,0,0.3); border-radius: 6px; display: flex; align-items: center; justify-content: center; padding: 5px; }}
        .fleet-img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
        .status-row {{ display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 8px; color: #94A3B8; }}
        .status-row strong {{ color: #e2e8f0; }}
        .tag-ok {{ background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 10px; }}
        
        /* Styl "Zamknięte" - Dokumenty */
        .doc-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
        .doc-card {{
            background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 6px; height: 65px; display: flex; flex-direction: column;
            align-items: center; justify-content: center; gap: 5px; position: relative;
        }}
        .doc-icon {{ font-size: 24px; color: #94A3B8; }}
        .doc-check {{ position: absolute; bottom: 5px; right: 5px; background: #10B981; color: #000; font-size: 10px; width: 14px; height: 14px; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-weight: bold; box-shadow: 0 0 5px #10B981;}}

    </style>

    <div class="mega-container">
        
        <!-- SEKCJA MAPY -->
        <div class="map-zone">
            <div class="map-header">Aktywne Trasy</div>
            <div class="map-bg"></div>
            
            <!-- SVG do rysowania zaokrąglonych linii połączeń -->
            <svg style="position: absolute; top:0; left:0; width:100%; height:100%; z-index: 2;">
                <!-- Trasy z Poznania (Hub) do innych miast -->
                <path d="M 150 120 Q 100 80 80 150" fill="transparent" stroke="rgba(212,175,55,0.6)" stroke-width="1.5" stroke-dasharray="4 4" />
                <path d="M 150 120 Q 200 90 220 180" fill="transparent" stroke="rgba(212,175,55,0.6)" stroke-width="1.5" />
                <path d="M 150 120 Q 120 180 90 230" fill="transparent" stroke="rgba(212,175,55,0.6)" stroke-width="1.5" />
            </svg>
            
            <!-- Punkty miast (Współrzędne symulowane dla efektu wizualnego) -->
            <div class="dot hub" style="top: 115px; left: 145px;"><div class="pulse"></div></div> <!-- Poznań -->
            <div class="dot" style="top: 148px; left: 78px;"></div> <!-- Paryż/Londyn -->
            <div class="dot" style="top: 178px; left: 218px;"></div> <!-- Kierunek wschód -->
            <div class="dot" style="top: 228px; left: 88px;"></div> <!-- Madryt -->
        </div>

        <!-- SEKCJA PROCESÓW (3 KOLUMNY) -->
        <div class="process-zone">
            
            <!-- Kolumna 1 -->
            <div class="process-col">
                <div class="col-header">Inicjacja <span class="badge">4 Aktywne</span></div>
                <div class="partner-grid">
                    <div class="partner-card">GEOSpeed</div>
                    <div class="partner-card">AeroCargo</div>
                    <div class="partner-card">FRANTRANS</div>
                    <div class="partner-card alert">L-Acoustics</div>
                </div>
            </div>
            
            <!-- Kolumna 2 (SQM Fleet z grafikami) -->
            <div class="process-col" style="flex: 1.2;">
                <div class="col-header" style="color: #D4AF37; border-bottom-color: rgba(212,175,55,0.3);">W Drodze (SQM Fleet)</div>
                <div class="fleet-box">
                    <div class="fleet-header">Status Floty Własnej</div>
                    <div class="fleet-images">
                        <div class="fleet-img-container">
                            <img src="{img_van_b64}" class="fleet-img" alt="VAN" onerror="this.style.display='none';">
                        </div>
                        <div class="fleet-img-container">
                            <img src="{img_ftl_b64}" class="fleet-img" alt="FTL" onerror="this.style.display='none';">
                        </div>
                    </div>
                    <div class="status-row"><span>Kierowca (VAN):</span> <strong>Kowalski</strong></div>
                    <div class="status-row"><span>Kierowca (FTL):</span> <strong>Nowak</strong></div>
                    <div class="status-row"><span>Status CMR:</span> <span class="tag-ok">WYSTAWIONO ✔</span></div>
                </div>
            </div>
            
            <!-- Kolumna 3 -->
            <div class="process-col">
                <div class="col-header">Zamknięte <span class="badge">Ostatnie 4</span></div>
                <div class="doc-grid">
                    <div class="doc-card">
                        <div class="doc-icon">📄</div><div style="font-size: 10px; color: #64748B;">POD-01</div>
                        <div class="doc-check">✓</div>
                    </div>
                    <div class="doc-card">
                        <div class="doc-icon">📄</div><div style="font-size: 10px; color: #64748B;">POD-02</div>
                        <div class="doc-check">✓</div>
                    </div>
                    <div class="doc-card">
                        <div class="doc-icon">📄</div><div style="font-size: 10px; color: #64748B;">POD-03</div>
                        <div class="doc-check">✓</div>
                    </div>
                    <div class="doc-card" style="opacity: 0.5;">
                        <div class="doc-icon">📄</div><div style="font-size: 10px; color: #64748B;">Oczekuje...</div>
                    </div>
                </div>
            </div>

        </div>
    </div>
    """
    
    # Renderowanie naszego potężnego mikro-frontendu
    components.html(custom_mega_flow_html, height=360)

    # ==========================================
    # SEKCJA 3 & 4: ISSUE INBOX I TABELA FAKTUR
    # ==========================================
    col_inbox, col_fin = st.columns([35, 65], gap="large")

    # Skrzynka Problemów
    with col_inbox:
        st.markdown('<div class="dash-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown('<h3 class="dash-title">Issue Inbox</h3>', unsafe_allow_html=True)
        
        if not lista_alertow:
            st.markdown("<div style='color: #10B981; padding: 20px 0; font-size: 14px; text-align: center;'>✅ Brak palących problemów operacyjnych.<br>Oby tak dalej!</div>", unsafe_allow_html=True)
        else:
            html_inbox = ""
            for alert in lista_alertow:
                klasa_boczna = "alert-danger" if alert["typ"] == "krytyczny" else "alert-warning"
                html_inbox += f"""
                <div class="alert-item {klasa_boczna}" style="background: rgba(0,0,0,0.2); border-radius: 6px; padding: 12px; margin-bottom: 12px;">
                    <div style="display: flex; gap: 10px; align-items: flex-start;">
                        <div style="font-size: 18px;">{alert['ikona']}</div>
                        <div>
                            <strong style="color: #F8FAFC; display: block; font-size: 13px; margin-bottom: 4px;">{alert['tytul']}</strong>
                            <span style="color: #94A3B8; font-size: 12px; line-height: 1.4;">{alert['opis']}</span>
                        </div>
                    </div>
                </div>
                """
            st.markdown(html_inbox, unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

    # Kontrola Płatności i Aging Faktur
    with col_fin:
        st.markdown('<div class="dash-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown(f'<h3 class="dash-title">Rozliczenia Zewnętrzne: Oczekujące Płatności</h3>', unsafe_allow_html=True)
        
        if not df_finanse.empty:
            # Używamy Pandas Styler do pokolorowania statusów przeterminowania
            def color_status(val):
                if "Przeterminowana" in str(val): return 'color: #ef4444; font-weight: bold;'
                if "W terminie" in str(val): return 'color: #10B981;'
                return 'color: #94A3B8;'

            # Ukrywamy techniczną kolumnę do sortowania (Dni_Opoznienia) i formatujemy resztę
            df_widok = df_finanse.drop(columns=["Dni_Opoznienia"])
            styled_df = df_widok.style.map(color_status, subset=['Status']).format({'Kwota (€)': "{:.2f} €"})
            
            st.dataframe(
                styled_df, 
                use_container_width=True, 
                hide_index=True,
                height=250
            )
        else:
            st.info("✅ Wszystkie zarejestrowane faktury w systemie są opłacone.")
            
        st.markdown('</div>', unsafe_allow_html=True)
