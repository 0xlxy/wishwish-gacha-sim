"""Global CSS injection for a denser, cleaner Streamlit layout."""
from __future__ import annotations

import streamlit as st


_CSS = """
<style>
/* Base typography — scoped carefully so Material Icons still render */
html, body {
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI",
                 Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
.stMarkdown, .stText, .stAlert, .stCaption, .stMetric, .stTabs,
.stButton > button, .stTextInput, .stNumberInput, .stSelectbox,
.stSlider, .stDataEditor, .stDataFrame, p, span, label, h1, h2, h3, h4, h5, h6 {
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI",
                 Helvetica, Arial, sans-serif !important;
    letter-spacing: -0.005em;
}
code, pre, kbd {
    font-family: "JetBrains Mono", "SF Mono", ui-monospace, Menlo, monospace !important;
}
/* Material icons must keep their own font. */
[class*="material-icons"], [class*="material-symbols"],
[data-testid="stIconMaterial"], [data-testid*="Icon"] {
    font-family: "Material Symbols Rounded", "Material Symbols Outlined",
                 "Material Icons" !important;
    font-feature-settings: "liga";
}

/* Tighter main-area padding */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px;
}

/* Title sizing */
h1 { font-size: 1.75rem !important; font-weight: 650; letter-spacing: -0.02em; }
h2 { font-size: 1.15rem !important; font-weight: 600; letter-spacing: -0.01em; margin-top: 1.4rem !important; }
h3 { font-size: 1rem !important; font-weight: 600; }
h4 { font-size: 0.92rem !important; font-weight: 600; color: #374151; }

/* Captions */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #6B7280 !important;
    font-size: 0.82rem !important;
}

/* Metric cards: tighter */
[data-testid="stMetric"] {
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    padding: 0.75rem 0.9rem;
    border-radius: 8px;
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #6B7280 !important;
    font-weight: 500;
}
[data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
    font-weight: 650;
    color: #111827;
}

/* Sidebar */
[data-testid="stSidebar"] {
    min-width: 260px !important;
    max-width: 280px !important;
    background: #FAFAFA;
    border-right: 1px solid #E5E7EB;
}
[data-testid="stSidebar"] .block-container {
    padding-top: 1rem !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2 {
    font-size: 0.95rem !important;
    font-weight: 600;
    letter-spacing: 0;
}

/* Tighter expanders */
.streamlit-expanderHeader {
    font-size: 0.86rem !important;
    font-weight: 500;
}
[data-testid="stExpander"] {
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    background: #FFFFFF;
}

/* Dividers: subtler */
hr {
    margin: 1.2rem 0 !important;
    border-color: #EEF0F3 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    border-bottom: 1px solid #E5E7EB;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.9rem;
    padding: 0.5rem 0.25rem;
}

/* Data editor: modest compaction */
[data-testid="stDataFrameResizable"] * {
    font-size: 0.85rem !important;
}

/* Primary button */
.stButton > button[kind="primary"] {
    background: #111827;
    color: #FFFFFF;
    border: 1px solid #111827;
    border-radius: 6px;
    font-weight: 500;
}
.stButton > button[kind="primary"]:hover {
    background: #1F2937;
    border-color: #1F2937;
}
.stButton > button {
    border-radius: 6px;
    font-size: 0.85rem;
}

/* Plotly chart container */
[data-testid="stPlotlyChart"] {
    border: 1px solid #EEF0F3;
    border-radius: 8px;
    padding: 0.25rem;
    background: #FFFFFF;
}

/* Narrative / markdown blocks */
.stMarkdown p { line-height: 1.5; }

/* Alert / info callouts */
[data-baseweb="notification"] {
    border-radius: 8px !important;
}

/* Section label pill */
.section-pill {
    display: inline-block;
    background: #EEF2FF;
    color: #4338CA;
    font-size: 0.68rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-right: 6px;
    vertical-align: middle;
}
</style>
"""


def inject() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
