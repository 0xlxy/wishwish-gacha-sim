"""Global CSS injection.

Palette & type stack match https://codereview.withmartian.com/ — Work Sans at
14 px base, Ant-Design-derived neutral tokens (rgba(0,0,0,0.88) text, #E5DFDF
borders, 6 px radius), purple accent `#563fff`.
"""
from __future__ import annotations

import streamlit as st


# --------------------------------------------------------------------------- #
# Tokens (also consumed by viz/theme.py so Plotly figures match).
# --------------------------------------------------------------------------- #
TEXT_PRIMARY = "rgba(0, 0, 0, 0.88)"
TEXT_SECONDARY = "rgba(0, 0, 0, 0.65)"
TEXT_TERTIARY = "rgba(0, 0, 0, 0.45)"

BG_BODY = "#FFFFFF"
BG_LAYOUT = "#F5F5F5"
BG_SUBTLE = "#FAFAFA"

BORDER = "#E5DFDF"
BORDER_STRONG = "#D9D9D9"

ACCENT = "#563FFF"      # primary link / focus
ACCENT_SOFT = "#F0EDFF"
SUCCESS = "#55C89F"
ERROR = "#EE412B"
WARNING = "#FFD24D"

FONT_STACK = (
    '"Work Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", '
    'Helvetica, Arial, sans-serif'
)
MONO_STACK = (
    '"SF Mono", SFMono-Regular, "JetBrains Mono", Consolas, '
    '"Liberation Mono", Menlo, monospace'
)

SHADOW_CARD = (
    "0 1px 2px -2px rgba(0,0,0,0.16), "
    "0 3px 6px 0 rgba(0,0,0,0.08)"
)


# --------------------------------------------------------------------------- #
# CSS — one long string, interpolated with the tokens above.
# --------------------------------------------------------------------------- #
_CSS = f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
/* ------------------------------------------------------------------------- */
/* Base: Work Sans at 14 px, Ant-style neutrals                               */
/* ------------------------------------------------------------------------- */
html, body {{
    font-family: {FONT_STACK};
    font-size: 14px;
    line-height: 1.5;
    color: {TEXT_PRIMARY};
    background: {BG_LAYOUT};
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}
.stApp {{
    background: {BG_LAYOUT};
}}
.stMarkdown, .stText, .stAlert, .stCaption, .stMetric, .stTabs,
.stButton > button, .stTextInput, .stNumberInput, .stSelectbox,
.stSlider, .stDataEditor, .stDataFrame, p, span, label,
h1, h2, h3, h4, h5, h6, div[data-testid="stMarkdownContainer"] {{
    font-family: {FONT_STACK} !important;
}}
code, pre, kbd, tt {{
    font-family: {MONO_STACK} !important;
    font-size: 0.92em;
}}
/* Preserve Material Icons glyph font */
[class*="material-icons"], [class*="material-symbols"],
[data-testid="stIconMaterial"], [data-testid*="Icon"] span {{
    font-family: "Material Symbols Rounded", "Material Symbols Outlined",
                 "Material Icons" !important;
    font-feature-settings: "liga";
}}

/* ------------------------------------------------------------------------- */
/* Main container: generous whitespace, centered                              */
/* ------------------------------------------------------------------------- */
.block-container {{
    padding-top: 1.25rem !important;
    padding-bottom: 3rem !important;
    max-width: 1320px;
    background: {BG_BODY};
}}
[data-testid="stAppViewContainer"] > .main {{
    background: {BG_BODY};
}}

/* ------------------------------------------------------------------------- */
/* Typography scale                                                           */
/* ------------------------------------------------------------------------- */
h1 {{
    font-size: 28px !important;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    letter-spacing: -0.01em;
    margin-bottom: 0.25rem !important;
}}
h2 {{
    font-size: 18px !important;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    margin-top: 1.5rem !important;
}}
h3 {{
    font-size: 15px !important;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}
h4, h5 {{
    font-size: 14px !important;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}
.stCaption, [data-testid="stCaptionContainer"] {{
    color: {TEXT_SECONDARY} !important;
    font-size: 13px !important;
}}

/* ------------------------------------------------------------------------- */
/* Sidebar                                                                    */
/* ------------------------------------------------------------------------- */
[data-testid="stSidebar"] {{
    min-width: 260px !important;
    max-width: 280px !important;
    background: {BG_BODY};
    border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] .block-container {{
    padding-top: 1rem !important;
    background: {BG_BODY};
}}
[data-testid="stSidebar"] h4 {{
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {TEXT_TERTIARY} !important;
    font-weight: 600;
    margin-top: 1rem;
    margin-bottom: 0.25rem;
}}

/* ------------------------------------------------------------------------- */
/* KPI metric cards                                                           */
/* ------------------------------------------------------------------------- */
[data-testid="stMetric"] {{
    background: {BG_BODY};
    border: 1px solid {BORDER};
    padding: 12px 14px;
    border-radius: 6px;
    box-shadow: {SHADOW_CARD};
}}
[data-testid="stMetricLabel"] {{
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {TEXT_SECONDARY} !important;
    font-weight: 500;
}}
[data-testid="stMetricValue"] {{
    font-size: 22px !important;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    letter-spacing: -0.01em;
}}

/* ------------------------------------------------------------------------- */
/* Inputs                                                                     */
/* ------------------------------------------------------------------------- */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {{
    border-radius: 6px !important;
    border-color: {BORDER} !important;
    background: {BG_BODY} !important;
    font-size: 13px !important;
}}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 2px {ACCENT_SOFT} !important;
}}
label p, .stNumberInput label, .stTextInput label, .stSelectbox label,
.stSlider label, .stCheckbox label {{
    font-size: 13px !important;
    color: {TEXT_SECONDARY} !important;
    font-weight: 500;
}}

/* ------------------------------------------------------------------------- */
/* Buttons                                                                    */
/* ------------------------------------------------------------------------- */
.stButton > button {{
    border-radius: 6px;
    border: 1px solid {BORDER};
    background: {BG_BODY};
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 500;
    padding: 6px 14px;
    box-shadow: {SHADOW_CARD};
    transition: all 0.15s ease;
}}
.stButton > button:hover {{
    border-color: {ACCENT} !important;
    color: {ACCENT} !important;
    background: {BG_BODY};
}}
.stButton > button[kind="primary"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #FFFFFF;
}}
.stButton > button[kind="primary"]:hover {{
    background: #6E5BFF !important;
    border-color: #6E5BFF !important;
    color: #FFFFFF !important;
}}

/* ------------------------------------------------------------------------- */
/* Expanders                                                                  */
/* ------------------------------------------------------------------------- */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {BG_BODY};
    box-shadow: {SHADOW_CARD};
}}
.streamlit-expanderHeader, [data-testid="stExpander"] summary {{
    font-size: 13px !important;
    font-weight: 500 !important;
    color: {TEXT_PRIMARY};
}}

