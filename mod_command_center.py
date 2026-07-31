import streamlit as st
import pandas as pd
import datetime
import base64
import os
import streamlit.components.v1 as components
from db import load_data
import math

# =====================================================================
# 1. KONFIGURACJA I SŁOWNIKI GEOGRAFICZNE (BAZA MIAST Z TWOICH ARKUSZY)
# =====================================================================

# Słownik z geolokalizacją (Lat, Lon) dla destynacji z Twojego pliku 1.jpg
GEO_DICT = {
    "POZNAŃ": (52.4064, 16.9252), # Hub SQM
    "MONACHIUM": (48.1351, 11.5820),
    "MUNICH": (48.1351, 11.5820),
    "KOLONIA": (50.9375, 6.9603),
    "COLOGNE": (50.9375, 6.9603),
    "FRANKFURT": (50.1109, 8.6821),
    "KOPENHAGA": (55.6761, 12.5683),
    "KIELCE": (50.8703, 20.6275),
    "LONDYN": (51.5074, -0.1278),
    "LONDON": (51.5074, -0.1278),
    "GUYANCOURT": (48.7718, 2.0494), # Okolice Paryża
    "SZTOKHOLM": (59.3293, 18.0686),
    "STOCKHOLM": (59.3293, 18.0686),
    "HANOWER": (52.3759, 9.7320),
    "HANOVER": (52.3759, 9.7320),
    "PARYŻ": (48.8566, 2.3522),
    "PARIS": (48.8566, 2.3522),
    "BERLIN": (52.5200, 13.4050),
    "HAMBURG": (53.5511, 9.9937),
    "WURSELEN": (50.8214, 6.1386),
    "MADRYT": (40.4168, -3.7038)
}

# Parametry okna mapy (projekcja Merkatora na uproszczony SVG)
MAP_BOUNDS = {
    "min_lat": 36.0, "max_lat": 63.0,
    "min_lon": -10.0, "max_lon": 30.0,
    "svg_width": 300, "svg_height": 200
}

# =====================================================================
# 2. KLASY PRZETWARZANIA DANYCH (BACKEND LOGIC)
# =====================================================================

