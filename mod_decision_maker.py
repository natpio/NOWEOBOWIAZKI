import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

def get_all_rates():
    """Baza danych stawek twardo przepisana z cennika PRICELIST 2026 v4.3.1"""
    return {
        'WŁASNY SQM BUS': {'postoj': 30.0, 'vClass': 'BUS', 'type': 'SQM', 'exp': {'Amsterdam': 373.8, 'Barcelona': 1106.4, 'Bazylea': 481.2, 'Berlin': 129, 'Bruksela': 415.2, 'Budapeszt': 324.6, 'Cannes / Nicea': 826.8, 'Frankfurt nad Menem': 331.8, 'Gdańsk': 162.6, 'Genewa': 648.6, 'Hamburg': 238.2, 'Hannover': 226.2, 'Kielce': 187.8, 'Kolonia / Dusseldorf': 359.4, 'Kopenhaga': 273.6, 'Lipsk': 186, 'Liverpool': 725.4, 'Lizbona': 1585.8, 'Londyn': 352.8, 'Lyon': 707.4, 'Madryt': 1382.4, 'Manchester': 717, 'Mediolan': 633.6, 'Monachium': 347.4, 'Norymberga': 285.6, 'Paryż': 577.8, 'Praga': 180.6, 'Rzym': 846.6, 'Sewilla': 988.2, 'Sofia': 704.4, 'Sztokholm': 668.4, 'Tuluza': 1000.2, 'Warszawa': 169.2, 'Wiedeń': 285.6}, 'imp': {'Amsterdam': 373.8, 'Barcelona': 1106.4, 'Bazylea': 481.2, 'Berlin': 129, 'Bruksela': 415.2, 'Budapeszt': 324.6, 'Cannes / Nicea': 826.8, 'Frankfurt nad Menem': 331.8, 'Gdańsk': 162.6, 'Genewa': 648.6, 'Hamburg': 238.2, 'Hannover': 226.2, 'Kielce': 187.8, 'Kolonia / Dusseldorf': 359.4, 'Kopenhaga': 273.6, 'Lipsk': 186, 'Liverpool': 725.4, 'Lizbona': 1585.8, 'Londyn': 352.8, 'Lyon': 707.4, 'Madryt': 1382.4, 'Manchester': 717, 'Mediolan': 633.6, 'Monachium': 347.4, 'Norymberga': 285.6, 'Paryż': 577.8, 'Praga': 180.6, 'Rzym': 846.6, 'Sewilla': 988.2, 'Sofia': 704.4, 'Sztokholm': 668.4, 'Tuluza': 1000.2, 'Warszawa': 169.2, 'Wiedeń': 285.6}, 'dniowki': {}}, 
        'WŁASNY SQM SOLO': {'postoj': 150.0, 'vClass': 'SOLO', 'type': 'SQM', 'exp': {'Amsterdam': 626.4, 'Barcelona': 1638.6, 'Bazylea': 1638.6, 'Berlin': 202.2, 'Bruksela': 705.6, 'Budapeszt': 493.2, 'Cannes / Nicea': 1251.6, 'Frankfurt nad Menem': 586.2, 'Gdańsk': 252.6, 'Genewa': 1104, 'Hamburg': 410.4, 'Hannover': 388.2, 'Kielce': 286.2, 'Kolonia / Dusseldorf': 627, 'Kopenhaga': 440.4, 'Lipsk': 314.4, 'Liverpool': 1117.8, 'Lizbona': 2215.8, 'Londyn': 669.6, 'Lyon': 1131, 'Madryt': 1956, 'Manchester': 1107, 'Mediolan': 1002.6, 'Monachium': 616.2, 'Norymberga': 501.6, 'Paryż': 948.6, 'Praga': 255, 'Rzym': 1267.8, 'Sewilla': 1455, 'Sofia': 1089.6, 'Sztokholm': 532.8, 'Tuluza': 1510.2, 'Warszawa': 251.4, 'Wiedeń': 352.2}, 'imp': {'Amsterdam': 626.4, 'Barcelona': 1638.6, 'Bazylea': 1638.6, 'Berlin': 202.2, 'Bruksela': 705.6, 'Budapeszt': 493.2, 'Cannes / Nicea': 1251.6, 'Frankfurt nad Menem': 586.2, 'Gdańsk': 252.6, 'Genewa': 1104, 'Hamburg': 410.4, 'Hannover': 388.2, 'Kielce': 286.2, 'Kolonia / Dusseldorf': 627, 'Kopenhaga': 440.4, 'Lipsk': 314.4, 'Liverpool': 1117.8, 'Lizbona': 2215.8, 'Londyn': 669.6, 'Lyon': 1131, 'Madryt': 1956, 'Manchester': 1107, 'Mediolan': 1002.6, 'Monachium': 616.2, 'Norymberga': 501.6, 'Paryż': 948.6, 'Praga': 255, 'Rzym': 1267.8, 'Sewilla': 1455, 'Sofia': 1089.6, 'Sztokholm': 532.8, 'Tuluza': 1510.2, 'Warszawa': 251.4, 'Wiedeń': 352.2}, 'dniowki': {'Amsterdam': 680, 'Barcelona': 1360, 'Bazylea': 680, 'Berlin': 340, 'Bruksela': 680, 'Budapeszt': 340, 'Cannes / Nicea': 1020, 'Frankfurt nad Menem': 680, 'Gdańsk': 340, 'Genewa': 680, 'Hamburg': 340, 'Hannover': 340, 'Kielce': 340, 'Kolonia / Dusseldorf': 680, 'Kopenhaga': 680, 'Lipsk': 340, 'Liverpool': 1020, 'Lizbona': 1700, 'Londyn': 1020, 'Lyon': 1020, 'Madryt': 1360, 'Manchester': 1020, 'Mediolan': 680, 'Monachium': 680, 'Norymberga': 340, 'Paryż': 680, 'Praga': 340, 'Rzym': 1360, 'Sewilla': 1700, 'Sofia': 1020, 'Sztokholm': 1020, 'Tuluza': 1360, 'Warszawa': 340, 'Wiedeń': 680}}, 
        'WŁASNY SQM FTL': {'postoj': 150.0, 'vClass': 'FTL', 'type': 'SQM', 'exp': {'Amsterdam': 874.8, 'Barcelona': 2156.4, 'Bazylea': 1148.4, 'Berlin': 277.2, 'Bruksela': 1009.2, 'Budapeszt': 639.6, 'Cannes / Nicea': 1895.4, 'Frankfurt nad Menem': 819.6, 'Gdańsk': 310.8, 'Genewa': 1908, 'Hamburg': 571.2, 'Hannover': 540, 'Kielce': 355.8, 'Kolonia / Dusseldorf': 877.2, 'Kopenhaga': 636.6, 'Lipsk': 435.6, 'Liverpool': 1540.2, 'Lizbona': 2920.8, 'Londyn': 924, 'Lyon': 1524, 'Madryt': 2565, 'Manchester': 1524.6, 'Mediolan': 1542.6, 'Monachium': 862.2, 'Norymberga': 700.8, 'Paryż': 1292.4, 'Praga': 351, 'Rzym': 1812, 'Sewilla': 1869, 'Sofia': 1502.4, 'Sztokholm': 723, 'Tuluza': 1956.6, 'Warszawa': 313.8, 'Wiedeń': 478.2}, 'imp': {'Amsterdam': 874.8, 'Barcelona': 2156.4, 'Bazylea': 1148.4, 'Berlin': 277.2, 'Bruksela': 1009.2, 'Budapeszt': 639.6, 'Cannes / Nicea': 1895.4, 'Frankfurt nad Menem': 819.6, 'Gdańsk': 310.8, 'Genewa': 1908, 'Hamburg': 571.2, 'Hannover': 540, 'Kielce': 355.8, 'Kolonia / Dusseldorf': 877.2, 'Kopenhaga': 636.6, 'Lipsk': 435.6, 'Liverpool': 1540.2, 'Lizbona': 2920.8, 'Londyn': 924, 'Lyon': 1524, 'Madryt': 2565, 'Manchester': 1524.6, 'Mediolan': 1542.6, 'Monachium': 862.2, 'Norymberga': 700.8, 'Paryż': 1292.4, 'Praga': 351, 'Rzym': 1812, 'Sewilla': 1869, 'Sofia': 1502.4, 'Sztokholm': 723, 'Tuluza': 1956.6, 'Warszawa': 313.8, 'Wiedeń': 478.2}, 'dniowki': {'Amsterdam': 680, 'Barcelona': 1360, 'Bazylea': 680, 'Berlin': 340, 'Bruksela': 680, 'Budapeszt': 340, 'Cannes / Nicea': 1020, 'Frankfurt nad Menem': 680, 'Gdańsk': 340, 'Genewa': 680, 'Hamburg': 340, 'Hannover': 340, 'Kielce': 340, 'Kolonia / Dusseldorf': 680, 'Kopenhaga': 680, 'Lipsk': 340, 'Liverpool': 1020, 'Lizbona': 1700, 'Londyn': 1020, 'Lyon': 1020, 'Madryt': 1360, 'Manchester': 1020, 'Mediolan': 680, 'Monachium': 680, 'Norymberga': 340, 'Paryż': 680, 'Praga': 340, 'Rzym': 1360, 'Sewilla': 1700, 'Sofia': 1020, 'Sztokholm': 1020, 'Tuluza': 1360, 'Warszawa': 340, 'Wiedeń': 680}}, 
        'PREMIUM TRANSPORT': {'postoj': 330.0, 'vClass': 'FTL', 'type': 'EXT', 'exp': {'Gdańsk': 650, 'Kielce': 740, 'Warszawa': 640, 'Berlin': 1200, 'Lipsk': 1300, 'Hannover': 1500, 'Hamburg': 1600, 'Monachium': 2100, 'Frankfurt nad Menem': 2050, 'Norymberga': 1800, 'Kolonia / Dusseldorf': 1990, 'Paryż': 2990, 'Lyon': 3300, 'Cannes / Nicea': 3600, 'Tuluza': 4100, 'Mediolan': 2950, 'Rzym': 3800, 'Barcelona': 4300, 'Madryt': 4950, 'Sewilla': 5800, 'Lizbona': 5900, 'Genewa': 4900, 'Bazylea': 3000, 'Londyn': 5200, 'Liverpool': 5500, 'Manchester': 5500, 'Amsterdam': 2300, 'Bruksela': 2500, 'Kopenhaga': 2400, 'Sztokholm': 3500, 'Wiedeń': 1900, 'Praga': 1500, 'Budapeszt': 2500, 'Sofia': 3900}, 'imp': {'Gdańsk': 650, 'Kielce': 740, 'Warszawa': 640, 'Berlin': 1200, 'Lipsk': 1300, 'Hannover': 1500, 'Hamburg': 1600, 'Monachium': 2100, 'Frankfurt nad Menem': 2050, 'Norymberga': 1800, 'Kolonia / Dusseldorf': 1990, 'Paryż': 2990, 'Lyon': 3300, 'Cannes / Nicea': 3600, 'Tuluza': 4100, 'Mediolan': 2950, 'Rzym': 3800, 'Barcelona': 4300, 'Madryt': 4950, 'Sewilla': 5800, 'Lizbona': 5900, 'Genewa': 4900, 'Bazylea': 3000, 'Londyn': 5200, 'Liverpool': 5500, 'Manchester': 5500, 'Amsterdam': 2300, 'Bruksela': 2500, 'Kopenhaga': 2400, 'Sztokholm': 3500, 'Wiedeń': 1900, 'Praga': 1500, 'Budapeszt': 2500, 'Sofia': 3900}, 'dniowki': {}}, 
        'BLM EXPRESS SOLO': {'postoj': 250.0, 'vClass': 'SOLO', 'type': 'EXT', 'exp': {'Amsterdam': 1250, 'Barcelona': 2750, 'Berlin': 450, 'Bruksela': 1400, 'Budapeszt': 1200, 'Cannes / Nicea': 2200, 'Frankfurt nad Menem': 1100, 'Gdańsk': 500, 'Hamburg': 800, 'Hannover': 750, 'Kielce': 550, 'Kolonia / Dusseldorf': 1150, 'Kopenhaga': 1300, 'Lipsk': 550, 'Liverpool': 2650, 'Lizbona': 3900, 'Londyn': 2250, 'Lyon': 2000, 'Madryt': 3350, 'Manchester': 2650, 'Mediolan': 1850, 'Monachium': 1150, 'Norymberga': 1050, 'Paryż': 1700, 'Praga': 650, 'Rzym': 2350, 'Sewilla': 3900, 'Sofia': 2750, 'Sztokholm': 2250, 'Tuluza': 2600, 'Warszawa': 600, 'Wiedeń': 850}, 'imp': {'Amsterdam': 1250, 'Barcelona': 2750, 'Berlin': 450, 'Bruksela': 1400, 'Budapeszt': 1200, 'Cannes / Nicea': 2200, 'Frankfurt nad Menem': 1100, 'Gdańsk': 500, 'Hamburg': 800, 'Hannover': 750, 'Kielce': 550, 'Kolonia / Dusseldorf': 1150, 'Kopenhaga': 1050, 'Lipsk': 550, 'Liverpool': 1850, 'Lizbona': 3900, 'Londyn': 1550, 'Lyon': 2000, 'Madryt': 3350, 'Manchester': 1850, 'Mediolan': 1850, 'Monachium': 1150, 'Norymberga': 1050, 'Paryż': 1700, 'Praga': 650, 'Rzym': 2350, 'Sewilla': 3900, 'Sofia': 2750, 'Sztokholm': 1750, 'Tuluza': 2600, 'Warszawa': 600, 'Wiedeń': 850}, 'dniowki': {}}, 
        'BLM EXPRESS FTL': {'postoj': 400.0, 'vClass': 'FTL', 'type': 'EXT', 'exp': {'Amsterdam': 1700, 'Barcelona': 3950, 'Bazylea': 2100, 'Berlin': 800, 'Bruksela': 1900, 'Budapeszt': 1750, 'Cannes / Nicea': 3150, 'Frankfurt nad Menem': 1500, 'Gdańsk': 750, 'Genewa': 2700, 'Hamburg': 1050, 'Hannover': 1050, 'Kielce': 750, 'Kolonia / Dusseldorf': 1550, 'Kopenhaga': 1550, 'Lipsk': 770, 'Liverpool': 3750, 'Lizbona': 5650, 'Londyn': 3050, 'Lyon': 2700, 'Madryt': 4850, 'Manchester': 3700, 'Mediolan': 2600, 'Monachium': 1550, 'Norymberga': 1300, 'Paryż': 2450, 'Praga': 850, 'Rzym': 3250, 'Sewilla': 5650, 'Sofia': 3170, 'Sztokholm': 2550, 'Tuluza': 3590, 'Warszawa': 750, 'Wiedeń': 1400}, 'imp': {'Amsterdam': 1700, 'Barcelona': 3500, 'Bazylea': 1850, 'Berlin': 700, 'Bruksela': 1700, 'Budapeszt': 1550, 'Cannes / Nicea': 2850, 'Frankfurt nad Menem': 1350, 'Gdańsk': 750, 'Genewa': 2400, 'Hamburg': 950, 'Hannover': 900, 'Kielce': 750, 'Kolonia / Dusseldorf': 1400, 'Kopenhaga': 1450, 'Lipsk': 690, 'Liverpool': 3400, 'Lizbona': 5050, 'Londyn': 2800, 'Lyon': 2410, 'Madryt': 4350, 'Manchester': 3400, 'Mediolan': 2350, 'Monachium': 1400, 'Norymberga': 1150, 'Paryż': 2200, 'Praga': 750, 'Rzym': 2900, 'Sewilla': 5050, 'Sofia': 2830, 'Sztokholm': 2350, 'Tuluza': 3190, 'Warszawa': 750, 'Wiedeń': 1250}, 'dniowki': {}}, 
        'RUN LOGISTICS FTL': {'postoj': 450.0, 'vClass': 'FTL', 'type': 'EXT', 'exp': {'Amsterdam': 1900, 'Barcelona': 3700, 'Bazylea': 3200, 'Berlin': 1100, 'Bruksela': 1900, 'Budapeszt': 2400, 'Cannes / Nicea': 3500, 'Frankfurt nad Menem': 1900, 'Gdańsk': 550, 'Genewa': 3400, 'Hamburg': 1400, 'Hannover': 1400, 'Kielce': 620, 'Kolonia / Dusseldorf': 1800, 'Kopenhaga': 2500, 'Lipsk': 1150, 'Liverpool': 3900, 'Lizbona': 4900, 'Londyn': 3900, 'Lyon': 3200, 'Madryt': 4200, 'Manchester': 3900, 'Mediolan': 2800, 'Monachium': 1900, 'Norymberga': 1600, 'Paryż': 3200, 'Praga': 1400, 'Rzym': 3300, 'Sewilla': 4800, 'Sofia': 3000, 'Sztokholm': 3300, 'Tuluza': 3650, 'Warszawa': 520, 'Wiedeń': 1950}, 'imp': {'Amsterdam': 1700, 'Barcelona': 3300, 'Bazylea': 3100, 'Berlin': 900, 'Bruksela': 1600, 'Budapeszt': 2100, 'Cannes / Nicea': 3000, 'Frankfurt nad Menem': 1700, 'Gdańsk': 550, 'Genewa': 3200, 'Hamburg': 1200, 'Hannover': 1000, 'Kielce': 620, 'Kolonia / Dusseldorf': 1600, 'Kopenhaga': 2200, 'Lipsk': 950, 'Liverpool': 2900, 'Lizbona': 4700, 'Londyn': 2900, 'Lyon': 2500, 'Madryt': 4000, 'Manchester': 2900, 'Mediolan': 2700, 'Monachium': 1700, 'Norymberga': 1400, 'Paryż': 2500, 'Praga': 1200, 'Rzym': 3200, 'Sewilla': 4400, 'Sofia': 2900, 'Sztokholm': 2800, 'Tuluza': 3350, 'Warszawa': 520, 'Wiedeń': 1750}, 'dniowki': {}}, 
        'VECTURA FTL': {'postoj': 350.0, 'vClass': 'FTL', 'type': 'EXT', 'exp': {'Amsterdam': 2000, 'Barcelona': 3800, 'Bazylea': 2600, 'Berlin': 900, 'Bruksela': 2100, 'Budapeszt': 2100, 'Cannes / Nicea': 3500, 'Frankfurt nad Menem': 1700, 'Gdańsk': 550, 'Genewa': 3200, 'Hamburg': 1300, 'Hannover': 1250, 'Kielce': 620, 'Kolonia / Dusseldorf': 1700, 'Kopenhaga': 2350, 'Lipsk': 1100, 'Liverpool': 4700, 'Lizbona': 5300, 'Londyn': 4400, 'Lyon': 2800, 'Madryt': 4500, 'Manchester': 4700, 'Mediolan': 2700, 'Monachium': 1750, 'Norymberga': 1500, 'Paryż': 2600, 'Praga': 1300, 'Rzym': 3300, 'Sewilla': 5100, 'Sofia': 3200, 'Sztokholm': 2800, 'Tuluza': 3600, 'Warszawa': 520, 'Wiedeń': 1600}, 'imp': {'Amsterdam': 1900, 'Barcelona': 3600, 'Bazylea': 2400, 'Berlin': 900, 'Bruksela': 2000, 'Budapeszt': 1900, 'Cannes / Nicea': 3300, 'Frankfurt nad Menem': 1600, 'Gdańsk': 550, 'Genewa': 3000, 'Hamburg': 1200, 'Hannover': 1150, 'Kielce': 620, 'Kolonia / Dusseldorf': 1600, 'Kopenhaga': 2150, 'Lipsk': 950, 'Liverpool': 4700, 'Lizbona': 5100, 'Londyn': 4400, 'Lyon': 2600, 'Madryt': 4300, 'Manchester': 4700, 'Mediolan': 2600, 'Monachium': 1650, 'Norymberga': 1400, 'Paryż': 2400, 'Praga': 1200, 'Rzym': 3100, 'Sewilla': 4900, 'Sofia': 2900, 'Sztokholm': 2600, 'Tuluza': 3400, 'Warszawa': 520, 'Wiedeń': 1500}, 'dniowki': {}}
    }