/* ------------------------------------------------------------------------- */
/* Tabs                                                                       */
/* ------------------------------------------------------------------------- */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0.75rem;
    border-bottom: 1px solid {BORDER};
}}
.stTabs [data-baseweb="tab"] {{
    font-size: 14px;
    font-weight: 500;
    color: {TEXT_SECONDARY};
    padding: 0.5rem 0.25rem;
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: {ACCENT} !important;
}}
.stTabs [data-baseweb="tab-highlight"] {{
    background-color: {ACCENT} !important;
}}

/* ------------------------------------------------------------------------- */
/* Dividers                                                                   */
/* ------------------------------------------------------------------------- */
hr {{
    border: none !important;
    border-top: 1px solid {BORDER} !important;
    margin: 1.25rem 0 !important;
}}

/* ------------------------------------------------------------------------- */
/* Plotly charts container                                                    */
/* ------------------------------------------------------------------------- */
[data-testid="stPlotlyChart"] {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px;
    background: {BG_BODY};
    box-shadow: {SHADOW_CARD};
}}

/* ------------------------------------------------------------------------- */
/* DataFrame / data_editor                                                    */
/* ------------------------------------------------------------------------- */
[data-testid="stDataFrameResizable"] {{
    border-radius: 6px;
}}
[data-testid="stDataFrameResizable"] * {{
    font-size: 13px !important;
}}

/* ------------------------------------------------------------------------- */
/* Section pill (small category tag above each section heading)               */
/* ------------------------------------------------------------------------- */
.section-pill {{
    display: inline-block;
    background: {ACCENT_SOFT};
    color: {ACCENT};
    font-size: 10px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-right: 8px;
    vertical-align: middle;
}}

/* ------------------------------------------------------------------------- */
/* Alerts                                                                     */
/* ------------------------------------------------------------------------- */
[data-baseweb="notification"] {{
    border-radius: 6px !important;
    border: 1px solid {BORDER} !important;
    box-shadow: {SHADOW_CARD};
}}

/* ------------------------------------------------------------------------- */
/* Header toolbar                                                             */
/* ------------------------------------------------------------------------- */
header[data-testid="stHeader"] {{
    background: transparent;
}}
</style>
"""


def inject() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