class LogistykaDataProcessor:
    """Klasa agregująca i czyszcząca dane ze wszystkich modułów SQM."""
    
    def __init__(self, df_ev, df_sub, df_yt):
        # Inicjalizacja i czyszczenie pustych DataFrame'ów
        self.df_ev = df_ev if not df_ev.empty else pd.DataFrame()
        self.df_sub = df_sub if not df_sub.empty else pd.DataFrame()
        self.df_yt = df_yt if not df_yt.empty else pd.DataFrame()
        self.dzisiaj = pd.Timestamp.today().normalize()
        
    def get_aktywne_eventy(self):
        """Zwraca tylko niezarchiwizowane eventy."""
        if self.df_ev.empty:
            return pd.DataFrame()
        return self.df_ev[self.df_ev.get("Zakonczone_Arch", pd.Series()) != "TAK"]

    def get_zamkniete_eventy(self):
        """Zwraca zarchiwizowane eventy do analizy POD."""
        if self.df_ev.empty:
            return pd.DataFrame()
        return self.df_ev[self.df_ev.get("Zakonczone_Arch", pd.Series()) == "TAK"]

    def extract_financials(self):
        """Przetwarza wszystkie faktury i oblicza Dni Opóźnienia (Aging)."""
        nieoplacone = []
        
        def parse_module(df, mod_name, id_col, partner_col, cost_col):
            if df.empty: return
            
            # Filtrujemy tylko nieopłacone
            df_nie = df[df.get("Faktura_Oplacona", pd.Series()) == "NIE"]
            for _, row in df_nie.iterrows():
                # Bezpieczne wyciąganie kwoty
                try:
                    kwota = float(str(row.get(cost_col, 0)).replace(',', '.'))
                except ValueError:
                    kwota = 0.0
                
                if kwota <= 0:
                    continue
                    
                termin_str = str(row.get("Data_Platnosci", "")).strip()
                partner = str(row.get(partner_col, "")).strip()
                
                # Tylko zewnetrzni partnerzy, pomijamy Flotę SQM i N/A
                if partner.upper() in ["SQM", "WŁASNY SQM", ""] or termin_str == "N/A":
                    continue

                status_platnosci = "W terminie"
                dni_opoznienia = 0
                
                if termin_str and termin_str not in ["None", "nan", "NaT"]:
                    try:
                        termin_date = pd.to_datetime(termin_str).normalize()
                        if termin_date < self.dzisiaj:
                            dni_opoznienia = (self.dzisiaj - termin_date).days
                            status_platnosci = f"Przeterminowana ({dni_opoznienia} dni)"
                    except Exception:
                        status_platnosci = "Brak / Błędna data"

                nieoplacone.append({
                    "Moduł": mod_name, 
                    "ID Operacji": row.get(id_col, "-"), 
                    "Kontrahent": partner, 
                    "Kwota (€)": kwota, 
                    "Termin": termin_str,
                    "Status": status_platnosci,
                    "Dni_Opoznienia": dni_opoznienia
                })

        parse_module(self.df_ev, "Event", "ID_Zlecenia", "Przewoznik", "Koszt_Transportu_EUR")
        parse_module(self.df_sub, "Subrent", "ID_Subrentu", "Dostawca", "Koszt_Calkowity_EUR")
        parse_module(self.df_yt, "Yestech", "ID_Yestech", "Przewoznik", "Koszt_Rzeczywisty")

        df_wynik = pd.DataFrame(nieoplacone)
        if not df_wynik.empty:
            df_wynik = df_wynik.sort_values(by="Dni_Opoznienia", ascending=False)
        return df_wynik

    def generate_alerts(self, df_finanse):
        """Generuje skrzynkę problemów bazując TYLKO na twardych danych z DB."""
        alerty = []
        
        # 1. Alerty Krytyczne: Brakujące POD (Eventy zakończone)
        zamkniete = self.get_zamkniete_eventy()
        if not zamkniete.empty:
            df_ev_pod = zamkniete[zamkniete.get("CMR_Podpisane_POD", pd.Series()) == "NIE"]
            for _, row in df_ev_pod.iterrows():
                # Ignoruj flotę własną (POD dotyczy głównie zewn.) chyba że SQM też wymaga.
                if row.get("Typ_Transportu", "") != "Własny SQM":
                    alerty.append({
                        "typ": "krytyczny", "ikona": "🛑",
                        "tytul": f"Brak POD: {row.get('Nazwa_Targow', 'Nieznana destynacja')}",
                        "opis": f"Przewoźnik {row.get('Przewoznik', '-')} nie odesłał dokumentów przewozowych."
                    })
                
        # 2. Alerty Ostrzegawcze: Gotowe do zwrotu (Subrenty)
        if not self.df_sub.empty:
            df_sub_alert = self.df_sub[self.df_sub.get("Status_Subrentu", pd.Series()) == "4. Gotowe do zwrotu (Alert)"]
            for _, row in df_sub_alert.iterrows():
                alerty.append({
                    "typ": "ostrzezenie", "ikona": "⚠️",
                    "tytul": f"Zwrot sprzętu: {row.get('Co_Jedzie', '-')}",
                    "opis": f"Sprzęt oczekuje na zwrot do: {row.get('Dostawca', '-')} (Deadline: {row.get('Deadline_Zwrotu', '-')})."
                })
                
        # 3. Alerty Finansowe: Poważne zadłużenie
        if not df_finanse.empty:
            powazne_dlugi = df_finanse[df_finanse["Dni_Opoznienia"] > 14]
            for _, row in powazne_dlugi.head(3).iterrows():
                alerty.append({
                    "typ": "finanse", "ikona": "💸",
                    "tytul": f"Zaległa faktura: {row['Kontrahent']}",
                    "opis": f"Opóźnienie płatności o {row['Dni_Opoznienia']} dni na kwotę {row['Kwota (€)']} €."
                })
                
        return alerty

# =====================================================================
# 3. GENERATOR KOMPONENTÓW HTML/CSS (PIXEL PERFECT MICRO-FRONTEND)
# =====================================================================

