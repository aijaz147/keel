"""
Visual design system for Keel: a dark, data-terminal-inspired analytics
look (near-black canvas, glass cards, a single electric-violet brand
accent, monospace data tags) with a consistent color vocabulary: green =
healthy/profitable, red = risk/negative, blue/violet/cyan = neutral
analytical series.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
COLOR_BG = "#08090D"
COLOR_BG_ELEVATED = "#0E1016"
COLOR_CARD = "#12141C"
COLOR_CARD_HOVER = "#171A24"
COLOR_BORDER = "#23262F"
COLOR_BORDER_SOFT = "#1A1C24"
COLOR_TEXT = "#F3F4F8"
COLOR_SUBTEXT = "#8B8FA3"
COLOR_MUTED = "#5C6070"

COLOR_GREEN = "#2FE6A6"
COLOR_GREEN_BG = "rgba(47, 230, 166, 0.12)"
COLOR_RED = "#FF5C7A"
COLOR_RED_BG = "rgba(255, 92, 122, 0.12)"
COLOR_BLUE = "#5B8DFF"
COLOR_BLUE_BG = "rgba(91, 141, 255, 0.12)"
COLOR_PURPLE = "#8B7CFF"
COLOR_PURPLE_BG = "rgba(139, 124, 255, 0.14)"
COLOR_AMBER = "#FFB020"
COLOR_AMBER_BG = "rgba(255, 176, 32, 0.12)"
COLOR_CYAN = "#22D3EE"

ACCENT_GRADIENT = "linear-gradient(120deg, #8B7CFF 0%, #5B8DFF 55%, #22D3EE 100%)"

CHANNEL_COLORS = {
    "Google Ads": "#5B8DFF",
    "Meta Ads": "#8B7CFF",
    "Organic Search": "#2FE6A6",
    "Email/SMS": "#FFB020",
    "Direct": "#8B8FA3",
    "Organic Social": "#22D3EE",
    "Unattributed": "#3A3D4A",
}

CATEGORY_COLORS = {
    "Cleansers": "#5B8DFF",
    "Serums": "#8B7CFF",
    "Moisturizers": "#22D3EE",
    "Sunscreen": "#FFB020",
    "Eye Care": "#FF5C7A",
    "Masks": "#2FE6A6",
    "Bundles & Sets": "#E066FF",
}

PLOTLY_SEQUENCE = ["#5B8DFF", "#8B7CFF", "#2FE6A6", "#FFB020", "#22D3EE", "#FF5C7A", "#E066FF", "#8B8FA3"]

FONT_FAMILY = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
MONO_FAMILY = "'JetBrains Mono', ui-monospace, monospace"


def inject_global_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: {FONT_FAMILY};
        }}

        .stApp {{
            background:
                radial-gradient(ellipse 1200px 600px at 15% -10%, rgba(139,124,255,0.16), transparent 60%),
                radial-gradient(ellipse 900px 500px at 100% 0%, rgba(34,211,238,0.10), transparent 55%),
                {COLOR_BG};
        }}

        section[data-testid="stSidebar"] {{
            background-color: {COLOR_BG_ELEVATED};
            border-right: 1px solid {COLOR_BORDER_SOFT};
        }}
        section[data-testid="stSidebar"] * {{
            color: {COLOR_TEXT};
        }}

        h1, h2, h3 {{
            color: {COLOR_TEXT};
            font-weight: 800;
            letter-spacing: -0.02em;
        }}

        p, li, span, label {{
            color: {COLOR_TEXT};
        }}

        [data-testid="stCaptionContainer"], .stCaption, small {{
            color: {COLOR_SUBTEXT} !important;
        }}

        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: {COLOR_BORDER}; border-radius: 8px; }}

        /* Brand lockup */
        .pp-brand {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 2px;
        }}
        .pp-brand-mark {{
            width: 30px; height: 30px; border-radius: 9px;
            background: {ACCENT_GRADIENT};
            display: flex; align-items: center; justify-content: center;
            font-size: 15px; font-weight: 900; color: #060709;
            box-shadow: 0 0 18px rgba(139,124,255,0.45);
            flex-shrink: 0;
        }}
        .pp-brand-name {{
            font-size: 1.28rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: {COLOR_TEXT};
        }}
        .pp-brand-tag {{
            font-family: {MONO_FAMILY};
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: {COLOR_MUTED};
            margin: 2px 0 4px 40px;
        }}

        /* Live source tag strip */
        .pp-tagstrip {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 14px 0 22px 0;
        }}
        .pp-tag {{
            font-family: {MONO_FAMILY};
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.06em;
            color: {COLOR_SUBTEXT};
            background: {COLOR_CARD};
            border: 1px solid {COLOR_BORDER};
            padding: 5px 11px;
            border-radius: 7px;
        }}
        .pp-tag .live-dot {{
            display: inline-block;
            width: 6px; height: 6px; border-radius: 50%;
            background: {COLOR_GREEN};
            box-shadow: 0 0 6px {COLOR_GREEN};
            margin-right: 7px;
        }}

        /* Page titles: subtle gradient accent */
        div[data-testid="stAppViewContainer"] h1 {{
            font-size: 2.05rem;
            background: linear-gradient(90deg, #FFFFFF 30%, #C7C2FF 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            padding-bottom: 2px;
        }}

        /* Metric cards */
        .pp-card {{
            background: {COLOR_CARD};
            border: 1px solid {COLOR_BORDER};
            border-radius: 14px;
            padding: 18px 20px;
            height: 100%;
            position: relative;
            transition: border-color 0.15s ease, transform 0.15s ease;
        }}
        .pp-card:hover {{
            border-color: #34374A;
        }}
        .pp-card-label {{
            font-family: {MONO_FAMILY};
            font-size: 0.7rem;
            font-weight: 600;
            color: {COLOR_SUBTEXT};
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .pp-card-value {{
            font-size: clamp(1.15rem, 1.6vw, 1.6rem);
            font-weight: 800;
            color: {COLOR_TEXT};
            line-height: 1.2;
            white-space: nowrap;
            letter-spacing: -0.01em;
        }}
        .pp-card-delta {{
            font-family: {MONO_FAMILY};
            font-size: 0.78rem;
            font-weight: 600;
            margin-top: 8px;
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .pp-delta-pos {{ color: {COLOR_GREEN}; }}
        .pp-delta-neg {{ color: {COLOR_RED}; }}
        .pp-delta-flat {{ color: {COLOR_MUTED}; }}

        /* Section headers */
        .pp-section-title {{
            font-size: 1.08rem;
            font-weight: 700;
            color: {COLOR_TEXT};
            margin: 8px 0 2px 0;
            letter-spacing: -0.01em;
        }}
        .pp-section-sub {{
            font-size: 0.86rem;
            color: {COLOR_SUBTEXT};
            margin-bottom: 12px;
        }}

        /* Insight / recommendation cards */
        .pp-insight {{
            background: {COLOR_CARD};
            border: 1px solid {COLOR_BORDER};
            border-left: 3px solid {COLOR_PURPLE};
            border-radius: 10px;
            padding: 13px 16px;
            margin-bottom: 10px;
            font-size: 0.92rem;
            color: {COLOR_TEXT};
            line-height: 1.5;
        }}
        .pp-insight.warn {{ border-left-color: {COLOR_AMBER}; }}
        .pp-insight.bad {{ border-left-color: {COLOR_RED}; }}
        .pp-insight.good {{ border-left-color: {COLOR_GREEN}; }}

        .pp-reco {{
            background: {COLOR_BG_ELEVATED};
            border: 1px solid {COLOR_BORDER};
            border-radius: 10px;
            padding: 11px 14px;
            margin-bottom: 8px;
            font-size: 0.88rem;
            color: {COLOR_TEXT};
            line-height: 1.5;
        }}

        .pp-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            font-family: {MONO_FAMILY};
        }}
        .pp-badge-green {{ background: {COLOR_GREEN_BG}; color: {COLOR_GREEN}; }}
        .pp-badge-red {{ background: {COLOR_RED_BG}; color: {COLOR_RED}; }}
        .pp-badge-amber {{ background: {COLOR_AMBER_BG}; color: {COLOR_AMBER}; }}
        .pp-badge-blue {{ background: {COLOR_BLUE_BG}; color: {COLOR_BLUE}; }}

        .pp-mono {{
            font-family: {MONO_FAMILY};
            font-size: 0.78rem;
            color: {COLOR_SUBTEXT};
        }}

        /* Streamlit native widget re-skin */
        div[data-testid="stMetricValue"] {{
            font-weight: 800;
            color: {COLOR_TEXT};
        }}

        div[data-testid="stDataFrame"] {{
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid {COLOR_BORDER};
        }}

        div[data-baseweb="select"] > div {{
            background-color: {COLOR_CARD} !important;
            border-color: {COLOR_BORDER} !important;
            border-radius: 9px !important;
        }}

        .stTextInput input, .stTextArea textarea, .stDateInput input {{
            background-color: {COLOR_CARD} !important;
            color: {COLOR_TEXT} !important;
            border-color: {COLOR_BORDER} !important;
            border-radius: 9px !important;
        }}

        .stButton button, .stDownloadButton button {{
            border-radius: 9px !important;
            font-weight: 600 !important;
        }}
        .stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {{
            background: {ACCENT_GRADIENT} !important;
            border: none !important;
            color: #06070A !important;
        }}

        div[data-baseweb="tab-list"] {{
            border-bottom: 1px solid {COLOR_BORDER};
        }}

        [data-testid="stExpander"] {{
            background: {COLOR_CARD};
            border: 1px solid {COLOR_BORDER};
            border-radius: 12px;
        }}

        hr {{ border-color: {COLOR_BORDER}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def brand_lockup(name: str, tag: str) -> None:
    initial = name.strip()[0].upper() if name.strip() else "K"
    st.markdown(
        f'<div class="pp-brand"><div class="pp-brand-mark">{initial}</div>'
        f'<div class="pp-brand-name">{name}</div></div>'
        f'<div class="pp-brand-tag">{tag}</div>',
        unsafe_allow_html=True,
    )


def tag_strip(tags: list[str], live: bool = True) -> None:
    dot = '<span class="live-dot"></span>' if live else ""
    items = "".join(f'<span class="pp-tag">{dot if i == 0 else ""}{t}</span>' for i, t in enumerate(tags))
    st.markdown(f'<div class="pp-tagstrip">{items}</div>', unsafe_allow_html=True)


def metric_card(label: str, value: str, delta: str | None = None, delta_good: bool | None = None, help_text: str | None = None) -> str:
    delta_html = ""
    if delta:
        cls = "pp-delta-flat" if delta_good is None else ("pp-delta-pos" if delta_good else "pp-delta-neg")
        # Arrow reflects the literal direction of change (from the delta
        # string's sign); color reflects whether that direction is good.
        arrow = "▼" if delta.strip().startswith("-") else ("▲" if delta.strip().startswith("+") else "•")
        delta_html = f'<div class="pp-card-delta {cls}"><span>{arrow}</span>{delta}</div>'
    help_html = f' <span class="pp-mono" title="{help_text}">&#9432;</span>' if help_text else ""
    return (
        f'<div class="pp-card"><div class="pp-card-label">{label}{help_html}</div>'
        f'<div class="pp-card-value">{value}</div>{delta_html}</div>'
    )


def section_title(title: str, subtitle: str | None = None) -> None:
    st.markdown(f'<div class="pp-section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="pp-section-sub">{subtitle}</div>', unsafe_allow_html=True)


def multi_stat_card(title: str, subtitle: str, stats: list[tuple[str, str]]) -> str:
    stat_html = "".join(
        f'<div style="flex:1; min-width:88px;">'
        f'<div class="pp-card-label" style="margin-bottom:4px;">{label}</div>'
        f'<div style="font-size:1.15rem; font-weight:800; color:{COLOR_TEXT}; white-space:nowrap;">{value}</div>'
        f"</div>"
        for label, value in stats
    )
    return (
        f'<div class="pp-card">'
        f'<div style="font-size:1rem; font-weight:700; color:{COLOR_TEXT}; margin-bottom:2px;">{title}</div>'
        f'<div style="font-size:0.8rem; color:{COLOR_SUBTEXT}; margin-bottom:14px;">{subtitle}</div>'
        f'<div style="display:flex; gap:14px; flex-wrap:wrap;">{stat_html}</div>'
        f"</div>"
    )


def badge(text: str, kind: str = "blue") -> str:
    return f'<span class="pp-badge pp-badge-{kind}">{text}</span>'
