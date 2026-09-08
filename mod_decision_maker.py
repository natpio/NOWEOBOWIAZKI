import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def get_sqm_rates():
    """Stawki twardo przepisane z cennika PRICELIST 2026 v4.3.1"""
    return {
        'BUS': {
            'postoj': 30.0,
            'exp': {'Amsterdam': 373.8, 'Barcelona': 1106.4, 'Bazylea': 481.2, 'Berlin': 129, 'Bruksela': 415.2, 'Budapeszt': 324.6, 'Cannes / Nicea': 826.8, 'Frankfurt nad Menem': 331.8, 'Gdańsk': 162.6, 'Genewa': 648.6, 'Hamburg': 238.2, 'Hannover': 226.2, 'Kielce': 187.8, 'Kolonia / Dusseldorf': 359.4, 'Kopenhaga': 273.6, 'Lipsk': 186, 'Liverpool': 725.4, 'Lizbona': 1585.8, 'Londyn': 352.8, 'Lyon': 707.4, 'Madryt': 1382.4, 'Manchester': 717, 'Mediolan': 633.6, 'Monachium': 347.4, 'Norymberga': 285.6, 'Paryż': 577.8, 'Praga': 180.6, 'Rzym': 846.6, 'Sewilla': 988.2, 'Sofia': 704.4, 'Sztokholm': 668.4, 'Tuluza': 1000.2, 'Warszawa': 169.2, 'Wiedeń': 285.6},
            'imp': {'Amsterdam': 373.8, 'Barcelona': 1106.4, 'Bazylea': 481.2, 'Berlin': 129, 'Bruksela': 415.2, 'Budapeszt': 324.6, 'Cannes / Nicea': 826.8, 'Frankfurt nad Menem': 331.8, 'Gdańsk': 162.6, 'Genewa': 648.6, 'Hamburg': 238.2, 'Hannover': 226.2, 'Kielce': 187.8, 'Kolonia / Dusseldorf': 359.4, 'Kopenhaga': 273.6, 'Lipsk': 186, 'Liverpool': 725.4, 'Lizbona': 1585.8, 'Londyn': 352.8, 'Lyon': 707.4, 'Madryt': 1382.4, 'Manchester': 717, 'Mediolan': 633.6, 'Monachium': 347.4, 'Norymberga': 285.6, 'Paryż': 577.8, 'Praga': 180.6, 'Rzym': 846.6, 'Sewilla': 988.2, 'Sofia': 704.4, 'Sztokholm': 668.4, 'Tuluza': 1000.2, 'Warszawa': 169.2, 'Wiedeń': 285.6},
            'dniowki': {}
        },
        'SOLO': {
            'postoj': 150.0,
            'exp': {'Amsterdam': 626.4, 'Barcelona': 1638.6, 'Bazylea': 1638.6, 'Berlin': 202.2, 'Bruksela': 705.6, 'Budapeszt': 493.2, 'Cannes / Nicea': 1251.6, 'Frankfurt nad Menem': 586.2, 'Gdańsk': 252.6, 'Genewa': 1104, 'Hamburg': 410.4, 'Hannover': 388.2, 'Kielce': 286.2, 'Kolonia / Dusseldorf': 627, 'Kopenhaga': 440.4, 'Lipsk': 314.4, 'Liverpool': 1117.8, 'Lizbona': 2215.8, 'Londyn': 669.6, 'Lyon': 1131, 'Madryt': 1956, 'Manchester': 1107, 'Mediolan': 1002.6, 'Monachium': 616.2, 'Norymberga': 501.6, 'Paryż': 948.6, 'Praga': 255, 'Rzym': 1267.8, 'Sewilla': 1455, 'Sofia': 1089.6, 'Sztokholm': 532.8, 'Tuluza': 1510.2, 'Warszawa': 251.4, 'Wiedeń': 352.2},
            'imp': {'Amsterdam': 626.4, 'Barcelona': 1638.6, 'Bazylea': 1638.6, 'Berlin': 202.2, 'Bruksela': 705.6, 'Budapeszt': 493.2, 'Cannes / Nicea': 1251.6, 'Frankfurt nad Menem': 586.2, 'Gdańsk': 252.6, 'Genewa': 1104, 'Hamburg': 410.4, 'Hannover': 388.2, 'Kielce': 286.2, 'Kolonia / Dusseldorf': 627, 'Kopenhaga': 440.4, 'Lipsk': 314.4, 'Liverpool': 1117.8, 'Lizbona': 2215.8, 'Londyn': 669.6, 'Lyon': 1131, 'Madryt': 1956, 'Manchester': 1107, 'Mediolan': 1002.6, 'Monachium': 616.2, 'Norymberga': 501.6, 'Paryż': 948.6, 'Praga': 255, 'Rzym': 1267.8, 'Sewilla': 1455, 'Sofia': 1089.6, 'Sztokholm': 532.8, 'Tuluza': 1510.2, 'Warszawa': 251.4, 'Wiedeń': 352.2},
            'dniowki': {'Amsterdam': 680, 'Barcelona': 1360, 'Bazylea': 680, 'Berlin': 340, 'Bruksela': 680, 'Budapeszt': 340, 'Cannes / Nicea': 1020, 'Frankfurt nad Menem': 680, 'Gdańsk': 340, 'Genewa': 680, 'Hamburg': 340, 'Hannover': 340, 'Kielce': 340, 'Kolonia / Dusseldorf': 680, 'Kopenhaga': 680, 'Lipsk': 340, 'Liverpool': 1020, 'Lizbona': 1700, 'Londyn': 1020, 'Lyon': 1020, 'Madryt': 1360, 'Manchester': 1020, 'Mediolan': 680, 'Monachium': 680, 'Norymberga': 340, 'Paryż': 680, 'Praga': 340, 'Rzym': 1360, 'Sewilla': 1700, 'Sofia': 1020, 'Sztokholm': 1020, 'Tuluza': 1360, 'Warszawa': 340, 'Wiedeń': 680}
        },
        'FTL': {
            'postoj': 150.0,
            'exp': {'Amsterdam': 874.8, 'Barcelona': 2156.4, 'Bazylea': 1148.4, 'Berlin': 277.2, 'Bruksela': 1009.2, 'Budapeszt': 639.6, 'Cannes / Nicea': 1895.4, 'Frankfurt nad Menem': 819.6, 'Gdańsk': 310.8, 'Genewa': 1908, 'Hamburg': 571.2, 'Hannover': 540, 'Kielce': 355.8, 'Kolonia / Dusseldorf': 877.2, 'Kopenhaga': 636.6, 'Lipsk': 435.6, 'Liverpool': 1540.2, 'Lizbona': 2920.8, 'Londyn': 924, 'Lyon': 1524, 'Madryt': 2565, 'Manchester': 1524.6, 'Mediolan': 1542.6, 'Monachium': 862.2, 'Norymberga': 700.8, 'Paryż': 1292.4, 'Praga': 351, 'Rzym': 1812, 'Sewilla': 1869, 'Sofia': 1502.4, 'Sztokholm': 723, 'Tuluza': 1956.6, 'Warszawa': 313.8, 'Wiedeń': 478.2},
            'imp': {'Amsterdam': 874.8, 'Barcelona': 2156.4, 'Bazylea': 1148.4, 'Berlin': 277.2, 'Bruksela': 1009.2, 'Budapeszt': 639.6, 'Cannes / Nicea': 1895.4, 'Frankfurt nad Menem': 819.6, 'Gdańsk': 310.8, 'Genewa': 1908, 'Hamburg': 571.2, 'Hannover': 540, 'Kielce': 355.8, 'Kolonia / Dusseldorf': 877.2, 'Kopenhaga': 636.6, 'Lipsk': 435.6, 'Liverpool': 1540.2, 'Lizbona': 2920.8, 'Londyn': 924, 'Lyon': 1524, 'Madryt': 2565, 'Manchester': 1524.6, 'Mediolan': 1542.6, 'Monachium': 862.2, 'Norymberga': 700.8, 'Paryż': 1292.4, 'Praga': 351, 'Rzym': 1812, 'Sewilla': 1869, 'Sofia': 1502.4, 'Sztokholm': 723, 'Tuluza': 1956.6, 'Warszawa': 313.8, 'Wiedeń': 478.2},
            'dniowki': {'Amsterdam': 680, 'Barcelona': 1360, 'Bazylea': 680, 'Berlin': 340, 'Bruksela': 680, 'Budapeszt': 340, 'Cannes / Nicea': 1020, 'Frankfurt nad Menem': 680, 'Gdańsk': 340, 'Genewa': 680, 'Hamburg': 340, 'Hannover': 340, 'Kielce': 340, 'Kolonia / Dusseldorf': 680, 'Kopenhaga': 680, 'Lipsk': 340, 'Liverpool': 1020, 'Lizbona': 1700, 'Londyn': 1020, 'Lyon': 1020, 'Madryt': 1360, 'Manchester': 1020, 'Mediolan': 680, 'Monachium': 680, 'Norymberga': 340, 'Paryż': 680, 'Praga': 340, 'Rzym': 1360, 'Sewilla': 1700, 'Sofia': 1020, 'Sztokholm': 1020, 'Tuluza': 1360, 'Warszawa': 340, 'Wiedeń': 680}
        }
    }