def get_base64_image(filepath):
    """Bezpieczne ładowanie grafik b64 z obsługą błędów."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "rb") as img_file:
                return f"data:image/png;base64,{base64.b64encode(img_file.read()).decode()}"
        except Exception:
            pass
    return ""

def latlon_to_svg(lat, lon):
    """Prosta projekcja pseudo-Merkatora do współrzędnych SVG."""
    w = MAP_BOUNDS["svg_width"]
    h = MAP_BOUNDS["svg_height"]
    
    # Skalowanie Lon (X)
    x = (lon - MAP_BOUNDS["min_lon"]) / (MAP_BOUNDS["max_lon"] - MAP_BOUNDS["min_lon"]) * w
    
    # Skalowanie Lat (Y) - Merkator (odwrócona oś Y)
    lat_rad = lat * math.pi / 180.0
    merc_n = math.log(math.tan((math.pi / 4.0) + (lat_rad / 2.0)))
    
    min_lat_rad = MAP_BOUNDS["min_lat"] * math.pi / 180.0
    max_lat_rad = MAP_BOUNDS["max_lat"] * math.pi / 180.0
    min_merc = math.log(math.tan((math.pi / 4.0) + (min_lat_rad / 2.0)))
    max_merc = math.log(math.tan((math.pi / 4.0) + (max_lat_rad / 2.0)))
    
    y = h - ((merc_n - min_merc) / (max_merc - min_merc) * h)
    return x, y

def build_dynamic_flow_html(aktywne_ev, zamkniete_ev):
    """
    Kluczowa funkcja generująca DYNAMICZNY kod HTML na podstawie FAKTYCZNYCH danych.
    Zero zmyślonych kierowców i przewoźników.
    """
    
    # 1. PARSOWANIE: Faza INICJACJI (Zewnętrzni partnerzy)
    inicjacja_ev = aktywne_ev[aktywne_ev.get("Faza_Procesu", pd.Series()).isin(["Inicjacja", "Planowanie"])]
    zewnetrzni_partnerzy = set()
    for _, row in inicjacja_ev.iterrows():
        if row.get("Typ_Transportu", "") != "Własny SQM":
            przewoznik = str(row.get("Przewoznik", "")).strip().upper()
            if przewoznik and przewoznik not in ["", "SQM", "N/A"]:
                zewnetrzni_partnerzy.add(przewoznik[:15]) # Limit długości dla UI
    
    html_inicjacja = ""
    if not zewnetrzni_partnerzy:
        html_inicjacja = "<div class='logo-item dark' style='grid-column: 1 / -1;'>Brak inicjacji</div>"
    else:
        for p in list(zewnetrzni_partnerzy)[:4]: # Max 4 w kafelku
            html_inicjacja += f"<div class='logo-item'>{p}</div>"

    # 2. PARSOWANIE: Faza W DRODZE (Tylko SQM Fleet)
    w_drodze_ev = aktywne_ev[
        (aktywne_ev.get("Faza_Procesu", pd.Series()).isin(["Trasa", "Załadunek"])) & 
        (aktywne_ev.get("Typ_Transportu", pd.Series()) == "Własny SQM")
    ]
    
    html_flota = ""
    if w_drodze_ev.empty:
        html_flota = """
        <div class="fleet-box" style="display:flex; align-items:center; justify-content:center; color:#64748B;">
            Aktualnie brak pojazdów SQM w trasie.
        </div>"""
    else:
        html_flota = '<div class="fleet-box"><div class="fleet-header">Status Pojazdów w Trasie</div>'
        # Pobieranie grafik
        b64_bus = get_base64_image("bus.png")
        b64_van = get_base64_image("van.png")
        b64_ftl = get_base64_image("ftl.png")
        b64_sol = get_base64_image("solowka.png")
        
        for idx, row in w_drodze_ev.head(2).iterrows(): # Pokazujemy max 2 pojazdy by zachowac UI
            typ = str(row.get("Typ_Pojazdu", "")).upper()
            kierowca = str(row.get("Przewoznik", "Nieznany")).title()
            cmr_status = str(row.get("CMR_Gotowe", "NIE")).upper()
            cmr_klasa = "tag-ok" if cmr_status == "TAK" else "tag-alert"
            
            # Dobór grafiki bazując na typie (z DB)
            img_src = b64_van # Domyslny
            if "BUS" in typ: img_src = b64_bus
            elif "FTL" in typ: img_src = b64_ftl
            elif "SOL" in typ: img_src = b64_sol
            
            html_flota += f"""
            <div style="display: flex; gap: 10px; margin-bottom: 12px; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px;">
                <div style="width: 50px; height: 35px; background: rgba(0,0,0,0.4); border-radius: 4px; display:flex; align-items:center; justify-content:center;">
                    <img src="{img_src}" style="max-width: 90%; max-height: 90%;" onerror="this.style.display='none';">
                </div>
                <div style="flex: 1;">
                    <div style="font-size: 11px; color:#94A3B8;">Kierowca: <strong style="color:#F8FAFC;">{kierowca}</strong></div>
                    <div style="font-size: 10px; color:#94A3B8; margin-top:2px;">CMR: <span class="{cmr_klasa}">{cmr_status}</span></div>
                </div>
            </div>
            """
        html_flota += "</div>"

    # 3. PARSOWANIE: Faza ZAMKNIĘTE (Dokumenty POD z DB)
    html_zamkniete = ""
    if zamkniete_ev.empty:
        html_zamkniete = "<div class='logo-item dark' style='grid-column: 1 / -1;'>Brak historii</div>"
    else:
        for idx, row in zamkniete_ev.tail(4).iterrows():
            id_zew = str(row.get("ID_Zlecenia", "BRAK"))[:7]
            pod_status = str(row.get("CMR_Podpisane_POD", "NIE")).upper()
            
            if pod_status == "TAK":
                html_zamkniete += f"""
                <div class="doc-card">
                    <div class="doc-icon">📄</div><div style="font-size: 9px; color: #64748B;">{id_zew}</div>
                    <div class="doc-check">✓</div>
                </div>"""
            else:
                html_zamkniete += f"""
                <div class="doc-card" style="opacity: 0.6; border-color: rgba(239, 68, 68, 0.3);">
                    <div class="doc-icon" style="color: #ef4444;">📄</div><div style="font-size: 9px; color: #ef4444;">Brak POD</div>
                </div>"""

    # 4. MAPA I LINIE (DYNAMICZNY SVG)
    svg_lines = ""
    html_dots = ""
    
    # Rysowanie huba (Poznań)
    hx, hy = latlon_to_svg(GEO_DICT["POZNAŃ"][0], GEO_DICT["POZNAŃ"][1])
    html_dots += f'<div class="dot hub" style="top: {hy}px; left: {hx}px;"><div class="pulse"></div></div>'
    
    # Rysowanie destynacji aktywnych
    unikalne_destynacje = set()
    for _, row in aktywne_ev.iterrows():
        targi = str(row.get("Nazwa_Targow", "")).upper()
        # Proste dopasowanie nazwy z bazy do słownika
        for miasto in GEO_DICT.keys():
            if miasto in targi:
                unikalne_destynacje.add(miasto)
                break
                
    for dest in unikalne_destynacje:
        if dest != "POZNAŃ":
            dx, dy = latlon_to_svg(GEO_DICT[dest][0], GEO_DICT[dest][1])
            html_dots += f'<div class="dot" style="top: {dy}px; left: {dx}px;"></div>'
            # Rysowanie krzywej Beziera od Poznania do destynacji
            ctrl_y = min(hy, dy) - 30 # Lekkie wygięcie krzywej w górę
            svg_lines += f'<path d="M {hx+6} {hy+6} Q {(hx+dx)/2} {ctrl_y} {dx+4} {dy+4}" fill="transparent" stroke="rgba(212,175,55,0.8)" stroke-width="1.5" stroke-dasharray="3 3" />'


    # 5. SKŁADANIE KOŃCOWEGO HTML'A
    css_string = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        body { margin: 0; padding: 0; font-family: 'Inter', sans-serif; background-color: transparent; color: #F8FAFC; overflow: hidden; }
        .mega-container {
            display: flex; gap: 20px; background: rgba(15, 23, 42, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 20px;
            box-shadow: inset 0 0 40px rgba(0,0,0,0.5), 0 10px 30px rgba(0,0,0,0.3); height: 350px; box-sizing: border-box;
        }
        .map-zone {
            flex: 0 0 35%; position: relative; background: radial-gradient(circle at center, rgba(30, 41, 59, 0.8) 0%, rgba(2, 6, 23, 0.9) 100%);
            border-radius: 10px; border: 1px solid rgba(255,255,255,0.02); overflow: hidden;
        }
        .map-bg {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: url('https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Europe_orthographic_Caucasus_Urals_boundary.svg/600px-Europe_orthographic_Caucasus_Urals_boundary.svg.png') no-repeat center 80%;
            background-size: 140%; opacity: 0.15; filter: grayscale(100%) brightness(1.5);
        }
        .map-header { position: absolute; top: 10px; left: 15px; font-size: 12px; font-weight: 700; color: #e2e8f0; z-index: 10;}
        .dot { position: absolute; width: 8px; height: 8px; background: #3b82f6; border-radius: 50%; box-shadow: 0 0 10px #3b82f6; z-index: 5; }
        .dot.hub { background: #D4AF37; width: 12px; height: 12px; box-shadow: 0 0 15px #D4AF37; z-index: 6; }
        .pulse { position: absolute; width: 26px; height: 26px; background: rgba(212, 175, 55, 0.4); border-radius: 50%; top: -7px; left: -7px; z-index: 4; animation: radar 2s infinite ease-out; }
        @keyframes radar { 0% { transform: scale(0.1); opacity: 1; } 100% { transform: scale(2.5); opacity: 0; } }
        
        .process-zone { flex: 1; display: flex; gap: 15px; }
        .process-col { flex: 1; display: flex; flex-direction: column; }
        .col-header { font-size: 12px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 15px; padding-bottom: 5px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .logo-grid, .doc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .logo-item { background: #ffffff; height: 40px; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #0f172a; font-weight: 800; font-size: 10px; text-align: center; padding: 0 5px;}
        .logo-item.dark { background: rgba(255,255,255,0.05); color: #94A3B8; border: 1px dashed rgba(255,255,255,0.1); }
        .fleet-box { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid rgba(212, 175, 55, 0.4); border-radius: 8px; padding: 12px; height: 100%; box-sizing: border-box; }
        .fleet-header { color: #F8FAFC; font-weight: 700; font-size: 12px; margin-bottom: 15px; border-bottom: 1px dashed rgba(255,255,255,0.1); padding-bottom: 8px;}
        .tag-ok { background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 9px; }
        .tag-alert { background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 9px; }
        .doc-card { background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; height: 60px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; position: relative; }
        .doc-icon { font-size: 20px; color: #94A3B8; }
        .doc-check { position: absolute; bottom: 4px; right: 4px; background: #10B981; color: #000; font-size: 9px; width: 12px; height: 12px; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-weight: bold;}
    </style>
    """

    final_html = f"""
    {css_string}
    <div class="mega-container">
        <!-- ZONA MAPY -->
        <div class="map-zone">
            <div class="map-header">Aktywne Trasy Z bazy</div>
            <div class="map-bg"></div>
            <svg style="position: absolute; top:0; left:0; width:100%; height:100%; z-index: 2;">
                {svg_lines}
            </svg>
            {html_dots}
        </div>
        
        <!-- ZONA PROCESOW -->
        <div class="process-zone">
            <div class="process-col">
                <div class="col-header">Inicjacja (Zewn.)</div>
                <div class="logo-grid">{html_inicjacja}</div>
            </div>
            
            <div class="process-col" style="flex: 1.3;">
                <div class="col-header" style="color: #D4AF37; border-bottom-color: rgba(212,175,55,0.3);">W Drodze (SQM Fleet)</div>
                {html_flota}
            </div>
            
            <div class="process-col">
                <div class="col-header">Zamknięte (Status POD)</div>
                <div class="doc-grid">{html_zamkniete}</div>
            </div>
        </div>
    </div>
    """
    return final_html

