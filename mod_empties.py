import streamlit as st
import pandas as pd
import datetime
import base64
import os
import html
import db
from db import load_data


# ============================================================
# BASEBALL CONFIGURATION
# ============================================================

STATUSY = [
    "0. 🚚 Dostarczone na targi (Pełne)",
    "1. 🔴 Puste do odebrania (Hala)",
    "2. 🟢 Puste zmagazynowane",
    "3. ⚠️ Do dostarczenia (Demontaż)",
    "4. 📦 Puste dostarczone (Pakowanie)",
    "5. 🚨 Pełne gotowe do zabrania",
    "6. ✅ Pełne zabrane (W drodze)",
]


INNINGS = [
    {
        "number": "01",
        "team": "YANKEES",
        "title": "DELIVERED",
        "subtitle": "Dostarczone na targi",
        "bg": "#0C2340",
        "bg2": "#162F52",
        "accent": "#C4CED4",
        "border": "#FFFFFF",
        "font": "'Bebas Neue', sans-serif",
    },
    {
        "number": "02",
        "team": "RED SOX",
        "title": "EMPTY PICKUP",
        "subtitle": "Puste do odebrania",
        "bg": "#8B2635",
        "bg2": "#BD3039",
        "accent": "#FFFFFF",
        "border": "#FFFFFF",
        "font": "'Bebas Neue', sans-serif",
    },
    {
        "number": "03",
        "team": "ATHLETICS",
        "title": "STORAGE",
        "subtitle": "Puste zmagazynowane",
        "bg": "#003831",
        "bg2": "#115E45",
        "accent": "#EFB21E",
        "border": "#EFB21E",
        "font": "'Bebas Neue', sans-serif",
    },
    {
        "number": "04",
        "team": "GIANTS",
        "title": "DISMANTLE",
        "subtitle": "Do dostarczenia — demontaż",
        "bg": "#1F1F1F",
        "bg2": "#332B27",
        "accent": "#FD5A1E",
        "border": "#FD5A1E",
        "font": "'Playball', cursive",
    },
    {
        "number": "05",
        "team": "DODGERS",
        "title": "PACKING",
        "subtitle": "Puste dostarczone — pakowanie",
        "bg": "#005A9C",
        "bg2": "#00447A",
        "accent": "#FFFFFF",
        "border": "#FFFFFF",
        "font": "'Playball', cursive",
    },
    {
        "number": "06",
        "team": "CUBS",
        "title": "READY",
        "subtitle": "Pełne gotowe do zabrania",
        "bg": "#0E3386",
        "bg2": "#172D6B",
        "accent": "#CC3433",
        "border": "#CC3433",
        "font": "'Bebas Neue', sans-serif",
    },
    {
        "number": "07",
        "team": "WHITE SOX",
        "title": "IN TRANSIT",
        "subtitle": "Pełne zabrane — w drodze",
        "bg": "#27251F",
        "bg2": "#111111",
        "accent": "#C4CED4",
        "border": "#C4CED4",
        "font": "'Bebas Neue', sans-serif",
    },
]


# ============================================================
# HELPERS
# ============================================================

def safe_text(value, fallback="-"):
    """Bezpieczne wyświetlanie wartości z DataFrame."""
    if value is None:
        return fallback

    try:
        if pd.isna(value):
            return fallback
    except Exception:
        pass

    value = str(value).strip()

    if value.lower() in ("nan", "none", "nat"):
        return fallback

    return value if value else fallback


def esc(value, fallback="-"):
    """HTML escape."""
    return html.escape(safe_text(value, fallback))


