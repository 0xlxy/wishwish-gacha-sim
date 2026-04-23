"""Global CSS injection.

Visual language modeled on https://codereview.withmartian.com/ — Ant-Design
tokens, Work Sans at 14 px base. Demarcation is done with **flat 1 px borders
and background tint**, not shadows, so stacked cards don't stack visual noise.
"""
from __future__ import annotations

import streamlit as st


# --------------------------------------------------------------------------- #
# Tokens (also consumed by viz/theme.py).
# --------------------------------------------------------------------------- #
TEXT_PRIMARY = "rgba(0, 0, 0, 0.88)"
TEXT_SECONDARY = "rgba(0, 0, 0, 0.65)"
TEXT_TERTIARY = "rgba(0, 0, 0, 0.45)"

# Three-layer background hierarchy:
#   app outer  =  white
#   sidebar    =  #FAFAFA   (one step down)
#   subtle fill =  #F7F7F7  (for KPI cards / hover zones)
BG_APP = "#FFFFFF"
BG_SIDEBAR = "#FAFAFA"
BG_SUBTLE = "#F7F7F7"

BORDER = "#E8E4E4"        # standard 1 px divider
BORDER_STRONG = "#D9D4D4"  # used sparingly — sidebar/tab separator

ACCENT = "#563FFF"
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


_CSS = f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
/* ------------------------------------------------------------------------- */
/* Base                                                                       */
/* ------------------------------------------------------------------------- */
html, body, .stApp,
[data-testid="stAppViewContainer"] > .main {{
    font-family: {FONT_STACK};
    font-size: 14px;
    line-height: 1.5;
    color: {TEXT_PRIMARY};
    background: {BG_APP};
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
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
[class*="material-icons"], [class*="material-symbols"],
[data-testid="stIconMaterial"], [data-testid*="Icon"] span {{
    font-family: "Material Symbols Rounded", "Material Symbols Outlined",
                 "Material Icons" !important;
    font-feature-settings: "liga";
}}

/* ------------------------------------------------------------------------- */
/* Main container                                                             */
/* ------------------------------------------------------------------------- */
.block-container {{
    padding-top: 1.25rem !important;
    padding-bottom: 3rem !important;
    max-width: 1320px;
    background: {BG_APP};
}}

/* ------------------------------------------------------------------------- */
/* Typography                                                                 */
/* ------------------------------------------------------------------------- */
h1 {{
    font-size: 26px !important;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    letter-spacing: -0.01em;
    margin-bottom: 0.25rem !important;
}}
h2 {{
    font-size: 17px !important;
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
/* Sidebar — gray tint creates the separator, no heavy border                 */
/* ------------------------------------------------------------------------- */
[data-testid="stSidebar"] {{
    min-width: 260px !important;
    max-width: 280px !important;
    background: {BG_SIDEBAR} !important;
    border-right: 1px solid {BORDER_STRONG} !important;
    box-shadow: none !important;
}}
[data-testid="stSidebar"] .block-container {{
    padding-top: 1rem !important;
    background: {BG_SIDEBAR} !important;
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
[data-testid="stSidebar"] hr {{
    border: none !important;
    border-top: 1px solid {BORDER} !important;
    margin: 0.75rem 0 !important;
}}

/* ------------------------------------------------------------------------- */
/* KPI metric cards — flat, no shadow; subtle tint + 1 px border              */
/* ------------------------------------------------------------------------- */
[data-testid="stMetric"] {{
    background: {BG_APP};
    border: 1px solid {BORDER};
    padding: 12px 14px;
    border-radius: 6px;
    box-shadow: none;
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
/* Inputs — flat                                                              */
/* ------------------------------------------------------------------------- */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {{
    border-radius: 6px !important;
    border: 1px solid {BORDER} !important;
    background: {BG_APP} !important;
    font-size: 13px !important;
    box-shadow: none !important;
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
/* Buttons — flat                                                             */
/* ------------------------------------------------------------------------- */
.stButton > button {{
    border-radius: 6px;
    border: 1px solid {BORDER};
    background: {BG_APP};
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 500;
    padding: 6px 14px;
    box-shadow: none;
    transition: border-color 0.15s ease, color 0.15s ease,
                background 0.15s ease;
}}
.stButton > button:hover {{
    border-color: {ACCENT} !important;
    color: {ACCENT} !important;
    background: {BG_APP};
}}
.stButton > button:active {{
    background: {ACCENT_SOFT} !important;
}}
.stButton > button[kind="primary"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #FFFFFF;
    box-shadow: none;
}}
.stButton > button[kind="primary"]:hover {{
    background: #6E5BFF !important;
    border-color: #6E5BFF !important;
    color: #FFFFFF !important;
}}

/* ------------------------------------------------------------------------- */
/* Expanders — flat, single border                                            */
/* ------------------------------------------------------------------------- */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {BG_APP};
    box-shadow: none;
    overflow: hidden;
}}
/* Streamlit wraps the body in a <details>/inner div that ships with its own
   border + radius. Null them so the outer wrapper's border is the only one. */
[data-testid="stExpander"] > details,
[data-testid="stExpander"] > details > div,
[data-testid="stExpanderDetails"],
[data-testid="stExpander"] [data-baseweb="block"] {{
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    background: transparent !important;
}}
[data-testid="stExpander"] summary {{
    padding: 10px 14px !important;
    border: none !important;
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
/* Plotly charts — flat card, single border                                   */
/* ------------------------------------------------------------------------- */
[data-testid="stPlotlyChart"] {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 6px 2px 6px;
    background: {BG_APP};
    box-shadow: none;
    overflow: hidden;
}}
[data-testid="stPlotlyChart"] > div,
[data-testid="stPlotlyChart"] .js-plotly-plot,
[data-testid="stPlotlyChart"] .plot-container {{
    border: none !important;
    box-shadow: none !important;
}}

/* ------------------------------------------------------------------------- */
/* DataFrame / data_editor — single border on outer wrapper                   */
/* ------------------------------------------------------------------------- */
[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {{
    border-radius: 6px;
    border: 1px solid {BORDER};
    box-shadow: none;
    overflow: hidden;
}}
[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"],
[data-testid="stDataEditor"] [data-testid="stDataFrameResizable"],
[data-testid="stDataFrameResizable"] {{
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}}
[data-testid="stDataFrameResizable"] * {{
    font-size: 13px !important;
}}

/* ------------------------------------------------------------------------- */
/* Section pill                                                               */
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
    box-shadow: none !important;
}}

/* ------------------------------------------------------------------------- */
/* Header toolbar                                                             */
/* ------------------------------------------------------------------------- */
header[data-testid="stHeader"] {{
    background: transparent;
    box-shadow: none;
}}
</style>
"""


def inject() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
