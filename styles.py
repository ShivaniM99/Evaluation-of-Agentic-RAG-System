# styles.py
# All CSS for ABC Technology ATLAS — imported by app.py
# Split into logical sections for maintainability

# ── DESIGN TOKENS ─────────────────────────────────────────────────────────────
# Change values here to retheme the entire app

TOKENS = """
:root {
    --red:        #c00000;
    --red-dark:   #990000;
    --red-light:  #fff0f0;
    --bg:         #f4f4f4;
    --surface:    #ffffff;
    --text:       #1a1a1a;
    --text-muted: #666666;
    --text-faint: #999999;
    --border:     #e0e0e0;
    --radius-sm:  8px;
    --radius-md:  12px;
    --radius-lg:  20px;
    --radius-pill:32px;
    --shadow-sm:  0 1px 4px rgba(0,0,0,0.06);
    --shadow-md:  0 2px 12px rgba(0,0,0,0.08);
    --shadow-lg:  0 4px 24px rgba(0,0,0,0.12);
    --max-w:      720px;
    --font-body:  'DM Sans', sans-serif;
    --font-mono:  'DM Mono', monospace;
}
"""

# ── GLOBAL RESET ──────────────────────────────────────────────────────────────
GLOBAL = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: var(--font-body);
    background-color: var(--bg) !important;
    color: var(--text);
}

/* Force background on all Streamlit root containers */
.stApp,
.stApp > div,
div[data-testid="stAppViewContainer"],
div[data-testid="stAppViewBlockContainer"],
section[data-testid="stMain"],
section[data-testid="stSidebar"] + div {
    background-color: var(--bg) !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Remove default padding */
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}
.appview-container > section > div:first-child {
    padding-top: 0 !important;
}
div[data-testid="stAppViewContainer"] {
    padding-top: 0 !important;
}
div[data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

/* Kill the white strip — column top padding Streamlit injects */
div[data-testid="stHorizontalBlock"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
    align-items: center !important;
}
div[data-testid="column"] {
    padding-top: 0 !important;
}

/* Remove label gap above text input */
div[data-testid="stTextInput"] {
    margin-top: 0 !important;
    padding-top: 0 !important;
}
div[data-testid="stTextInput"] label {
    display: none !important;
}
div[data-testid="stTextInput"] > div {
    margin-top: 0 !important;
}
"""

# ── NAV BAR ───────────────────────────────────────────────────────────────────
NAV = """
.abc-nav {
    background-color: var(--red);
    padding: 14px 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.abc-nav .logo {
    font-size: 18px;
    font-weight: 700;
    color: white;
    letter-spacing: 0.06em;
}
.abc-nav .logo span {
    color: rgba(255,255,255,0.6);
    font-weight: 300;
}
.abc-nav .tagline {
    font-size: 10px;
    color: rgba(255,255,255,0.65);
    letter-spacing: 0.18em;
    text-transform: uppercase;
}
"""

# ── HERO ──────────────────────────────────────────────────────────────────────
HERO = """
.hero {
    background: linear-gradient(135deg, #111111 0%, #222222 55%, #c00000 100%);
    padding: 48px 40px 40px 40px;
    text-align: center;
}
.hero h1 {
    font-size: clamp(24px, 3vw, 40px);
    font-weight: 700;
    color: white;
    margin: 0 0 10px 0;
    letter-spacing: -0.02em;
    line-height: 1.2;
}
.hero h1 .hl { color: #ff6b6b; font-weight: 800; }
.hero .subtitle {
    font-size: 11px;
    color: rgba(255,255,255,0.45);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: 10px;
}
.hero-pills {
    margin-top: 18px;
    display: flex;
    gap: 8px;
    justify-content: center;
    flex-wrap: wrap;
}
.hero-pill {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.7);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 10px;
    letter-spacing: 0.08em;
}
"""

# ── PAGE CONTENT WRAPPER ──────────────────────────────────────────────────────
# All page content sits inside a centered column
# This replaces the broken .centered div approach
LAYOUT = """
.page-body {
    max-width: var(--max-w);
    margin: 0 auto;
    padding: 32px 24px 60px 24px;
}
"""

# ── INPUT AREA ────────────────────────────────────────────────────────────────
# The input uses Streamlit's native text_area + button
# We style the container, not try to float things inside columns
INPUT = """
.input-wrapper {
    background: var(--surface);
    border-radius: var(--radius-pill);
    border: 1.5px solid var(--border);
    padding: 14px 18px;
    box-shadow: var(--shadow-md);
    transition: border-color 0.2s, box-shadow 0.2s;
    margin-bottom: 12px;
}
.input-wrapper:focus-within {
    border-color: var(--red);
    box-shadow: 0 2px 20px rgba(192,0,0,0.12);
}

/* Text input inside wrapper — strip all native styling */
.input-wrapper .stTextInput > div {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important;
}
.input-wrapper .stTextInput input {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    font-size: 15px !important;
    font-family: var(--font-body) !important;
    color: var(--text) !important;
    padding: 4px 0 !important;
    outline: none !important;
}
.input-wrapper .stTextInput input::placeholder {
    color: var(--text-faint) !important;
}

/* Ask button */
div[data-testid="stButton"] > button[kind="primary"] {
    background: var(--red) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-pill) !important;
    padding: 10px 20px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    font-family: var(--font-body) !important;
    letter-spacing: 0.03em !important;
    cursor: pointer !important;
    transition: background 0.2s !important;
    width: 100% !important;
    height: 42px !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: var(--red-dark) !important;
}

/* Mic button — circular ghost */
div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important;
    border: 1.5px solid var(--border) !important;
    color: var(--text-muted) !important;
    border-radius: 50% !important;
    padding: 0 !important;
    font-size: 16px !important;
    font-family: var(--font-body) !important;
    width: 42px !important;
    height: 42px !important;
    min-width: 42px !important;
    transition: all 0.2s !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    border-color: var(--red) !important;
    color: var(--red) !important;
    background: var(--red-light) !important;
}
"""

# ── STATUS / AGENT TRACE ──────────────────────────────────────────────────────
AGENT = """
div[data-testid="stStatus"] {
    border-radius: var(--radius-md) !important;
    border: 1px solid #f0c8c8 !important;
    background: #fff8f8 !important;
    box-shadow: 0 2px 12px rgba(192,0,0,0.07) !important;
    margin: 16px 0 !important;
    border-left: 3px solid var(--red) !important;
}
"""

# ── ANSWER CARD ───────────────────────────────────────────────────────────────
ANSWER = """
.answer-card {
    background: var(--surface);
    border-radius: var(--radius-md);
    border-left: 4px solid var(--red);
    padding: 24px 28px;
    box-shadow: var(--shadow-md);
    margin: 16px 0 24px 0;
    font-size: 15px;
    line-height: 1.8;
    color: var(--text);
}
.answer-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--red);
    margin-bottom: 10px;
}
"""

# ── CITATIONS ─────────────────────────────────────────────────────────────────
CITATIONS = """
.citations-label {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--text);
    margin: 32px 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--red);
    display: block;
}

