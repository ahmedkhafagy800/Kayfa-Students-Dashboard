import streamlit as st
from utils.theme import get_brand


def apply_theme(fig, height=400):
    """Apply brand theme to a Plotly figure."""
    brand = get_brand()
    fig.update_layout(
        paper_bgcolor=brand['paper_bg'],
        plot_bgcolor=brand['plot_bg'],
        font=dict(color=brand['font_color']),
        title_font=dict(color=brand['primary'], size=16),
        legend=dict(font=dict(color=brand['font_color']), bgcolor=brand['plot_bg']),
        height=height
    )
    fig.update_xaxes(
        gridcolor=brand['grid_color'],
        linecolor=brand['line_color'],
        tickfont=dict(color=brand['font_color']),
        title_font=dict(color=brand['font_color'])
    )
    fig.update_yaxes(
        gridcolor=brand['grid_color'],
        linecolor=brand['line_color'],
        tickfont=dict(color=brand['font_color']),
        title_font=dict(color=brand['font_color'])
    )
    return fig


def apply_pct_axis(fig, axis="y"):
    """Format the given axis as a percentage (assumes 0-1 fractions)."""
    if axis in ("y", "both"):
        fig.update_yaxes(tickformat=".0%")
    if axis in ("x", "both"):
        fig.update_xaxes(tickformat=".0%")
    return fig


def show_pct_labels(fig, axis="y"):
    """Show the value on top of each bar formatted as a percentage.

    axis="y" for vertical bars (value on y), axis="x" for horizontal bars
    (value on x). Defaults to "y" to match historical behavior.
    """
    template = '%{y:.1%}' if axis == "y" else '%{x:.1%}'
    fig.update_traces(texttemplate=template, textposition='outside')
    return fig


def insight(text):
    """Display an insight/tip box."""
    st.markdown(f'<div class="insight">💡 {text}</div>', unsafe_allow_html=True)


def copyright_footer(company="Kayfa", year=None):
    """Display a centered copyright line. Call once at the bottom of a page."""
    import datetime
    brand = get_brand()
    display_year = year or datetime.datetime.now().year
    st.markdown(f"""
    <div style="text-align:center; color:{brand['font_color']}; font-size:0.8rem;
                opacity:0.55; padding:16px 0 4px 0;">
        © {display_year} {company}. All rights reserved.
    </div>
    """, unsafe_allow_html=True)


def q_header(num, text, difficulty, pts):
    """Display a question header with difficulty badge and points."""
    brand = get_brand()
    colors = {"MEDIUM": "#FFA657", "HARD": "#F85149", "VERY HARD": "#D2A8FF"}
    color = colors.get(difficulty, "#4B5FFA")
    st.markdown(f"""
    <div class="q-header">
        <span style="color:{brand['primary']};font-weight:700;font-size:1rem;">Q{num}</span>
        <span style="color:{brand['font_color']};font-size:0.95rem;margin-left:10px;">{text}</span>
        <span style="background:{color}22;color:{color};border-radius:20px;
                     padding:2px 10px;font-size:0.75rem;margin-left:10px;">{difficulty}</span>
        <span style="background:{brand['primary']}22;color:{brand['primary']};border-radius:20px;
                     padding:2px 10px;font-size:0.75rem;margin-left:6px;">{pts} pts</span>
    </div>
    """, unsafe_allow_html=True)