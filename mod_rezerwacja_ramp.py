import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time as dt_time
import time
import os
import base64
from streamlit_calendar import calendar
import db


# ============================================================
# SQM TRANSPORT HUB — REZERWACJA RAMPY 2.0
# ============================================================

RAMPY = ["11", "12", "13", "14", "15"]

COLORS = {
    "navy": "#07111F",
    "navy_2": "#0B1728",
    "panel": "#0E1B2D",
    "panel_2": "#111F33",
    "gold": "#C5A880",
    "gold_soft": "rgba(197,168,128,.22)",
    "white": "#F7F4EE",
    "text": "#D8D2C8",
    "muted": "#8E8A82",
    "green": "#19B878",
    "blue": "#3B82F6",
    "red": "#C65A5A",
    "gray": "#718096",
}


def get_b64(filepath):
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def safe_str(value, default=""):
    if value is None:
        return default
    value = str(value).strip()
    if value.lower() in ("nan", "none"):
        return default
    return value


def parse_date(value, fallback=None):
    fallback = fallback or date.today()
    value = safe_str(value)
    if not value:
        return fallback
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except Exception:
        return fallback


def parse_time(value, fallback=None):
    fallback = fallback or dt_time(8, 0)
    value = safe_str(value)
    if not value:
        return fallback
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except Exception:
            pass
    return fallback


def normalize_bool(value):
    return safe_str(value).upper() == "TAK"


def format_podjazd(value, reservation_date):
    value = safe_str(value)
    if not value:
        return "–"
    try:
        if " " in value:
            d, t = value.split(" ", 1)
            if d == str(reservation_date):
                return t[:5]
            return f"{d[8:10]}.{d[5:7]} {t[:5]}"
        return value[:5]
    except Exception:
        return value


def reservation_status(row):
    """
    Kolejność statusów:
    1. zakończono
    2. trwa załadunek
    3. podjazd zarejestrowany
    4. zaplanowano / oczekuje
    """
    if normalize_bool(row.get("Zakonczono", "")):
        return "done"
    if normalize_bool(row.get("Trwa_Zaladunek", "")):
        return "loading"
    if safe_str(row.get("Faktyczny_Podjazd", "")):
        return "arrived"
    return "planned"


def status_meta(status):
    return {
        "planned": {
            "label": "OCZEKUJE",
            "color": COLORS["gold"],
            "icon": "◷",
        },
        "arrived": {
            "label": "POD RAMPĄ",
            "color": COLORS["green"],
            "icon": "●",
        },
        "loading": {
            "label": "ZAŁADUNEK",
            "color": COLORS["blue"],
            "icon": "◆",
        },
        "done": {
            "label": "ZAKOŃCZONE",
            "color": COLORS["gray"],
            "icon": "✓",
        },
    }[status]


def has_conflict(df, reservation_id, ramp, selected_date, start_time, end_time):
    """Sprawdza nakładanie rezerwacji na tej samej rampie."""
    if df is None or df.empty:
        return False, None

    try:
        target_start = datetime.combine(selected_date, start_time)
        target_end = datetime.combine(selected_date, end_time)
        if target_end <= target_start:
            return True, "Godzina Do musi być późniejsza niż Godzina Od."

        for _, r in df.iterrows():
            if safe_str(r.get("ID_Rezerwacji")) == safe_str(reservation_id):
                continue
            if safe_str(r.get("Rampa")) != safe_str(ramp):
                continue
            if parse_date(r.get("Data")) != selected_date:
                continue

            other_start = datetime.combine(
                selected_date, parse_time(r.get("Godzina_Od"), dt_time(0, 0))
            )
            other_end = datetime.combine(
                selected_date, parse_time(r.get("Godzina_Do"), dt_time(0, 0))
            )

            if target_start < other_end and target_end > other_start:
                event_name = safe_str(r.get("Nazwa_Imprezy"), "Inna rezerwacja")
                event_time = (
                    f"{safe_str(r.get('Godzina_Od'), '?')}–"
                    f"{safe_str(r.get('Godzina_Do'), '?')}"
                )
                return True, f"{event_name} ({event_time})"
    except Exception:
        return False, None

    return False, None