def load_batter_image():
    """Ładowanie batter.png jako Base64."""
    if os.path.exists("batter.png"):
        try:
            with open("batter.png", "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return ""
    return ""


def get_status_index(status):
    """Zwraca numer inningu dla statusu."""
    try:
        return STATUSY.index(status)
    except ValueError:
        return 0


def update_status(worksheet, row, new_status):
    """Bezpieczna zmiana statusu."""
    db.update_single_row_safe(
        "DB_Empties",
        int(row["sheet_row"]),
        pd.Series([
            row["ID_Empties"],
            row["Nazwa_Eventu"],
            row["Numery_Projektow"],
            new_status,
            row["Lokalizacja_Aktualna"],
            row["Auto_Kierowca"],
            row["Data_Akcji"],
            row["Notatki"],
        ])
    )

    st.cache_data.clear()
    st.rerun()


# ============================================================
# GLOBAL CSS
# ============================================================

def inject_css():
    st.markdown(
        """
        <style>

        /* =====================================================
           GOOGLE FONTS
        ===================================================== */

        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Playball&family=Roboto+Condensed:wght@300;400;500;600;700;800&display=swap');


        /* =====================================================
           SCOREBOARD HEADER
        ===================================================== */

        .scoreboard {
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(
                    135deg,
                    rgba(17, 25, 39, 0.98),
                    rgba(8, 12, 19, 0.98)
                );
            border: 1px solid rgba(197,168,128,0.35);
            border-top: 4px solid #BA4949;
            border-radius: 10px;
            padding: 25px 28px 22px 28px;
            margin-bottom: 18px;
            box-shadow:
                0 18px 45px rgba(0,0,0,0.45),
                inset 0 1px 0 rgba(255,255,255,0.03);
        }

        .scoreboard::before {
            content: "";
            position: absolute;
            inset: 0;
            opacity: 0.035;
            background-image:
                repeating-linear-gradient(
                    0deg,
                    transparent,
                    transparent 4px,
                    #ffffff 5px
                );
            pointer-events: none;
        }

        .scoreboard-title {
            position: relative;
            z-index: 2;
            font-family: 'Playball', cursive;
            color: #F4EFE5;
            font-size: 52px;
            line-height: 1;
            text-shadow:
                3px 3px 0 #8B3038,
                0 7px 25px rgba(0,0,0,0.55);
            margin: 0;
        }

        .scoreboard-subtitle {
            position: relative;
            z-index: 2;
            margin-top: 7px;
            color: #BFAF97;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 13px;
            letter-spacing: 4px;
        }

        .live-indicator {
            position: absolute;
            right: 25px;
            top: 25px;
            font-family: 'Bebas Neue', sans-serif;
            letter-spacing: 2px;
            font-size: 13px;
            color: #E7E0D4;
            border: 1px solid rgba(255,255,255,0.15);
            padding: 5px 11px;
            border-radius: 4px;
            background: rgba(0,0,0,0.25);
        }

        .live-dot {
            color: #D54A4A;
            margin-right: 5px;
        }


        /* =====================================================
           KPI
        ===================================================== */

        .kpi-card {
            background: rgba(12,16,23,0.94);
            border: 1px solid rgba(197,168,128,0.22);
            border-radius: 6px;
            padding: 10px 13px;
            min-height: 62px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.025),
                0 5px 15px rgba(0,0,0,0.25);
        }

        .kpi-label {
            color: #8E8A83;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 10px;
            letter-spacing: 1.8px;
        }

        .kpi-number {
            color: #EFE8DB;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 28px;
            line-height: 1;
        }


        /* =====================================================
           SEARCH
        ===================================================== */

        .search-label {
            color: #C5A880;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 11px;
            letter-spacing: 2px;
            margin-bottom: 4px;
        }

        div[data-testid="stTextInput"] input {
            background: #0B1017 !important;
            border: 1px solid rgba(197,168,128,0.30) !important;
            border-radius: 5px !important;
            color: #F3EEE5 !important;
            font-family: 'Roboto Condensed', sans-serif !important;
            font-size: 14px !important;
        }

        div[data-testid="stTextInput"] input:focus {
            border-color: #C5A880 !important;
            box-shadow: 0 0 0 1px rgba(197,168,128,0.25) !important;
        }


        /* =====================================================
           SELECTBOX
        ===================================================== */

        div[data-testid="stSelectbox"] label {
            color: #C5A880 !important;
            font-family: 'Bebas Neue', sans-serif !important;
            letter-spacing: 1.5px;
            font-size: 11px !important;
        }

        div[data-baseweb="select"] > div {
            background: #0B1017 !important;
            border-color: rgba(197,168,128,0.30) !important;
        }


        /* =====================================================
           INNING HEADER
        ===================================================== */

        .inning-header {
            position: relative;
            overflow: hidden;
            min-height: 92px;
            padding: 15px 17px;
            margin-top: 10px;
            margin-bottom: 11px;
            border-radius: 7px;
            border: 1px solid rgba(255,255,255,0.18);
            box-shadow:
                0 7px 20px rgba(0,0,0,0.35),
                inset 0 1px 0 rgba(255,255,255,0.08);
        }

        .inning-header::after {
            content: "";
            position: absolute;
            right: -45px;
            top: -65px;
            width: 210px;
            height: 210px;
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 50%;
        }

        .inning-number {
            position: absolute;
            left: 14px;
            top: 10px;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 11px;
            letter-spacing: 2px;
            opacity: 0.65;
        }

        .inning-team {
            position: relative;
            z-index: 2;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 11px;
            letter-spacing: 3px;
            opacity: 0.75;
            margin-top: 12px;
        }

        .inning-title {
            position: relative;
            z-index: 2;
            font-size: 25px;
            line-height: 1;
            margin-top: 4px;
            text-shadow: 2px 2px 5px rgba(0,0,0,0.5);
        }

        .inning-subtitle {
            position: relative;
            z-index: 2;
            font-family: 'Roboto Condensed', sans-serif;
            font-size: 11px;
            margin-top: 6px;
            opacity: 0.78;
        }

        .inning-count {
            position: absolute;
            z-index: 3;
            right: 14px;
            bottom: 13px;
            min-width: 38px;
            text-align: center;
            padding: 3px 8px;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 18px;
            color: #080B10;
            border-radius: 4px;
        }


        /* =====================================================
           PROJECT CARD
        ===================================================== */

        .project-card {
            position: relative;
            background:
                linear-gradient(
                    145deg,
                    rgba(29,31,34,0.98),
                    rgba(17,19,22,0.98)
                );
            border: 1px solid rgba(197,168,128,0.16);
            border-radius: 6px;
            padding: 13px;
            margin-bottom: 5px;
            overflow: hidden;
            box-shadow:
                0 5px 13px rgba(0,0,0,0.30);
        }

        .project-card::after {
            content: "";
            position: absolute;
            right: -25px;
            bottom: -45px;
            width: 120px;
            height: 120px;
            border: 1px solid rgba(255,255,255,0.035);
            border-radius: 50%;
        }

        .card-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255,255,255,0.055);
        }

        .project-number {
            font-family: 'Bebas Neue', sans-serif;
            font-size: 24px;
            letter-spacing: 1.8px;
        }

        .project-date {
            font-family: 'Bebas Neue', sans-serif;
            font-size: 10px;
            letter-spacing: 1px;
            color: #C7C0B4;
            background: rgba(197,168,128,0.10);
            border: 1px solid rgba(197,168,128,0.13);
            padding: 3px 6px;
            border-radius: 3px;
        }

        .event-name {
            margin-top: 9px;
            color: #EDE7DC;
            font-family: 'Roboto Condensed', sans-serif;
            font-size: 13px;
            font-weight: 700;
        }

        .card-info {
            color: #C8C2B8;
            font-family: 'Roboto Condensed', sans-serif;
            font-size: 11px;
            margin-top: 5px;
        }

        .card-driver {
            color: #BDA889;
            font-family: 'Roboto Condensed', sans-serif;
            font-size: 11px;
            font-weight: 700;
            margin-top: 5px;
        }

        .card-notes {
            background: rgba(0,0,0,0.28);
            border-left: 2px solid #A88962;
            padding: 6px 7px;
            margin-top: 9px;
            color: #A8A197;
            font-family: 'Roboto Condensed', sans-serif;
            font-size: 10px;
            font-style: italic;
        }


        /* =====================================================
           PROGRESS
        ===================================================== */

        .progress-wrap {
            margin-top: 12px;
            margin-bottom: 4px;
        }

        .progress-label {
            color: #706B64;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 8px;
            letter-spacing: 1.5px;
            margin-bottom: 4px;
        }

        .progress-line {
            display: flex;
            gap: 3px;
            height: 5px;
        }

        .progress-segment {
            flex: 1;
            border-radius: 2px;
            background: #292B2E;
        }

        .progress-segment.active {
            background: #BFA274;
            box-shadow: 0 0 5px rgba(191,162,116,0.35);
        }


        /* =====================================================
           EMPTY STATE
        ===================================================== */

        .empty-state {
            text-align: center;
            background: rgba(0,0,0,0.18);
            border: 1px dashed rgba(197,168,128,0.18);
            border-radius: 6px;
            padding: 20px 10px;
            margin-bottom: 15px;
            color: #69665F;
            font-family: 'Bebas Neue', sans-serif;
            letter-spacing: 1.5px;
            font-size: 11px;
        }


        /* =====================================================
           BUTTONS
        ===================================================== */

        div[data-testid="stButton"] button {
            background: #111318 !important;
            color: #BCA989 !important;
            border: 1px solid rgba(197,168,128,0.20) !important;
            border-radius: 4px !important;
            min-height: 29px !important;
            padding: 0 4px !important;
            font-family: 'Bebas Neue', sans-serif !important;
            font-size: 10px !important;
            letter-spacing: 1px !important;
        }

        div[data-testid="stButton"] button:hover {
            background: #C5A880 !important;
            color: #080B11 !important;
            border-color: #F4EFE5 !important;
        }

        div[data-testid="stButton"] button[kind="primary"] {
            background: #8B3038 !important;
            color: #F9F3E9 !important;
            border-color: #BA4949 !important;
        }

        div[data-testid="stButton"] button[kind="primary"]:hover {
            background: #BA4949 !important;
        }


        /* =====================================================
           POPOVER
        ===================================================== */

        div[data-testid="stPopoverBody"] {
            background: #10141B !important;
            border: 1px solid #A88962 !important;
            box-shadow: 0 15px 45px rgba(0,0,0,0.75) !important;
        }


        /* =====================================================
           FORM
        ===================================================== */

        .form-title {
            color: #C5A880;
            font-family: 'Playball', cursive;
            font-size: 32px;
            margin-bottom: 3px;
        }

        .form-subtitle {
            color: #77736B;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 11px;
            letter-spacing: 2px;
            margin-bottom: 20px;
        }


        /* =====================================================
           MOBILE
        ===================================================== */

        @media (max-width: 900px) {

            .scoreboard-title {
                font-size: 40px;
            }

            .live-indicator {
                display: none;
            }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SCOREBOARD
# ============================================================

def render_scoreboard(df_event, search_query):

    total = len(df_event)

    buffer_count = len(
        df_event[
            df_event["Status"].astype(str).str.startswith("2.")
        ]
    )

    ready_count = len(
        df_event[
            df_event["Status"].astype(str).str.startswith("5.")
        ]
    )

    transit_count = len(
        df_event[
            df_event["Status"].astype(str).str.startswith("6.")
        ]
    )

    st.markdown(
        """
        <div class="scoreboard">

            <div class="live-indicator">
                <span class="live-dot">●</span> LIVE CONTROL
            </div>

            <div class="scoreboard-title">
                EMPTIES CONTROL CENTER
            </div>

            <div class="scoreboard-subtitle">
                MAJOR LEAGUE LOGISTICS · PROJECT ROSTER · OPERATIONS
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4, gap="small")

    cards = [
        ("PROJECTS", total),
        ("IN BUFFER", buffer_count),
        ("READY", ready_count),
        ("IN TRANSIT", transit_count),
    ]

    for col, (label, value) in zip([c1, c2, c3, c4], cards):

        col.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-number">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# SEARCH
# ============================================================

def apply_search(df, query):

    if not query:
        return df

    query = query.strip()

    if not query:
        return df

    search_columns = [
        "ID_Empties",
        "Nazwa_Eventu",
        "Numery_Projektow",
        "Status",
        "Lokalizacja_Aktualna",
        "Auto_Kierowca",
        "Data_Akcji",
        "Notatki",
    ]

    available = [
        col for col in search_columns
        if col in df.columns
    ]

    if not available:
        return df

    search_text = (
        df[available]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
    )

    mask = search_text.str.contains(
        query,
        case=False,
        na=False,
        regex=False,
    )

    return df[mask].copy()


# ============================================================
# PROGRESS BAR
# ============================================================

def render_progress(current_index):

    segments = ""

    for i in range(len(STATUSY)):

        active = "active" if i <= current_index else ""

        segments += (
            f'<div class="progress-segment {active}"></div>'
        )

    st.markdown(
        f"""
        <div class="progress-wrap">

            <div class="progress-label">
                PROJECT JOURNEY · BASE {current_index + 1}/7
            </div>

            <div class="progress-line">
                {segments}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# PROJECT CARD
# ============================================================

def render_project_card(
    row,
    idx,
    style,
    worksheet,
):

    proj_id = safe_text(row.get("ID_Empties"))
    sheet_row = int(row["sheet_row"])

    project_number = esc(
        row.get("Numery_Projektow")
    )

    event_name = esc(
        row.get("Nazwa_Eventu")
    )

    location = esc(
        row.get("Lokalizacja_Aktualna"),
        "Brak lokalizacji",
    )

    driver = esc(
        row.get("Auto_Kierowca")
    )

    date = esc(
        row.get("Data_Akcji")
    )

    notes = safe_text(
        row.get("Notatki"),
        "",
    )

    notes_html = ""

    if notes:
        notes_html = f"""
            <div class="card-notes">
                📝 {esc(notes, "")}
            </div>
        """

    st.markdown(
        f"""
        <div class="project-card">

            <div class="card-top">

                <div
                    class="project-number"
                    style="color:{style['accent']};"
                >
                    #{project_number}
                </div>

                <div class="project-date">
                    📅 {date}
                </div>

            </div>

            <div class="event-name">
                {event_name}
            </div>

            <div class="card-info">
                📍 {location}
            </div>

            <div class="card-driver">
                🚚 {driver}
            </div>

            {notes_html}

        </div>
        """,
        unsafe_allow_html=True,
    )

    render_progress(idx)

    b1, b2, b3, b4 = st.columns(
        [1, 1, 1, 1],
        gap="small",
    )

    # --------------------------------------------------------
    # PREVIOUS
    # --------------------------------------------------------

    with b1:

        if idx > 0:

            if st.button(
                "◀ BACK",
                key=f"back_{proj_id}",
                use_container_width=True,
                help="Cofnij projekt do poprzedniej bazy",
            ):

                update_status(
                    worksheet,
                    row,
                    STATUSY[idx - 1],
                )

    # --------------------------------------------------------
    # EDIT
    # --------------------------------------------------------

    with b2:

        with st.popover(
            "EDIT",
            use_container_width=True,
        ):

            st.markdown(
                """
                <div style="
                    font-family:'Playball';
                    color:#C5A880;
                    font-size:25px;
                    margin-bottom:12px;
                ">
                    Project Correction
                </div>
                """,
                unsafe_allow_html=True,
            )

            e_loc = st.text_input(
                "📍 Lokalizacja",
                value=safe_text(
                    row.get("Lokalizacja_Aktualna"),
                    "",
                ),
                key=f"edit_loc_{proj_id}",
            )

            e_auto = st.text_input(
                "🚚 Auto / Kierowca",
                value=safe_text(
                    row.get("Auto_Kierowca"),
                    "",
                ),
                key=f"edit_auto_{proj_id}",
            )

            try:

                parsed_date = datetime.datetime.strptime(
                    safe_text(row.get("Data_Akcji")),
                    "%Y-%m-%d",
                ).date()

            except Exception:

                parsed_date = datetime.datetime.now().date()

            e_date = st.date_input(
                "📅 Data",
                value=parsed_date,
                key=f"edit_date_{proj_id}",
            )

            e_notes = st.text_area(
                "📝 Notatki",
                value=safe_text(
                    row.get("Notatki"),
                    "",
                ),
                key=f"edit_notes_{proj_id}",
            )

            if st.button(
                "SAVE UPDATE",
                key=f"save_{proj_id}",
                type="primary",
                use_container_width=True,
            ):

                db.update_single_row_safe(
                    "DB_Empties",
                    sheet_row,
                    pd.Series([
                        row["ID_Empties"],
                        row["Nazwa_Eventu"],
                        row["Numery_Projektow"],
                        STATUSY[idx],
                        e_loc,
                        e_auto,
                        str(e_date),
                        e_notes,
                    ]),
                )

                st.cache_data.clear()
                st.rerun()

    # --------------------------------------------------------
    # DELETE
    # --------------------------------------------------------

    with b3:

        with st.popover(
            "DEL",
            use_container_width=True,
        ):

            st.markdown(
                """
                <div style="
                    color:#D85B5B;
                    font-family:'Bebas Neue';
                    font-size:18px;
                    letter-spacing:1px;
                ">
                    REMOVE PROJECT?
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.caption(
                f"Projekt #{project_number} zostanie usunięty."
            )

            if st.button(
                "CONFIRM DELETE",
                key=f"delete_{proj_id}",
                type="primary",
                use_container_width=True,
            ):

                db.delete_row(
                    "DB_Empties",
                    sheet_row,
                )

                st.cache_data.clear()
                st.rerun()

    # --------------------------------------------------------
    # NEXT
    # --------------------------------------------------------

    with b4:

        if idx < len(STATUSY) - 1:

            if st.button(
                "NEXT BASE ▶",
                key=f"next_{proj_id}",
                use_container_width=True,
                help="Przenieś projekt do następnego etapu",
            ):

                update_status(
                    worksheet,
                    row,
                    STATUSY[idx + 1],
                )

    st.markdown(
        "<div style='height:14px;'></div>",
        unsafe_allow_html=True,
    )


# ============================================================
# INNING
# ============================================================

def render_inning(
    df_event,
    status_index,
    container,
    batter_b64,
    worksheet,
):

    config = INNINGS[status_index]

    status_name = STATUSY[status_index]

    df_status = df_event[
        df_event["Status"] == status_name
    ]

    count = len(df_status)

    batter_style = ""

    if batter_b64:

        batter_style = f"""
            background-image:
                url("data:image/png;base64,{batter_b64}");
            background-size: contain;
            background-position: right center;
            background-repeat: no-repeat;
        """

    with container:

        st.markdown(
            f"""
            <div
                class="inning-header"
                style="
                    background:
                        linear-gradient(
                            135deg,
                            {config['bg']},
                            {config['bg2']}
                        );
                    color:{config['accent']};
                    border-color:{config['border']};
                    {batter_style}
                "
            >

                <div class="inning-number">
                    INNING {config['number']}
                </div>

                <div class="inning-team">
                    {config['team']}
                </div>

                <div
                    class="inning-title"
                    style="
                        font-family:{config['font']};
                        color:{config['accent']};
                    "
                >
                    {config['title']}
                </div>

                <div class="inning-subtitle">
                    {config['subtitle']}
                </div>

                <div
                    class="inning-count"
                    style="
                        background:{config['accent']};
                    "
                >
                    {count}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        if df_status.empty:

            st.markdown(
                """
                <div class="empty-state">
                    NO PLAYERS ON BASE
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            for _, row in df_status.iterrows():

                render_project_card(
                    row=row,
                    idx=status_index,
                    style=config,
                    worksheet=worksheet,
                )


# ============================================================
# ADD PROJECT FORM
# ============================================================

def render_add_form(
    df,
):

    st.markdown(
        """
        <div class="form-title">
            Add Project to Roster
        </div>

        <div class="form-subtitle">
            REGISTER NEW LOGISTICS PROJECT
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(
        "form_add_empties",
        clear_on_submit=True,
    ):

        c1, c2 = st.columns(
            2,
            gap="large",
        )

        with c1:

            nazwa_evt = st.text_input(
                "Nazwa imprezy *",
                placeholder="np. IFA Berlin 2026",
            )

            projekty = st.text_input(
                "Numery projektów *",
                placeholder="np. 12345, 12346, 12350",
            )

            status_start = st.selectbox(
                "Starting Base",
                STATUSY,
                index=0,
            )

        with c2:

            lokalizacja = st.text_input(
                "Lokalizacja",
                placeholder="np. Hala 3.2 / stoisko 100",
            )

            auto_kier = st.text_input(
                "Auto / Kierowca",
                placeholder="np. PO 12345 / Jan Kowalski",
            )

            data_akcji = st.date_input(
                "Data dostawy",
                value=datetime.datetime.now().date(),
            )

        notatki = st.text_area(
            "Dodatkowe dyspozycje logistyczne",
            placeholder="Uwagi dotyczące odbioru, magazynu, demontażu...",
        )

        submitted = st.form_submit_button(
            "⚾ ADD TO ROSTER",
            type="primary",
            use_container_width=True,
        )

        if submitted:

            if not nazwa_evt.strip():

                st.error(
                    "Podaj nazwę imprezy."
                )

                return

            if not projekty.strip():

                st.error(
                    "Podaj przynajmniej jeden numer projektu."
                )

                return

            lista_projektow = [
                p.strip()
                for p in projekty.split(",")
                if p.strip()
            ]

            nowe_wiersze = []
            pominete = []

            for i, proj in enumerate(lista_projektow):

                istnieje = False

                if not df.empty:

                    event_mask = (
                        df["Nazwa_Eventu"]
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        ==
                        nazwa_evt.strip().lower()
                    )

                    project_mask = (
                        df["Numery_Projektow"]
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        ==
                        proj.lower()
                    )

                    duplicate = df[
                        event_mask & project_mask
                    ]

                    if not duplicate.empty:
                        istnieje = True

                if istnieje:

                    pominete.append(proj)

                else:

                    nowe_id = (
                        f"EMP-{proj}-"
                        f"{datetime.datetime.now().strftime('%m%d%H%M%S')}-"
                        f"{i}"
                    )

                    nowe_wiersze.append(
                        {
                            "ID_Empties": nowe_id,
                            "Nazwa_Eventu": str(nazwa_evt),
                            "Numery_Projektow": str(proj),
                            "Status": str(status_start),
                            "Lokalizacja_Aktualna": str(lokalizacja),
                            "Auto_Kierowca": str(auto_kier),
                            "Data_Akcji": str(data_akcji),
                            "Notatki": str(notatki),
                        }
                    )

            if nowe_wiersze:

                df_temp = pd.concat(
                    [
                        df,
                        pd.DataFrame(nowe_wiersze),
                    ],
                    ignore_index=True,
                )

                if "sheet_row" in df_temp.columns:

                    df_temp = df_temp.drop(
                        columns=["sheet_row"]
                    )

                fresh_ws = st.session_state[
                    "_empties_worksheet"
                ]

                fresh_ws.clear()

                df_str = (
                    df_temp
                    .astype(str)
                    .replace("nan", "")
                )

                fresh_ws.update(
                    values=[
                        df_str.columns.tolist()
                    ]
                    +
                    df_str.values.tolist(),
                    range_name="A1",
                )

                st.cache_data.clear()

                msg = (
                    f"⚾ HOME RUN! "
                    f"Utworzono {len(nowe_wiersze)} "
                    f"kart projektów."
                )

                if pominete:

                    msg += (
                        " Pominięto duplikaty: "
                        + ", ".join(pominete)
                        + "."
                    )

                st.success(msg)

                st.rerun()

            else:

                st.error(
                    "Wszystkie podane projekty "
                    "już znajdują się na tablicy."
                )


# ============================================================
# MAIN RENDER
# ============================================================

def render(sh):

    # --------------------------------------------------------
    # CSS
    # --------------------------------------------------------

    inject_css()

    # --------------------------------------------------------
    # BATTER IMAGE
    # --------------------------------------------------------

    batter_b64 = load_batter_image()

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    worksheet, df = load_data(
        sh,
        "DB_Empties",
    )

    st.session_state["_empties_worksheet"] = worksheet

    # --------------------------------------------------------
    # INITIALIZE DATABASE
    # --------------------------------------------------------

    if df.empty and len(df.columns) <= 1:

        headers = [
            "ID_Empties",
            "Nazwa_Eventu",
            "Numery_Projektow",
            "Status",
            "Lokalizacja_Aktualna",
            "Auto_Kierowca",
            "Data_Akcji",
            "Notatki",
        ]

        fresh_ws = sh.worksheet(
            "DB_Empties"
        )

        fresh_ws.append_row(headers)

        st.cache_data.clear()

        worksheet, df = load_data(
            sh,
            "DB_Empties",
        )

        st.session_state[
            "_empties_worksheet"
        ] = worksheet

    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------

    tab_board, tab_add = st.tabs(
        [
            "🏟️ CONTROL CENTER",
            "⚾ ADD TO ROSTER",
        ]
    )

    # ========================================================
    # CONTROL CENTER
    # ========================================================

    with tab_board:

        if df.empty:

            render_scoreboard(
                df,
                "",
            )

            st.markdown(
                """
                <div style="
                    text-align:center;
                    padding:70px 20px;
                    color:#716D66;
                    font-family:'Bebas Neue';
                    letter-spacing:2px;
                ">
                    <div style="
                        font-family:'Playball';
                        font-size:42px;
                        color:#A88962;
                    ">
                        No Players on the Field
                    </div>

                    <div style="
                        margin-top:8px;
                        font-size:12px;
                    ">
                        DODAJ PIERWSZY PROJEKT DO ROSTERU
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            # ------------------------------------------------
            # EVENT LIST
            # ------------------------------------------------

            lista_eventow = sorted(
                df["Nazwa_Eventu"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            event_options = [
                "ALL EVENTS"
            ] + lista_eventow

            if (
                "filtr_event_empties"
                not in st.session_state
            ):

                st.session_state[
                    "filtr_event_empties"
                ] = "ALL EVENTS"

            current_event = (
                st.session_state[
                    "filtr_event_empties"
                ]
            )

            if current_event not in event_options:

                current_event = "ALL EVENTS"

            # ------------------------------------------------
            # FILTER BAR
            # ------------------------------------------------

            f1, f2 = st.columns(
                [1.25, 2.75],
                gap="medium",
            )

            with f1:

                wybrany_event = st.selectbox(
                    "EVENT",
                    event_options,
                    index=event_options.index(
                        current_event
                    ),
                )

                st.session_state[
                    "filtr_event_empties"
                ] = wybrany_event

            with f2:

                st.markdown(
                    """
                    <div class="search-label">
                        🔎 SEARCH THE ROSTER
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                search_query = st.text_input(
                    "Search",
                    placeholder=(
                        "Project / Event / Location / "
                        "Driver / Vehicle / Notes..."
                    ),
                    label_visibility="collapsed",
                )

            # ------------------------------------------------
            # EVENT FILTER
            # ------------------------------------------------

            if wybrany_event == "ALL EVENTS":

                df_event = df.copy()

            else:

                df_event = df[
                    df["Nazwa_Eventu"]
                    .astype(str)
                    ==
                    wybrany_event
                ].copy()

            # ------------------------------------------------
            # SEARCH
            # ------------------------------------------------

            df_event = apply_search(
                df_event,
                search_query,
            )

            # ------------------------------------------------
            # SCOREBOARD
            # ------------------------------------------------

            render_scoreboard(
                df_event,
                search_query,
            )

            # ------------------------------------------------
            # SEARCH RESULT INFO
            # ------------------------------------------------

            if search_query:

                st.markdown(
                    f"""
                    <div style="
                        color:#8E897F;
                        font-family:'Bebas Neue';
                        font-size:11px;
                        letter-spacing:1.5px;
                        margin:13px 0 4px 0;
                    ">
                        SEARCH RESULTS FOR
                        <span style="
                            color:#C5A880;
                        ">
                            "{esc(search_query)}"
                        </span>
                        · {len(df_event)} MATCHES
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # ------------------------------------------------
            # DIVIDER
            # ------------------------------------------------

            st.markdown(
                """
                <div style="
                    margin:17px 0 20px 0;
                    border-top:1px dashed
                        rgba(186,73,73,0.45);
                "></div>
                """,
                unsafe_allow_html=True,
            )

            # ------------------------------------------------
            # KANBAN
            # ------------------------------------------------

            col1, col2, col3 = st.columns(
                3,
                gap="large",
            )

            render_inning(
                df_event,
                0,
                col1,
                batter_b64,
                worksheet,
            )

            render_inning(
                df_event,
                1,
                col1,
                batter_b64,
                worksheet,
            )

            render_inning(
                df_event,
                2,
                col1,
                batter_b64,
                worksheet,
            )

            render_inning(
                df_event,
                3,
                col2,
                batter_b64,
                worksheet,
            )

            render_inning(
                df_event,
                4,
                col2,
                batter_b64,
                worksheet,
            )

            render_inning(
                df_event,
                5,
                col3,
                batter_b64,
                worksheet,
            )

            render_inning(
                df_event,
                6,
                col3,
                batter_b64,
                worksheet,
            )

    # ========================================================
    # ADD PROJECT
    # ========================================================

    with tab_add:

        render_add_form(
            df,
        )