def render(sh=None):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Decision Maker</h1>
            <div class="module-subtitle">意思決定 ✦ AUTOMAGAZYN VS ZWIEZIENIE</div>
        </div>
    ''', unsafe_allow_html=True)

    rates = get_all_rates()
    carriers = list(rates.keys())
    
    # Utworzenie wspólnej, alfabetycznej listy miast ze wszystkich cenników
    cities_set = set()
    for c in rates.values():
        cities_set.update(c['exp'].keys())
    cities = sorted(list(cities_set))

    with st.container(border=True):
        st.markdown("<p style='color: #C5A880; font-weight: 700; margin-bottom: 5px; text-transform: uppercase;'>Wprowadź parametry zlecenia</p>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1.5, 2, 1.5])
        with c1:
            city = st.selectbox("📍 Miasto docelowe (Targi):", cities)
        with c2:
            carrier = st.selectbox("🚛 Przewoźnik i Pojazd:", carriers)
        with c3:
            # Intuicyjny wybór zakresu dat zamiast wpisywania liczby dni z palca
            default_start = datetime.today().date()
            default_end = default_start + timedelta(days=7)
            dates = st.date_input("📅 Czas postoju (Od - Do):", value=(default_start, default_end))
            
    # Obliczanie dni postoju (overlay) na podstawie wybranego zakresu w kalendarzu
    if isinstance(dates, tuple) and len(dates) == 2:
        start_date, end_date = dates
        overlay_days = max(0, (end_date - start_date).days)
    else:
        overlay_days = 0

    v_rates = rates[carrier]
    v_type = v_rates['vClass']
    is_sqm = v_rates['type'] == 'SQM'
    
    e = v_rates['exp'].get(city, 0)
    i = v_rates['imp'].get(city, 0)
    d = v_rates['dniowki'].get(city, 0)
    
    extra = 0
    extra_msg = ""
    
    if city in ["Londyn", "Liverpool", "Manchester"]:
        if is_sqm:
            if v_type == "BUS":
                extra = 332 + 166 + 19
                extra_msg = "Prom (332), ATA (166), Mosty (19)"
            else:
                extra = 522 + 166 + 19 + 69
                extra_msg = "Prom (522), ATA (166), Mosty (19), Drogi (69)"
        else:
            extra = 166
            extra_msg = "Karnet ATA (166)"
    elif city in ["Genewa", "Bazylea"]:
        extra = 166
        extra_msg = "Karnet ATA (166)"
        
    rt_cost = e + i + d + extra
    daily_standby = v_rates['postoj'] + 30 
    
    cost_zwiezienie = 2 * rt_cost
    cost_automagazyn = rt_cost + (overlay_days * daily_standby)
    
    break_even_days = rt_cost / daily_standby if daily_standby > 0 else 0

    st.markdown("<hr style='border-color: rgba(197, 168, 128, 0.1); margin: 25px 0;'>", unsafe_allow_html=True)
    
    winner = "AUTOMAGAZYN" if cost_automagazyn < cost_zwiezienie else "ZWIEZIENIE PUSTYCH"
    win_color = "#10B981" if winner == "AUTOMAGAZYN" else "#3B82F6"
    
    st.markdown(f'''
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="color: #A39B8F; font-size: 14px; font-weight: 700; letter-spacing: 2px;">REKOMENDOWANY MODEL LOGISTYCZNY</div>
            <div style="color: {win_color}; font-size: 48px; font-weight: 800; font-family: 'Bebas Neue', sans-serif; text-shadow: 2px 2px 0px #050A15;">{winner} JEST TAŃSZE</div>
        </div>
    ''', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    
    with col_a:
        is_win = cost_zwiezienie < cost_automagazyn
        border_col = "#3B82F6" if is_win else "rgba(197, 168, 128, 0.3)"
        st.markdown(f'''
            <div style="background-color: #F7F3EC; border: 2px solid {border_col}; padding: 25px; border-radius: 8px; box-shadow: 4px 4px 15px rgba(0,0,0,0.3);">
                <div style="color: #1A2530; font-family: 'Bebas Neue', sans-serif; font-size: 24px; letter-spacing: 1px;">OPCJA 1: ZWIEZIENIE PUSTYCH</div>
                <div style="color: #4A5568; font-size: 12px; font-weight: 600; margin-bottom: 15px; height: 35px;">(Wykonujemy 2 pełne trasy w obie strony. Zależnie od wyboru to flota własna lub podwykonawca.)</div>
                <div style="font-size: 32px; font-weight: 800; color: #990000; font-family: 'Bebas Neue', sans-serif;">€ {cost_zwiezienie:,.2f}</div>
            </div>
        ''', unsafe_allow_html=True)
        
        with st.expander("🔍 Zobacz szczegółowy składnik kosztów (Zwiezienie)"):
            st.markdown(f'''
            <ul style="color: #E2DCD3; font-size: 13px;">
                <li><b>Kurs 1 (Targi) - Wyjazd (Exp):</b> € {e:,.2f}</li>
                <li><b>Kurs 1 (Targi) - Powrót (Imp):</b> € {i:,.2f}</li>
                <li><b>Kurs 2 (Demontaż) - Wyjazd (Exp):</b> € {e:,.2f}</li>
                <li><b>Kurs 2 (Demontaż) - Powrót (Imp):</b> € {i:,.2f}</li>
                <li><b>Dniówki kierowcy (2 pełne kółka):</b> € {(d * 2):,.2f}</li>
                <li><b>Opłaty dodatkowe (2 pełne kółka):</b> € {(extra * 2):,.2f} <span style="color:#A39B8F;">{extra_msg}</span></li>
                <li style="border-top: 1px solid rgba(197, 168, 128, 0.2); margin-top: 5px; padding-top: 5px; font-weight: 800; color: #3B82F6;">Suma całkowita: € {cost_zwiezienie:,.2f}</li>
            </ul>
            ''', unsafe_allow_html=True)
        
    with col_b:
        is_win = cost_automagazyn < cost_zwiezienie
        border_col = "#10B981" if is_win else "rgba(197, 168, 128, 0.3)"
        st.markdown(f'''
            <div style="background-color: #F7F3EC; border: 2px solid {border_col}; padding: 25px; border-radius: 8px; box-shadow: 4px 4px 15px rgba(0,0,0,0.3);">
                <div style="color: #1A2530; font-family: 'Bebas Neue', sans-serif; font-size: 24px; letter-spacing: 1px;">OPCJA 2: AUTOMAGAZYN NA MIEJSCU</div>
                <div style="color: #4A5568; font-size: 12px; font-weight: 600; margin-bottom: 15px; height: 35px;">(Wysyłamy raz, auto z kierowcą stoi pod halą przez całe targi jako magazyn pustych casów.)</div>
                <div style="font-size: 32px; font-weight: 800; color: #990000; font-family: 'Bebas Neue', sans-serif;">€ {cost_automagazyn:,.2f}</div>
            </div>
        ''', unsafe_allow_html=True)

        daty_info = f"(Od {start_date.strftime('%d.%m')} do {end_date.strftime('%d.%m')})" if overlay_days > 0 else ""

        with st.expander("🔍 Zobacz szczegółowy składnik kosztów (Automagazyn)"):
            st.markdown(f'''
            <ul style="color: #E2DCD3; font-size: 13px;">
                <li><b>Kurs 1 (Targi) - Wyjazd (Exp):</b> € {e:,.2f}</li>
                <li><b>Kurs 1 (Targi) - Powrót (Imp):</b> € {i:,.2f}</li>
                <li><b>Dniówki kierowcy (1 pełne kółko):</b> € {d:,.2f}</li>
                <li><b>Opłaty dodatkowe (1 pełne kółko):</b> € {extra:,.2f} <span style="color:#A39B8F;">{extra_msg}</span></li>
                <li><b>Przestój podwykonawcy/floty ({overlay_days} dni) {daty_info}:</b> € {(v_rates['postoj'] * overlay_days):,.2f} <span style="color:#A39B8F;">(Stawka z cennika: €{v_rates['postoj']}/dzień)</span></li>
                <li><b>Koszty parkingowe pod halą ({overlay_days} dni):</b> € {(30 * overlay_days):,.2f} <span style="color:#A39B8F;">(Zryczałtowane: €30/dzień)</span></li>
                <li style="border-top: 1px solid rgba(197, 168, 128, 0.2); margin-top: 5px; padding-top: 5px; font-weight: 800; color: #10B981;">Suma całkowita: € {cost_automagazyn:,.2f}</li>
            </ul>
            ''', unsafe_allow_html=True)

    st.markdown(f'''
        <div style="margin-top: 30px; text-align: center; font-size: 14px; font-weight: 700; color: #C5A880;">
            ⚖️ Punkt opłacalności (Break-even): <span style="color: #E2DCD3;">Dla trasy do {city} ({carrier}), automagazyn opłaca się jeśli targi trwają do </span><span style="color: #BA4949; font-size: 18px;">{break_even_days:.1f} dni</span>.
        </div>
    ''', unsafe_allow_html=True)

    # Wykres
    fig = go.Figure()
    x_days = list(range(1, max(30, overlay_days + 10)))
    y_zwiezienie = [cost_zwiezienie] * len(x_days)
    y_automagazyn = [rt_cost + (x * daily_standby) for x in x_days]

    fig.add_trace(go.Scatter(x=x_days, y=y_zwiezienie, mode='lines', name='Koszt: Zwiezienie', line=dict(color='#3B82F6', width=3)))
    fig.add_trace(go.Scatter(x=x_days, y=y_automagazyn, mode='lines', name='Koszt: Automagazyn', line=dict(color='#10B981', width=3)))
    
    # Unikamy rysowania pionowej kreski w błędnym miejscu gdy overlay_days == 0
    if overlay_days > 0:
        fig.add_vline(x=overlay_days, line_width=2, line_dash="dash", line_color="#BA4949", annotation_text="TWÓJ EVENT", annotation_position="top right", annotation_font_color="#E2DCD3")
        
    fig.add_vline(x=break_even_days, line_width=1, line_dash="dot", line_color="#C5A880", annotation_text="BREAK-EVEN", annotation_position="bottom right", annotation_font_color="#C5A880")

    fig.update_layout(
        plot_bgcolor='#1C1A18', paper_bgcolor='#12100E',
        font=dict(color='#E2DCD3', family='Inter'),
        margin=dict(l=10, r=20, t=40, b=10),
        xaxis_title="Dni postoju (Overlay)",
        yaxis_title="Koszt całkowity (EUR)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        xaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.1)')
    )
    
    st.markdown('<div style="border: 1px solid rgba(197, 168, 128, 0.4); border-radius: 8px; padding: 15px; margin-top: 25px; background-color: #12100E; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)