/* Expanders */
div[data-testid="stExpander"] {
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
    box-shadow: var(--shadow-sm) !important;
    margin-bottom: 10px !important;
    margin-top: 4px !important;
}
div[data-testid="stExpander"] summary {
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 10px 14px !important;
}

.chunk-breadcrumb {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-faint);
    margin-bottom: 8px;
}
.chunk-body {
    font-size: 13px;
    color: #333;
    line-height: 1.7;
    background: #f8f8f8;
    border-radius: var(--radius-sm);
    padding: 12px 14px;
    white-space: pre-wrap;
}

/* Doc type badges */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-right: 6px;
    vertical-align: middle;
}
.badge-procedure     { background: #fff3cd; color: #856404; }
.badge-scenario      { background: #cce5ff; color: #004085; }
.badge-release-notes { background: #d4edda; color: #155724; }
.badge-unknown       { background: #e2e3e5; color: #383d41; }
"""

# ── ALERTS ────────────────────────────────────────────────────────────────────
ALERTS = """
div[data-testid="stAlert"] {
    border-radius: var(--radius-sm) !important;
    margin: 8px 0 !important;
}
"""

# ── FOOTER ────────────────────────────────────────────────────────────────────
FOOTER = """
.abc-footer {
    background: #111;
    color: rgba(255,255,255,0.35);
    text-align: center;
    padding: 20px;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 60px;
}
"""

# ── COMPOSE ALL ───────────────────────────────────────────────────────────────
# Single function to inject — call once at top of app.py
def inject_styles():
    import streamlit as st
    css = "\n".join([
        TOKENS,
        GLOBAL,
        NAV,
        HERO,
        LAYOUT,
        INPUT,
        AGENT,
        ANSWER,
        CITATIONS,
        ALERTS,
        FOOTER,
    ])
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)