def inject_css():
    st.markdown(
        f"""
        <style>
        /* =====================================================
           GLOBAL
           ===================================================== */
        :root {{
            --sqm-navy: {COLORS["navy"]};
            --sqm-navy2: {COLORS["navy_2"]};
            --sqm-panel: {COLORS["panel"]};
            --sqm-panel2: {COLORS["panel_2"]};
            --sqm-gold: {COLORS["gold"]};
            --sqm-white: {COLORS["white"]};
            --sqm-text: {COLORS["text"]};
            --sqm-muted: {COLORS["muted"]};
        }}

        .stApp {{
            background:
                radial-gradient(circle at 75% 5%, rgba(197,168,128,.07), transparent 25%),
                radial-gradient(circle at 5% 85%, rgba(59,130,246,.05), transparent 25%),
                #050C16 !important;
        }}

        [data-testid="stHeader"] {{
            background: transparent !important;
        }}

        [data-testid="stMainBlockContainer"] {{
            max-width: 1700px !important;
            padding-top: 1.2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }}

        /* =====================================================
           TYPOGRAPHY
           ===================================================== */
        h1, h2, h3 {{
            font-family: 'Bebas Neue', 'Arial Narrow', sans-serif !important;
        }}

        /* =====================================================
           BUTTONS / INPUTS
           ===================================================== */
        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-testid="stTimeInput"] input {{
            background: #0A1422 !important;
            color: var(--sqm-white) !important;
            border: 1px solid rgba(197,168,128,.20) !important;
            border-radius: 7px !important;
        }}

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stTextArea"] textarea:focus {{
            border-color: rgba(197,168,128,.65) !important;
            box-shadow: 0 0 0 1px rgba(197,168,128,.15) !important;
        }}

        .stButton > button {{
            border-radius: 7px !important;
            min-height: 40px !important;
            font-weight: 700 !important;
            letter-spacing: .4px !important;
        }}

        .sqm-primary button {{
            background: linear-gradient(135deg, #C5A880, #9E835A) !important;
            color: #0A1018 !important;
            border: 0 !important;
        }}

        /* =====================================================
           HEADER
           ===================================================== */
        .sqm-header {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin: 2px 0 20px;
        }}

        .sqm-header-icon {{
            width: 52px;
            height: 52px;
            display: grid;
            place-items: center;
            border-radius: 12px;
            background: linear-gradient(145deg, #14263D, #09121F);
            border: 1px solid rgba(197,168,128,.30);
            box-shadow: 0 10px 30px rgba(0,0,0,.35);
            font-size: 25px;
        }}

        .sqm-header-title {{
            margin: 0;
            color: var(--sqm-white);
            font-size: 37px;
            line-height: 1;
            letter-spacing: 2.2px;
            font-weight: 800;
        }}

        .sqm-header-sub {{
            color: var(--sqm-muted);
            font-size: 12px;
            margin-top: 7px;
        }}

        /* =====================================================
           DATE BAR
           ===================================================== */
        .sqm-date-label {{
            color: var(--sqm-muted);
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin: 0 0 5px 2px;
        }}

        .sqm-search-label {{
            color: var(--sqm-muted);
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin: 0 0 5px 2px;
        }}

        /* =====================================================
           KPI
           ===================================================== */
        .sqm-kpis {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 10px 0 16px;
        }}

        .sqm-kpi {{
            position: relative;
            overflow: hidden;
            min-height: 92px;
            padding: 16px 18px;
            border-radius: 10px;
            background: linear-gradient(145deg, rgba(15,28,45,.96), rgba(7,15,26,.96));
            border: 1px solid rgba(197,168,128,.13);
            box-shadow: 0 8px 25px rgba(0,0,0,.22);
        }}

        .sqm-kpi::after {{
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 3px;
            background: var(--kpi-color);
        }}

        .sqm-kpi-label {{
            color: var(--sqm-muted);
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.2px;
        }}

        .sqm-kpi-value {{
            color: var(--sqm-white);
            font-size: 31px;
            font-weight: 800;
            line-height: 1;
            margin-top: 8px;
            font-family: 'Bebas Neue', 'Arial Narrow', sans-serif;
        }}

        .sqm-kpi-icon {{
            position: absolute;
            right: 16px;
            bottom: 11px;
            font-size: 24px;
            opacity: .28;
        }}

        /* =====================================================
           CALENDAR WRAPPER
           ===================================================== */
        .sqm-calendar-shell {{
            background: linear-gradient(145deg, rgba(10,22,37,.98), rgba(5,12,21,.98));
            border: 1px solid rgba(197,168,128,.16);
            border-radius: 12px;
            padding: 8px;
            box-shadow: 0 16px 45px rgba(0,0,0,.32);
            overflow: hidden;
        }}

        .fc {{
            background: transparent !important;
            color: #D8D2C8 !important;
            font-family: Inter, Arial, sans-serif !important;
        }}

        .fc-scrollgrid {{
            border-color: rgba(197,168,128,.12) !important;
        }}

        .fc-col-header-cell {{
            background: #0B1728 !important;
            border-color: rgba(197,168,128,.12) !important;
            padding: 0 !important;
        }}

        .fc-col-header-cell-cushion {{
            display: block !important;
            padding: 12px 4px !important;
            color: #E8E2D9 !important;
            font-family: 'Bebas Neue', Arial Narrow, sans-serif !important;
            font-size: 17px !important;
            letter-spacing: 1.3px !important;
            text-decoration: none !important;
        }}

        .fc-timegrid-slot {{
            height: 42px !important;
            border-color: rgba(197,168,128,.065) !important;
        }}

        .fc-timegrid-slot-label {{
            color: #9E947F !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            border-color: rgba(197,168,128,.09) !important;
            padding-right: 7px !important;
        }}

        .fc-timegrid-col {{
            background: rgba(8,17,29,.55) !important;
            border-color: rgba(197,168,128,.10) !important;
        }}

        .fc-timegrid-col.fc-day-today {{
            background: rgba(197,168,128,.025) !important;
        }}

        .fc-timegrid-now-indicator-line {{
            border-color: #C65A5A !important;
            border-width: 2px !important;
        }}

        .fc-timegrid-now-indicator-arrow {{
            border-top-color: #C65A5A !important;
            border-bottom-color: #C65A5A !important;
        }}

        /* EVENT — nie wymuszamy białego tła */
        .fc-event {{
            border-radius: 7px !important;
            border-width: 0 0 0 4px !important;
            border-style: solid !important;
            padding: 4px 6px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,.30) !important;
            cursor: grab !important;
            overflow: hidden !important;
        }}

        .fc-event:active {{
            cursor: grabbing !important;
        }}

        .fc-event-main {{
            padding: 0 !important;
        }}

        .fc-event-title {{
            white-space: pre-wrap !important;
            font-size: 11px !important;
            line-height: 1.25 !important;
            font-weight: 700 !important;
            color: #F7F4EE !important;
        }}

        .fc-event-time {{
            color: #D5CCBD !important;
            font-size: 10px !important;
            font-weight: 800 !important;
        }}

        /* resource labels */
        .fc-resource-timeline-divider {{
            background: rgba(197,168,128,.15) !important;
        }}

        /* =====================================================
           LEGEND
           ===================================================== */
        .sqm-legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px 18px;
            margin: 10px 2px 22px;
            color: #99948B;
            font-size: 11px;
            font-weight: 700;
        }}

        .sqm-legend-item {{
            display: flex;
            align-items: center;
            gap: 7px;
        }}

        .sqm-dot {{
            width: 9px;
            height: 9px;
            border-radius: 50%;
            display: inline-block;
        }}

        /* =====================================================
           DETAIL PANEL
           ===================================================== */
        .sqm-detail {{
            position: relative;
            overflow: hidden;
            border-radius: 12px;
            padding: 23px;
            background:
                radial-gradient(circle at 90% 20%, rgba(197,168,128,.08), transparent 28%),
                linear-gradient(145deg, #101F33, #07111F);
            border: 1px solid rgba(197,168,128,.30);
            box-shadow: 0 18px 50px rgba(0,0,0,.35);
            margin-top: 4px;
        }}

        .sqm-detail-bg {{
            position: absolute;
            right: -45px;
            bottom: -45px;
            width: 360px;
            opacity: .08;
            pointer-events: none;
        }}

        .sqm-detail-content {{
            position: relative;
            z-index: 2;
        }}

        .sqm-detail-kicker {{
            color: var(--sqm-gold);
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }}

        .sqm-detail-title {{
            color: var(--sqm-white);
            font-family: 'Bebas Neue', Arial Narrow, sans-serif;
            font-size: 30px;
            letter-spacing: 1.2px;
            margin-top: 5px;
        }}

        .sqm-detail-ramp {{
            display: inline-block;
            color: #E5D5BB;
            font-size: 13px;
            font-weight: 900;
            letter-spacing: 1px;
            padding: 5px 9px;
            border-radius: 5px;
            background: rgba(197,168,128,.10);
            border: 1px solid rgba(197,168,128,.20);
            margin: 6px 0 17px;
        }}

        .sqm-time-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 4px 0 20px;
        }}

        .sqm-time-card {{
            padding: 13px 15px;
            border-radius: 8px;
            background: rgba(0,0,0,.20);
            border: 1px solid rgba(197,168,128,.10);
        }}

        .sqm-time-label {{
            color: var(--sqm-muted);
            font-size: 9px;
            font-weight: 900;
            letter-spacing: 1.2px;
        }}

        .sqm-time-value {{
            color: var(--sqm-white);
            font-size: 15px;
            font-weight: 800;
            margin-top: 6px;
        }}

        .sqm-info-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0,1fr));
            gap: 8px;
        }}

        .sqm-info {{
            padding: 10px 12px;
            border-left: 2px solid rgba(197,168,128,.35);
            background: rgba(0,0,0,.12);
            min-width: 0;
        }}

        .sqm-info-label {{
            color: var(--sqm-muted);
            font-size: 8px;
            font-weight: 900;
            letter-spacing: 1px;
        }}

        .sqm-info-value {{
            color: var(--sqm-white);
            font-size: 12px;
            font-weight: 700;
            margin-top: 4px;
            overflow-wrap: anywhere;
        }}

        /* =====================================================
           FORM
           ===================================================== */
        .sqm-form-title {{
            color: var(--sqm-gold);
            font-family: 'Bebas Neue', Arial Narrow, sans-serif;
            font-size: 24px;
            letter-spacing: 1px;
            margin: 5px 0 15px;
        }}

        .sqm-form-status {{
            padding: 14px;
            border-radius: 8px;
            background: rgba(10,20,40,.65);
            border: 1px solid rgba(197,168,128,.15);
            margin-bottom: 10px;
        }}

        /* =====================================================
           MOBILE
           ===================================================== */
        @media (max-width: 1100px) {{
            [data-testid="stMainBlockContainer"] {{
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }}

            .sqm-kpis {{
                grid-template-columns: repeat(2, minmax(0,1fr));
            }}

            .sqm-info-grid {{
                grid-template-columns: repeat(2, minmax(0,1fr));
            }}
        }}

        @media (max-width: 700px) {{
            [data-testid="stMainBlockContainer"] {{
                padding-left: .55rem !important;
                padding-right: .55rem !important;
                padding-top: .6rem !important;
            }}

            .sqm-header {{
                margin-bottom: 12px;
            }}

            .sqm-header-icon {{
                width: 42px;
                height: 42px;
                font-size: 20px;
            }}

            .sqm-header-title {{
                font-size: 27px;
            }}

            .sqm-header-sub {{
                font-size: 10px;
            }}

            .sqm-kpis {{
                grid-template-columns: repeat(2, minmax(0,1fr));
                gap: 7px;
            }}

            .sqm-kpi {{
                min-height: 76px;
                padding: 11px;
            }}

            .sqm-kpi-value {{
                font-size: 25px;
            }}

            .sqm-kpi-icon {{
                display: none;
            }}

            .sqm-calendar-shell {{
                padding: 2px;
                border-radius: 8px;
            }}

            .fc-col-header-cell-cushion {{
                font-size: 13px !important;
                padding: 9px 1px !important;
                letter-spacing: .5px !important;
            }}

            .fc-timegrid-slot {{
                height: 38px !important;
            }}

            .fc-timegrid-slot-label {{
                font-size: 9px !important;
            }}

            .fc-event-title {{
                font-size: 9px !important;
            }}

            .sqm-detail {{
                padding: 15px;
            }}

            .sqm-detail-title {{
                font-size: 25px;
            }}

            .sqm-time-grid {{
                grid-template-columns: 1fr;
            }}

            .sqm-info-grid {{
                grid-template-columns: 1fr 1fr;
            }}

            .sqm-legend {{
                gap: 7px 12px;
                font-size: 9px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_events(df_dzien):
    events = []

    if df_dzien is None or df_dzien.empty:
        return events

    for _, row in df_dzien.iterrows():
        status = reservation_status(row)
        meta = status_meta(status)

        impreza = safe_str(row.get("Nazwa_Imprezy"), "BEZ NAZWY")
        pojazd = safe_str(row.get("Pojazd"), "POJAZD –")
        kierowca = safe_str(row.get("Kierowca"), "KIEROWCA –")
        ramp = safe_str(row.get("Rampa"), "")

        podjazd = format_podjazd(
            row.get("Faktyczny_Podjazd"),
            safe_str(row.get("Data"), ""),
        )

        status_line = (
            f"{meta['icon']} {meta['label']}"
            + (f"  •  {podjazd}" if podjazd != "–" else "")
        )

        title = f"{impreza.upper()}\n{pojazd}\n{kierowca}\n{status_line}"

        events.append(
            {
                "id": safe_str(row.get("ID_Rezerwacji")),
                "resourceId": ramp,
                "start": (
                    f"{safe_str(row.get('Data'))}T"
                    f"{safe_str(row.get('Godzina_Od'), '08:00')}:00"
                ),
                "end": (
                    f"{safe_str(row.get('Data'))}T"
                    f"{safe_str(row.get('Godzina_Do'), '09:00')}:00"
                ),
                "title": title,
                "backgroundColor": (
                    "rgba(25,184,120,.18)"
                    if status == "arrived"
                    else "rgba(59,130,246,.20)"
                    if status == "loading"
                    else "rgba(113,128,150,.18)"
                    if status == "done"
                    else "rgba(197,168,128,.16)"
                ),
                "borderColor": meta["color"],
                "textColor": COLORS["white"],
            }
        )

    return events


def render_header():
    st.markdown(
        """
        <div class="sqm-header">
            <div class="sqm-header-icon">◫</div>
            <div>
                <div class="sqm-header-title">REZERWACJA RAMPY</div>
                <div class="sqm-header-sub">
                    PLANOWANIE • PODJAZDY • ZAŁADUNEK • ZWOLNIENIE RAMPY
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(df_dzien):
    planned = arrived = loading = done = 0

    if df_dzien is not None and not df_dzien.empty:
        for _, row in df_dzien.iterrows():
            status = reservation_status(row)
            if status == "planned":
                planned += 1
            elif status == "arrived":
                arrived += 1
            elif status == "loading":
                loading += 1
            elif status == "done":
                done += 1

    st.markdown(
        f"""
        <div class="sqm-kpis">
            <div class="sqm-kpi" style="--kpi-color:{COLORS["gold"]};">
                <div class="sqm-kpi-label">OCZEKUJE NA PODJAZD</div>
                <div class="sqm-kpi-value">{planned}</div>
                <div class="sqm-kpi-icon">◷</div>
            </div>
            <div class="sqm-kpi" style="--kpi-color:{COLORS["green"]};">
                <div class="sqm-kpi-label">POD RAMPĄ</div>
                <div class="sqm-kpi-value">{arrived}</div>
                <div class="sqm-kpi-icon">●</div>
            </div>
            <div class="sqm-kpi" style="--kpi-color:{COLORS["blue"]};">
                <div class="sqm-kpi-label">W TRAKCIE OPERACJI</div>
                <div class="sqm-kpi-value">{loading}</div>
                <div class="sqm-kpi-icon">◆</div>
            </div>
            <div class="sqm-kpi" style="--kpi-color:{COLORS["gray"]};">
                <div class="sqm-kpi-label">ZAKOŃCZONE DZISIAJ</div>
                <div class="sqm-kpi-value">{done}</div>
                <div class="sqm-kpi-icon">✓</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_detail_panel(df_rampy, b64_ftl):
    rez_id = st.session_state.get("wybrana_rezerwacja")
    if not rez_id:
        return

    if st.session_state.get("pokaz_formularz") == "NOWA":
        return

    matches = df_rampy[df_rampy["ID_Rezerwacji"].astype(str) == str(rez_id)]
    if matches.empty:
        st.session_state.wybrana_rezerwacja = None
        return

    row = matches.iloc[0]
    status = reservation_status(row)
    meta = status_meta(status)

    reservation_date = safe_str(row.get("Data"), "-")
    podjazd = safe_str(row.get("Faktyczny_Podjazd"))

    if podjazd:
        if " " in podjazd:
            pdate, ptime = podjazd.split(" ", 1)
            podjazd_display = f"{pdate} • {ptime[:5]}"
        else:
            podjazd_display = podjazd[:5]
    else:
        podjazd_display = "Brak zarejestrowanego podjazdu"

    vehicle = safe_str(row.get("Pojazd"), "–")
    if "/" in vehicle:
        vehicle = vehicle.split("/")[0].strip()

    st.markdown(
        f"""
        <div class="sqm-detail">
            {"<img class='sqm-detail-bg' src='data:image/png;base64," + b64_ftl + "'>" if b64_ftl else ""}
            <div class="sqm-detail-content">
                <div class="sqm-detail-kicker">
                    {meta["icon"]} {meta["label"]}
                </div>
                <div class="sqm-detail-title">
                    {safe_str(row.get("Nazwa_Imprezy"), "REZERWACJA")}
                </div>
                <div class="sqm-detail-ramp">
                    RAMPA {safe_str(row.get("Rampa"), "–")}
                </div>

                <div class="sqm-time-grid">
                    <div class="sqm-time-card">
                        <div class="sqm-time-label">PLANOWANA REZERWACJA</div>
                        <div class="sqm-time-value">
                            {reservation_date}
                            &nbsp; • &nbsp;
                            {safe_str(row.get("Godzina_Od"), "–")}
                            – {safe_str(row.get("Godzina_Do"), "–")}
                        </div>
                    </div>
                    <div class="sqm-time-card">
                        <div class="sqm-time-label">FAKTYCZNY PODJAZD</div>
                        <div class="sqm-time-value">{podjazd_display}</div>
                    </div>
                </div>

                <div class="sqm-info-grid">
                    <div class="sqm-info">
                        <div class="sqm-info-label">REJESTRACJA</div>
                        <div class="sqm-info-value">{vehicle}</div>
                    </div>
                    <div class="sqm-info">
                        <div class="sqm-info-label">NACZEPA</div>
                        <div class="sqm-info-value">{safe_str(row.get("Naczepa"), "–")}</div>
                    </div>
                    <div class="sqm-info">
                        <div class="sqm-info-label">KIEROWCA</div>
                        <div class="sqm-info-value">{safe_str(row.get("Kierowca"), "–")}</div>
                    </div>
                    <div class="sqm-info">
                        <div class="sqm-info-label">TELEFON</div>
                        <div class="sqm-info-value">{safe_str(row.get("Telefon"), "–")}</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    is_loading = normalize_bool(row.get("Trwa_Zaladunek"))
    is_done = normalize_bool(row.get("Zakonczono"))

    b1, b2, b3, b4 = st.columns([2.2, 2.2, 1.1, 1.0])

    with b1:
        if not is_done:
            if not is_loading:
                if st.button(
                    "▶ ROZPOCZNIJ OPERACJĘ",
                    use_container_width=True,
                    key=f"start_{rez_id}",
                ):
                    idx = df_rampy[df_rampy["ID_Rezerwacji"] == rez_id].index[0]
                    df_rampy.at[idx, "Trwa_Zaladunek"] = "TAK"

                    if not safe_str(df_rampy.at[idx, "Faktyczny_Podjazd"]):
                        df_rampy.at[idx, "Faktyczny_Podjazd"] = datetime.now().strftime(
                            "%Y-%m-%d %H:%M"
                        )

                    db.update_single_row_safe(
                        "DB_Rampy",
                        int(df_rampy.at[idx, "sheet_row"]),
                        df_rampy.loc[idx],
                    )
                    st.success("Operacja rozpoczęta.")
                    st.rerun()
            else:
                st.button(
                    "◆ OPERACJA W TOKU",
                    disabled=True,
                    use_container_width=True,
                    key=f"loading_{rez_id}",
                )

    with b2:
        if is_loading and not is_done:
            if st.button(
                "✓ ZWOLNIJ RAMPĘ",
                type="primary",
                use_container_width=True,
                key=f"finish_{rez_id}",
            ):
                now = datetime.now()
                podjazd_db = safe_str(row.get("Faktyczny_Podjazd"))
                start_dt = now

                try:
                    if podjazd_db and " " in podjazd_db:
                        start_dt = datetime.strptime(
                            podjazd_db, "%Y-%m-%d %H:%M"
                        )
                    elif podjazd_db:
                        start_dt = datetime.combine(
                            parse_date(row.get("Data")), parse_time(podjazd_db)
                        )
                except Exception:
                    start_dt = now

                # Operacje liczymy od 07:00, jeśli pojazd był wcześniej.
                today = now.date()
                if start_dt.date() < today or (
                    start_dt.date() == today and start_dt.time() < dt_time(7, 0)
                ):
                    start_dt = datetime.combine(today, dt_time(7, 0))

                minutes = max(0, int((now - start_dt).total_seconds() / 60))
                hours, mins = divmod(minutes, 60)
                duration = f"{hours}h {mins}m"

                idx = df_rampy[df_rampy["ID_Rezerwacji"] == rez_id].index[0]
                df_rampy.at[idx, "Trwa_Zaladunek"] = "NIE"
                df_rampy.at[idx, "Zakonczono"] = "TAK"

                notes = safe_str(df_rampy.at[idx, "Notatki"])
                prefix = f"[Czas operacji: {duration}]"
                df_rampy.at[idx, "Notatki"] = (
                    f"{prefix} {notes}".strip()
                )

                db.update_single_row_safe(
                    "DB_Rampy",
                    int(df_rampy.at[idx, "sheet_row"]),
                    df_rampy.loc[idx],
                )

                st.session_state.wybrana_rezerwacja = None
                st.success(f"Rampa zwolniona. Czas operacji: {duration}")
                st.rerun()

    with b3:
        if st.button("✎ EDYTUJ", use_container_width=True, key=f"edit_{rez_id}"):
            st.session_state.pokaz_formularz = "EDYCJA"
            st.rerun()

    with b4:
        if st.button("× ZAMKNIJ", use_container_width=True, key=f"close_{rez_id}"):
            st.session_state.wybrana_rezerwacja = None
            st.rerun()


def render_form(df_rampy):
    mode = st.session_state.get("pokaz_formularz")
    if mode not in ("NOWA", "EDYCJA"):
        return

    st.markdown("<hr style='border-color:rgba(197,168,128,.12);'>", unsafe_allow_html=True)

    title = "＋ NOWA REZERWACJA" if mode == "NOWA" else "✎ EDYCJA REZERWACJI"
    st.markdown(f"<div class='sqm-form-title'>{title}</div>", unsafe_allow_html=True)

    dane = {}

    if mode == "EDYCJA" and st.session_state.get("wybrana_rezerwacja"):
        matches = df_rampy[
            df_rampy["ID_Rezerwacji"].astype(str)
            == str(st.session_state.wybrana_rezerwacja)
        ]
        if not matches.empty:
            dane = matches.iloc[0].to_dict()

    with st.form("form_rampy_v2", clear_on_submit=False):
        c1, c2, c3 = st.columns([1, 1, 1])

        with c1:
            f_impreza = st.text_input(
                "Nazwa imprezy *",
                value=safe_str(dane.get("Nazwa_Imprezy")),
            )

            current_ramp = safe_str(dane.get("Rampa"), "11")
            f_rampa = st.selectbox(
                "Rampa",
                RAMPY,
                index=RAMPY.index(current_ramp) if current_ramp in RAMPY else 0,
            )

            f_data = st.date_input(
                "Data rezerwacji",
                value=parse_date(
                    dane.get("Data"), st.session_state.get("rampy_data", date.today())
                ),
            )

            f_od = st.time_input(
                "Godzina od",
                value=parse_time(dane.get("Godzina_Od"), dt_time(8, 0)),
            )

            f_do = st.time_input(
                "Godzina do",
                value=parse_time(dane.get("Godzina_Do"), dt_time(10, 0)),
            )

        with c2:
            f_pojazd = st.text_input(
                "Pojazd / rejestracja",
                value=safe_str(dane.get("Pojazd")),
            )
            f_naczepa = st.text_input(
                "Rejestracja naczepy",
                value=safe_str(dane.get("Naczepa")),
            )
            f_typ_naczepy = st.text_input(
                "Typ naczepy",
                value=safe_str(dane.get("Typ_Naczepy")),
            )
            f_kierowca = st.text_input(
                "Kierowca",
                value=safe_str(dane.get("Kierowca")),
            )
            f_tel = st.text_input(
                "Telefon kierowcy",
                value=safe_str(dane.get("Telefon")),
            )
            f_email = st.text_input(
                "E-mail",
                value=safe_str(dane.get("Email")),
            )

        with c3:
            st.markdown(
                "<div class='sqm-form-status'><b style='color:#C5A880'>STATUS OPERACJI</b>",
                unsafe_allow_html=True,
            )

            current_podjazd = safe_str(dane.get("Faktyczny_Podjazd"))
            podjazd_date = None
            podjazd_time = None

            if current_podjazd:
                try:
                    if " " in current_podjazd:
                        obj = datetime.strptime(
                            current_podjazd, "%Y-%m-%d %H:%M"
                        )
                        podjazd_date = obj.date()
                        podjazd_time = obj.time()
                    else:
                        podjazd_date = f_data
                        podjazd_time = parse_time(current_podjazd)
                except Exception:
                    pass

            f_podjazd_data = st.date_input(
                "Data faktycznego podjazdu",
                value=podjazd_date or f_data,
            )

            f_podjazd_czas = st.time_input(
                "Godzina faktycznego podjazdu",
                value=podjazd_time,
            )

            usun_podjazd = st.checkbox(
                "Wyczyść faktyczny podjazd",
                value=podjazd_time is None,
            )

            f_trwa = st.selectbox(
                "Operacja w toku?",
                ["NIE", "TAK"],
                index=1 if normalize_bool(dane.get("Trwa_Zaladunek")) else 0,
            )

            f_koniec = st.selectbox(
                "Zakończono?",
                ["NIE", "TAK"],
                index=1 if normalize_bool(dane.get("Zakonczono")) else 0,
            )

            st.markdown("</div>", unsafe_allow_html=True)

        f_notatki = st.text_area(
            "Notatki",
            value=safe_str(dane.get("Notatki")),
            height=100,
        )

        save_col, cancel_col = st.columns(2)

        save = save_col.form_submit_button(
            "💾 ZAPISZ REZERWACJĘ",
            type="primary",
            use_container_width=True,
        )

        cancel = cancel_col.form_submit_button(
            "× ANULUJ",
            use_container_width=True,
        )

        if cancel:
            st.session_state.pokaz_formularz = None
            st.rerun()

        if save:
            if not f_impreza.strip():
                st.error("Nazwa imprezy jest obowiązkowa.")
                return

            if f_do <= f_od:
                st.error("Godzina Do musi być późniejsza niż Godzina Od.")
                return

            reservation_id = (
                st.session_state.get("wybrana_rezerwacja")
                if mode == "EDYCJA"
                else ""
            )

            conflict, conflict_info = has_conflict(
                df_rampy,
                reservation_id,
                f_rampa,
                f_data,
                f_od,
                f_do,
            )

            if conflict:
                st.error(
                    f"⚠️ Konflikt rezerwacji na rampie {f_rampa}: "
                    f"{conflict_info}"
                )
                return

            final_podjazd = ""
            if not usun_podjazd and f_podjazd_czas:
                final_podjazd = (
                    f"{f_podjazd_data.strftime('%Y-%m-%d')} "
                    f"{f_podjazd_czas.strftime('%H:%M')}"
                )

            if mode == "NOWA":
                new_id = f"RMP-{int(time.time())}"

                new_row = [
                    new_id,
                    f_rampa,
                    str(f_data),
                    f_od.strftime("%H:%M"),
                    f_do.strftime("%H:%M"),
                    f_impreza.strip(),
                    f_pojazd,
                    f_kierowca,
                    f_tel,
                    f_email,
                    f_naczepa,
                    f_typ_naczepy,
                    final_podjazd,
                    f_trwa,
                    f_koniec,
                    f_notatki,
                ]

                db.append_data("DB_Rampy", new_row)
                st.success("Rezerwacja dodana.")

            else:
                idx = df_rampy[
                    df_rampy["ID_Rezerwacji"].astype(str)
                    == str(st.session_state.wybrana_rezerwacja)
                ].index[0]

                updates = {
                    "Rampa": f_rampa,
                    "Data": str(f_data),
                    "Godzina_Od": f_od.strftime("%H:%M"),
                    "Godzina_Do": f_do.strftime("%H:%M"),
                    "Nazwa_Imprezy": f_impreza.strip(),
                    "Pojazd": f_pojazd,
                    "Kierowca": f_kierowca,
                    "Telefon": f_tel,
                    "Email": f_email,
                    "Naczepa": f_naczepa,
                    "Typ_Naczepy": f_typ_naczepy,
                    "Faktyczny_Podjazd": final_podjazd,
                    "Trwa_Zaladunek": f_trwa,
                    "Zakonczono": f_koniec,
                    "Notatki": f_notatki,
                }

                for key, value in updates.items():
                    df_rampy.at[idx, key] = value

                db.update_single_row_safe(
                    "DB_Rampy",
                    int(df_rampy.at[idx, "sheet_row"]),
                    df_rampy.loc[idx],
                )

                st.success("Rezerwacja zaktualizowana.")

            st.session_state.pokaz_formularz = None
            st.session_state.wybrana_rezerwacja = None
            st.session_state.pop("rampy_calendar_v2", None)
            st.rerun()


def render(sh):
    # --------------------------------------------------------
    # INIT
    # --------------------------------------------------------
    inject_css()

    b64_ftl = get_b64("ftl.png")

    if "rampy_data" not in st.session_state:
        st.session_state.rampy_data = date.today()

    if "wybrana_rezerwacja" not in st.session_state:
        st.session_state.wybrana_rezerwacja = None

    if "pokaz_formularz" not in st.session_state:
        st.session_state.pokaz_formularz = None

    render_header()

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------
    worksheet_rampy, df_rampy = db.load_data(sh, "DB_Rampy")

    if worksheet_rampy is None:
        st.warning(
            "⚠️ Nie udało się pobrać danych z Google Sheets. "
            "Odczekaj chwilę i odśwież aplikację."
        )
        return

    if df_rampy.empty and len(df_rampy.columns) <= 1:
        headers = [
            "ID_Rezerwacji",
            "Rampa",
            "Data",
            "Godzina_Od",
            "Godzina_Do",
            "Nazwa_Imprezy",
            "Pojazd",
            "Kierowca",
            "Telefon",
            "Email",
            "Naczepa",
            "Typ_Naczepy",
            "Faktyczny_Podjazd",
            "Trwa_Zaladunek",
            "Zakonczono",
            "Notatki",
        ]
        worksheet_rampy.append_row(headers)
        st.cache_data.clear()
        worksheet_rampy, df_rampy = db.load_data(sh, "DB_Rampy")

    # --------------------------------------------------------
    # TOP NAV
    # --------------------------------------------------------
    nav1, nav2, nav3, nav4 = st.columns([0.55, 2.2, 0.55, 1.0])

    with nav1:
        if st.button("‹", use_container_width=True, key="prev_day_v2"):
            st.session_state.rampy_data -= timedelta(days=1)
            st.session_state.wybrana_rezerwacja = None
            st.rerun()

    with nav2:
        st.markdown("<div class='sqm-date-label'>DZIEŃ OPERACYJNY</div>", unsafe_allow_html=True)
        new_date = st.date_input(
            "Data",
            value=st.session_state.rampy_data,
            label_visibility="collapsed",
            key="date_picker_v2",
        )
        if new_date != st.session_state.rampy_data:
            st.session_state.rampy_data = new_date
            st.session_state.wybrana_rezerwacja = None
            st.rerun()

    with nav3:
        if st.button("›", use_container_width=True, key="next_day_v2"):
            st.session_state.rampy_data += timedelta(days=1)
            st.session_state.wybrana_rezerwacja = None
            st.rerun()

    with nav4:
        if st.button("DZIŚ", use_container_width=True, key="today_v2"):
            st.session_state.rampy_data = date.today()
            st.session_state.wybrana_rezerwacja = None
            st.rerun()

    search_col, add_col = st.columns([3.5, 1.25])

    with search_col:
        st.markdown("<div class='sqm-search-label'>WYSZUKIWANIE</div>", unsafe_allow_html=True)
        search = st.text_input(
            "Szukaj",
            placeholder="🔍  impreza, rejestracja, kierowca, naczepa...",
            label_visibility="collapsed",
            key="ramp_search_v2",
        )

    with add_col:
        st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
        st.markdown("<div class='sqm-primary'>", unsafe_allow_html=True)
        if st.button(
            "＋ NOWA REZERWACJA",
            use_container_width=True,
            key="new_reservation_v2",
        ):
            st.session_state.pokaz_formularz = "NOWA"
            st.session_state.wybrana_rezerwacja = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # WEEKEND WARNING
    # --------------------------------------------------------
    if st.session_state.rampy_data.weekday() >= 5:
        st.warning(
            "MAGAZYN ZAMKNIĘTY W WEEKEND — rezerwację dodawaj tylko po "
            "wcześniejszym uzgodnieniu z obsługą."
        )

    # --------------------------------------------------------
    # FILTER DATA
    # --------------------------------------------------------
    if df_rampy.empty:
        df_dzien = df_rampy.copy()
    else:
        df_dzien = df_rampy[
            df_rampy["Data"].astype(str)
            == str(st.session_state.rampy_data)
        ].copy()

        if search.strip():
            mask = df_dzien.astype(str).apply(
                lambda row: row.str.contains(
                    search.strip(), case=False, na=False
                ).any(),
                axis=1,
            )
            df_dzien = df_dzien[mask]

    render_kpis(df_dzien)

    # --------------------------------------------------------
    # CALENDAR
    # --------------------------------------------------------
    events = build_events(df_dzien)

    calendar_options = {
        "initialView": "resourceTimeGridDay",
        "initialDate": str(st.session_state.rampy_data),
        "resources": [
            {"id": ramp, "title": f"RAMPA {ramp}"}
            for ramp in RAMPY
        ],
        "slotMinTime": "07:00:00",
        "slotMaxTime": "19:00:00",
        "slotDuration": "00:30:00",
        "slotLabelInterval": "01:00",
        "allDaySlot": False,
        "editable": True,
        "eventStartEditable": True,
        "eventDurationEditable": True,
        "droppable": False,
        "selectable": False,
        "headerToolbar": False,
        "height": 720,
        "nowIndicator": True,
        "scrollTime": "08:00:00",
        "slotLabelFormat": {
            "hour": "2-digit",
            "minute": "2-digit",
            "hour12": False,
        },
        "resourceAreaWidth": "85px",
    }

    cal_css = """
    .fc .fc-scrollgrid {
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    .fc .fc-timegrid-axis {
        background: #091321 !important;
    }

    .fc .fc-timegrid-axis-cushion {
        color: #8E8A82 !important;
    }

    .fc .fc-resource-cell {
        background: #0B1728 !important;
        color: #E8E2D9 !important;
    }

    .fc .fc-resource-cell .fc-datagrid-cell-main {
        font-family: 'Bebas Neue', Arial Narrow, sans-serif !important;
        letter-spacing: 1px !important;
    }

    .fc-event {
        min-height: 24px !important;
    }
    """

    st.markdown("<div class='sqm-calendar-shell'>", unsafe_allow_html=True)

    cal_state = calendar(
        events=events,
        options=calendar_options,
        custom_css=cal_css,
        callbacks=["eventClick", "eventChange"],
        key="rampy_calendar_v2",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="sqm-legend">
            <div class="sqm-legend-item">
                <span class="sqm-dot" style="background:{COLORS["gold"]}"></span>
                Oczekuje
            </div>
            <div class="sqm-legend-item">
                <span class="sqm-dot" style="background:{COLORS["green"]}"></span>
                Pod rampą
            </div>
            <div class="sqm-legend-item">
                <span class="sqm-dot" style="background:{COLORS["blue"]}"></span>
                Operacja w toku
            </div>
            <div class="sqm-legend-item">
                <span class="sqm-dot" style="background:{COLORS["gray"]}"></span>
                Zakończone
            </div>
            <div style="margin-left:auto;">
                Przeciągnij rezerwację, aby zmienić rampę lub godzinę
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # CALENDAR EVENTS
    # --------------------------------------------------------
    if cal_state and cal_state.get("eventChange"):
        changed = cal_state["eventChange"]["event"]
        ev_id = safe_str(changed.get("id"))

        try:
            start_raw = safe_str(changed.get("start"))
            end_raw = safe_str(changed.get("end"))

            start_dt = datetime.fromisoformat(
                start_raw.replace("Z", "+00:00")
            )
            end_dt = (
                datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
                if end_raw
                else start_dt + timedelta(hours=1)
            )

            new_date = start_dt.date()
            new_start = start_dt.time().replace(second=0, microsecond=0)
            new_end = end_dt.time().replace(second=0, microsecond=0)

            # resourceId jest dostępne w większości wersji FullCalendar.
            new_ramp = safe_str(changed.get("resourceId"))
            if not new_ramp:
                # fallback — sprawdzamy event resource w danych.
                old_match = df_rampy[
                    df_rampy["ID_Rezerwacji"].astype(str) == ev_id
                ]
                if not old_match.empty:
                    new_ramp = safe_str(old_match.iloc[0].get("Rampa"), "11")

            conflict, conflict_info = has_conflict(
                df_rampy,
                ev_id,
                new_ramp,
                new_date,
                new_start,
                new_end,
            )

            if conflict:
                st.error(
                    f"⚠️ Nie można przesunąć rezerwacji. "
                    f"Konflikt na rampie {new_ramp}: {conflict_info}"
                )
                st.session_state.pop("rampy_calendar_v2", None)
                st.rerun()

            matches = df_rampy[
                df_rampy["ID_Rezerwacji"].astype(str) == ev_id
            ]

            if not matches.empty:
                idx = matches.index[0]
                df_rampy.at[idx, "Rampa"] = new_ramp
                df_rampy.at[idx, "Data"] = str(new_date)
                df_rampy.at[idx, "Godzina_Od"] = new_start.strftime("%H:%M")
                df_rampy.at[idx, "Godzina_Do"] = new_end.strftime("%H:%M")

                db.update_single_row_safe(
                    "DB_Rampy",
                    int(df_rampy.at[idx, "sheet_row"]),
                    df_rampy.loc[idx],
                )

                st.session_state.rampy_data = new_date
                st.session_state.pop("rampy_calendar_v2", None)
                st.toast(
                    f"✓ Rezerwacja przeniesiona: Rampa {new_ramp}, "
                    f"{new_start.strftime('%H:%M')}–{new_end.strftime('%H:%M')}"
                )
                time.sleep(.3)
                st.rerun()

        except Exception as e:
            st.error(f"Błąd podczas przesuwania rezerwacji: {e}")

    if cal_state and cal_state.get("eventClick"):
        clicked = cal_state["eventClick"]["event"]
        clicked_id = safe_str(clicked.get("id"))

        if clicked_id:
            st.session_state.wybrana_rezerwacja = clicked_id
            st.session_state.pokaz_formularz = None
            st.session_state.pop("rampy_calendar_v2", None)
            st.rerun()

    # --------------------------------------------------------
    # DETAIL / FORM
    # --------------------------------------------------------
    if st.session_state.get("pokaz_formularz") in ("NOWA", "EDYCJA"):
        render_form(df_rampy)
    elif st.session_state.get("wybrana_rezerwacja"):
        render_detail_panel(df_rampy, b64_ftl)


# Alias dla istniejącego sposobu uruchamiania modułu.
# Jeśli reszta projektu importuje render(), nic nie trzeba zmieniać.