def render(sh=None):
    st.markdown('''
        <div class="module-header-container">
            <h1 class="module-title">Decision Maker</h1>
            <div class="module-subtitle">意思決定 ✦ AUTOMAGAZYN VS ZWIEZIENIE</div>
        </div>
    ''', unsafe_allow_html=True)

    rates = get_sqm_rates()
    cities = sorted(list(rates['BUS']['exp'].keys()))

    with st.container(border=True):
        st.markdown("<p style='color: #C5A880; font-weight: 700; margin-bottom: 5px; text-transform: uppercase;'>Wprowadź parametry zlecenia</p>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            city = st.selectbox("📍 Miasto docelowe (Targi):", cities)
        with c2:
            v_type = st.selectbox("🚛 Typ pojazdu floty SQM:", ["BUS", "SOLO", "FTL"])
        with c3:
            overlay_days = st.number_input("⏳ Dni postoju (między wypakowaniem a pakowaniem):", min_value=1, max_value=60, value=7, step=1)

    v_rates = rates[v_type]
    
    e = v_rates['exp'].get(city, 0)
    i = v_rates['imp'].get(city, 0)
    d = v_rates['dniowki'].get(city, 0)
    
    extra = 0
    if city in ["Londyn", "Liverpool", "Manchester"]:
        extra = (332 + 166 + 19) if v_type == "BUS" else (522 + 166 + 19 + 69)
    elif city in ["Genewa", "Bazylea"]:
        extra = 166
        
    rt_cost = e + i + d + extra
    daily_standby = v_rates['postoj'] + 30 
    
    cost_zwiezienie = 2 * rt_cost
    cost_automagazyn = rt_cost + (overlay_days * daily_standby)
    
    break_even_days = rt_cost / daily_standby if daily_standby > 0 else 0

    st.markdown("<hr style='border-color: rgba(197, 168, 128, 0.1); margin: 25px 0;'>", unsafe_allow_html=True)
    
    winner = "AUTOMAGAZYN" if cost_automagazyn < cost_zwiezienie else "ZWIEZIENIE PUSTYCH"
    win_color = "#10B981" if winner == "AUTOMAGAZYN" else "#3B82F6"
    
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="color: #A39B8F; font-size: 14px; font-weight: 700; letter-spacing: 2px;">REKOMENDOWANY MODEL LOGISTYCZNY</div>
            <div style="color: {win_color}; font-size: 48px; font-weight: 800; font-family: 'Bebas Neue', sans-serif; text-shadow: 2px 2px 0px #050A15;">{winner} JEST TAŃSZE</div>
        </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    
    with col_a:
        is_win = cost_zwiezienie < cost_automagazyn
        border_col = "#3B82F6" if is_win else "rgba(197, 168, 128, 0.3)"
        st.markdown(f"""
            <div style="background-color: #F7F3EC; border: 2px solid {border_col}; padding: 25px; border-radius: 8px; box-shadow: 4px 4px 15px rgba(0,0,0,0.3);">
                <div style="color: #1A2530; font-family: 'Bebas Neue', sans-serif; font-size: 24px; letter-spacing: 1px;">OPCJA 1: ZWIEZIENIE PUSTYCH</div>
                <div style="color: #4A5568; font-size: 12px; font-weight: 600; margin-bottom: 15px; height: 35px;">(Wykonujemy 2 pełne trasy w obie strony. Auto wraca i zarabia w Polsce.)</div>
                <div style="font-size: 32px; font-weight: 800; color: #990000; font-family: 'Bebas Neue', sans-serif;">€ {cost_zwiezienie:,.2f}</div>
                <div style="margin-top: 10px; font-size: 11px; color: #718096; font-weight: 600;">Koszt pojedynczej trasy: € {rt_cost:,.2f}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col_b:
        is_win = cost_automagazyn < cost_zwiezienie
        border_col = "#10B981" if is_win else "rgba(197, 168, 128, 0.3)"
        st.markdown(f"""
            <div style="background-color: #F7F3EC; border: 2px solid {border_col}; padding: 25px; border-radius: 8px; box-shadow: 4px 4px 15px rgba(0,0,0,0.3);">
                <div style="color: #1A2530; font-family: 'Bebas Neue', sans-serif; font-size: 24px; letter-spacing: 1px;">OPCJA 2: AUTOMAGAZYN NA MIEJSCU</div>
                <div style="color: #4A5568; font-size: 12px; font-weight: 600; margin-bottom: 15px; height: 35px;">(Wysyłamy raz, auto stoi pod halą przez całe targi jako magazyn pustych casów.)</div>
                <div style="font-size: 32px; font-weight: 800; color: #990000; font-family: 'Bebas Neue', sans-serif;">€ {cost_automagazyn:,.2f}</div>
                <div style="margin-top: 10px; font-size: 11px; color: #718096; font-weight: 600;">Koszt postoju (Dniówka + Parking): € {daily_standby:,.2f} / dzień</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
        <div style="margin-top: 30px; text-align: center; font-size: 14px; font-weight: 700; color: #C5A880;">
            ⚖️ Punkt opłacalności (Break-even): <span style="color: #E2DCD3;">Dla trasy do {city} ({v_type}), automagazyn opłaca się jeśli targi trwają do </span><span style="color: #BA4949; font-size: 18px;">{break_even_days:.1f} dni</span>.
        </div>
    """, unsafe_allow_html=True)

    # Wykres
    fig = go.Figure()
    x_days = list(range(1, max(30, overlay_days + 10)))
    y_zwiezienie = [cost_zwiezienie] * len(x_days)
    y_automagazyn = [rt_cost + (x * daily_standby) for x in x_days]

    fig.add_trace(go.Scatter(x=x_days, y=y_zwiezienie, mode='lines', name='Koszt: Zwiezienie', line=dict(color='#3B82F6', width=3)))
    fig.add_trace(go.Scatter(x=x_days, y=y_automagazyn, mode='lines', name='Koszt: Automagazyn', line=dict(color='#10B981', width=3)))
    
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
