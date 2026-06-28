import streamlit as st

# ── Theme Configuration ───────────────────────────────────────────
BRAND_DARK = {
    'primary':    '#4B5FFA',
    'bg':         '#0D1117',
    'font_color': '#E6EDF3',
    'paper_bg':   '#0D1117',
    'plot_bg':    '#161B22',
    'grid_color': '#2A3A4A',
    'line_color': '#444444',
    'sidebar_bg': '#4B5FFA',
    'palette':    ['#4B5FFA', '#3FB950', '#F85149', '#D2A8FF', '#FFA657'],
    'card_bg':    '#161B22',
    'card_border': '#30363D',
    'input_bg':       '#161B22',
    'input_border':   '#30363D',
    'input_text':     '#E6EDF3',
    'button_bg':      '#4B5FFA',
    'button_text':    '#FFFFFF',
}

BRAND_LIGHT = {
    'primary':    '#4B5FFA',
    'bg':         '#F8FAFC',
    'font_color': '#1E293B',
    'paper_bg':   '#FFFFFF',
    'plot_bg':    '#F1F5F9',
    'grid_color': '#CBD5E1',
    'line_color': '#94A3B8',
    'sidebar_bg': '#4B5FFA',
    'palette':    ['#4B5FFA', '#16A34A', '#DC2626', '#7C3AED', '#D97706'],
    'card_bg':    '#FFFFFF',
    'card_border': '#BFDBFE',
    'input_bg':       '#FFFFFF',
    'input_border':   '#CBD5E1',
    'input_text':     '#1E293B',
    'button_bg':      '#4B5FFA',
    'button_text':    '#FFFFFF',
}


def get_brand():
    """Get the current brand theme based on dark_mode session state.

    NOTE: Always call this function to get the brand dict - never cache
    its result in a module-level variable, since dark_mode can change
    at any point during the session (toggle in sidebar).
    """
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = True
    return BRAND_DARK if st.session_state.dark_mode else BRAND_LIGHT


@st.cache_data
def _build_css(primary, bg, font_color, sidebar_bg, plot_bg, card_bg, card_border,
                input_bg, input_border, input_text, button_bg, button_text):
    """Build the CSS string for the given theme values. Cached so repeated
    reruns with the same theme don't rebuild the same string from scratch."""
    return f"""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], .main, .block-container {{
    background-color: {bg} !important;
    color: {font_color} !important;
}}
header {{ background-color: {bg} !important; }}
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
    background-color: {sidebar_bg} !important;
}}
[data-testid="stSidebar"] * {{ color: #FFFFFF !important; }}
h1, h2, h3, h4, h5, h6 {{ color: {primary} !important; }}
p, span, div, label, .stMarkdown {{ color: {font_color} !important; }}
hr {{ border-color: {primary} !important; opacity: 0.3; }}
.kpi-card {{
    background-color: {card_bg};
    border: 1px solid {card_border};
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    margin-bottom: 16px;
}}
.kpi-value {{
    font-size: 2rem;
    font-weight: 700;
    color: {primary};
}}
.kpi-label {{
    font-size: 0.9rem;
    color: {font_color};
    opacity: 0.75;
    margin-top: 4px;
}}
.insight {{
    background-color: {plot_bg};
    border-left: 3px solid {primary};
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.88rem;
    color: {font_color};
    margin-top: 6px;
    margin-bottom: 20px;
}}
.q-header {{
    background-color: {plot_bg};
    border: 1px solid {primary}44;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 16px;
}}

/* ── Username / Password fields ──────────────────────────────── */
[data-testid="stTextInput"] input {{
    background-color: {input_bg} !important;
    color: {input_text} !important;
    border: 1px solid {input_border} !important;
    border-radius: 8px !important;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: {primary} !important;
    box-shadow: 0 0 0 1px {primary} !important;
}}
[data-testid="stTextInput"] label {{
    color: {font_color} !important;
}}

/* ── Login button (and other form submit buttons) ───────────── */
[data-testid="stFormSubmitButton"] button {{
    background-color: {button_bg} !important;
    color: {button_text} !important;
    border: none !important;
    border-radius: 8px !important;
}}
[data-testid="stFormSubmitButton"] button:hover {{
    background-color: {button_bg} !important;
    opacity: 0.85;
}}
[data-testid="stFormSubmitButton"] button p {{
    color: {button_text} !important;
}}
</style>
"""


def apply_brand_css():
    """Apply the current theme's CSS styling to the app."""
    brand = get_brand()
    css = _build_css(
        brand['primary'], brand['bg'], brand['font_color'],
        brand['sidebar_bg'], brand['plot_bg'], brand['card_bg'], brand['card_border'],
        brand['input_bg'], brand['input_border'], brand['input_text'],
        brand['button_bg'], brand['button_text']
    )
    st.markdown(css, unsafe_allow_html=True)