# =====================================================================
# 4. GŁÓWNA FUNKCJA RENDERUJĄCA STREAMLIT
# =====================================================================

def render(sh):
    # --- 1. ŁADOWANIE I WSTĘPNE PRZETWARZANIE ---
    try:
        _, df_ev = load_data(sh, "DB_Eventy")
        _, df_sub = load_data(sh, "DB_Subrenty")
        _, df_yt = load_data(sh, "DB_Yestech")
    except Exception as e:
        st.error(f"Krytyczny błąd pobierania danych: {e}")
        return

    processor = LogistykaDataProcessor(df_ev, df_sub, df_yt)
    aktywne_ev = processor.get_aktywne_eventy()
    zamkniete_ev = processor.get_zamkniete_eventy()
    
    df_finanse = processor.extract_financials()
    alerty = processor.generate_alerts(df_finanse)

    # Obliczenia KPI
    braki_cmr = len(aktywne_ev[aktywne_ev.get("CMR_Gotowe", pd.Series()) == "NIE"]) if not aktywne_ev.empty else 0
    braki_pod = len(zamkniete_ev[zamkniete_ev.get("CMR_Podpisane_POD", pd.Series()) == "NIE"]) if not zamkniete_ev.empty else 0
    
    liczba_faktur = len(df_finanse) if not df_finanse.empty else 0
    kwota_suma = df_finanse["Kwota (€)"].sum() if not df_finanse.empty else 0.0

    # --- 2. GŁÓWNY INTERFEJS (KARTY KPI) ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="dash-card kpi-advanced" style="padding: 20px;">
            <div class="kpi-adv-header" style="font-size: 14px;">CMR do wystawienia (Aktywne) <span class="icon">📝</span></div>
            <div class="kpi-adv-value" style="font-size: 42px; color: #F8FAFC;">{braki_cmr}</div>
            <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {min(braki_cmr*10, 100)}%;"></div></div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="dash-card kpi-advanced" style="padding: 20px;">
            <div class="kpi-adv-header" style="font-size: 14px;">Brakujące zwroty POD (Zamknięte) <span class="icon">📄</span></div>
            <div class="kpi-adv-value" style="font-size: 42px; color: #F8FAFC;">{braki_pod}</div>
            <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {min(braki_pod*10, 100)}%; background: #f59e0b;"></div></div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="dash-card kpi-advanced" style="padding: 20px;">
            <div class="kpi-adv-header" style="font-size: 14px;">Nieopłacone faktury zewn. <span class="icon">💰</span></div>
            <div class="kpi-adv-value" style="font-size: 42px; color: #F8FAFC;">{liczba_faktur}</div>
            <div class="kpi-progress-bar"><div class="kpi-progress" style="width: {min(liczba_faktur*5, 100)}%; background: #ef4444;"></div></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 3. DYNAMICZNY MICRO-FRONTEND WIZUALNY ---
    st.markdown('<h3 class="dash-title">Rzeczywisty Przepływ Operacyjny (Live)</h3>', unsafe_allow_html=True)
    
    # Generowanie HTML'a zasilonego prawdziwymi danymi ze SQM Sheets
    html_flow = build_dynamic_flow_html(aktywne_ev, zamkniete_ev)
    components.html(html_flow, height=360)

    # --- 4. ISSUE INBOX ORAZ TABELA FAKTUR ---
    col_inbox, col_fin = st.columns([35, 65], gap="large")

    with col_inbox:
        st.markdown('<div class="dash-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown('<h3 class="dash-title">Skrzynka Problemów (Issue Inbox)</h3>', unsafe_allow_html=True)
        
        if not alerty:
            st.markdown("<div style='color: #10B981; padding: 20px 0; font-size: 13px; text-align: center;'>✅ Brak palących problemów operacyjnych w bazach danych.</div>", unsafe_allow_html=True)
        else:
            html_inbox = ""
            for a in alerty:
                k_boczna = "alert-danger" if a["typ"] == "krytyczny" else ("alert-warning" if a["typ"] == "ostrzezenie" else "alert-warning")
                html_inbox += f"""
                <div class="alert-item {k_boczna}" style="background: rgba(0,0,0,0.2); border-radius: 6px; padding: 10px; margin-bottom: 10px;">
                    <div style="display: flex; gap: 10px; align-items: flex-start;">
                        <div style="font-size: 16px;">{a['ikona']}</div>
                        <div>
                            <strong style="color: #F8FAFC; display: block; font-size: 12px; margin-bottom: 2px;">{a['tytul']}</strong>
                            <span style="color: #94A3B8; font-size: 11px; line-height: 1.3;">{a['opis']}</span>
                        </div>
                    </div>
                </div>
                """
            st.markdown(html_inbox, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_fin:
        st.markdown('<div class="dash-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown(f'<h3 class="dash-title" style="color: #ef4444;">Faktury oczekujące na opłacenie (Zobowiązania: {kwota_suma:,.2f} €)</h3>', unsafe_allow_html=True)
        
        if not df_finanse.empty:
            def color_status(val):
                if "Przeterminowana" in str(val): return 'color: #ef4444; font-weight: bold;'
                if "W terminie" in str(val): return 'color: #10B981;'
                return 'color: #94A3B8;'

            df_widok = df_finanse.drop(columns=["Dni_Opoznienia"])
            styled_df = df_widok.style.map(color_status, subset=['Status']).format({'Kwota (€)': "{:.2f} €"})
            
            st.dataframe(
                styled_df, 
                use_container_width=True, 
                hide_index=True,
                height=260
            )
        else:
            st.info("✅ Brak nieopłaconych faktur zewnętrznych w systemie (Subrenty, Yestech, Eventy).")
            
        st.markdown('</div>', unsafe_allow_html=True)
