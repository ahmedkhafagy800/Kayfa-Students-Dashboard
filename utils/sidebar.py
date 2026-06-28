import streamlit as st
import base64
from utils.auth import logout, is_logged_in


@st.cache_data
def get_logo_base64():
    """Load logo as base64 string. Cached since the file never changes
    during the app's lifetime - avoids re-reading disk on every rerun."""
    try:
        with open("kayfaio_logo.jpg", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


def hide_page_nav():
    """Hide the auto-generated page navigation list in the sidebar.

    Used on the login screen so an unauthenticated visitor can't see
    (or click into) page names like "Overview" / "Analytics" before
    signing in. The pages are still guarded by auth.require_login(),
    but hiding the links avoids exposing page names and unnecessary
    clicks that just bounce back with a "please log in" message.
    """
    st.markdown("""
    <style>
    [data-testid="stSidebarNav"],
    section[data-testid="stSidebarNav"],
    div[data-testid="stSidebarNav"] {
        display: none !important;
        height: 0px !important;
        visibility: hidden !important;
    }
    </style>
    """, unsafe_allow_html=True)


def init_sidebar():
    """Initialize sidebar with logo and dark mode toggle."""
    # Initialize dark_mode in session state if not present
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = True

    is_dark = st.session_state.dark_mode

    # Display logo
    logo_b64 = get_logo_base64()
    if logo_b64:
        st.sidebar.markdown(
            f'<img src="data:image/jpeg;base64,{logo_b64}" width="160" '
            f'style="display:block; margin:0 auto 8px auto; filter:brightness(0) invert(1);"/>',
            unsafe_allow_html=True
        )

    # Dark mode toggle
    new_dark = st.sidebar.toggle(
        "🌙 Dark Mode" if is_dark else "☀️ Light Mode",
        value=st.session_state.dark_mode,
        key="theme_toggle"
    )
    if new_dark != st.session_state.dark_mode:
        st.session_state.dark_mode = new_dark
        st.rerun()

    # Divider
    st.sidebar.markdown("<hr style='border-color:rgba(255,255,255,0.3); margin:8px 0;'>", unsafe_allow_html=True)

    # User info + logout
    if is_logged_in():
        display_name = st.session_state.get("display_name", "User")
        st.sidebar.markdown(
            f"<p style='color:#FFFFFF; font-size:0.85rem; opacity:0.85; margin-bottom:4px;'>"
            f"👤 {display_name}</p>",
            unsafe_allow_html=True
        )
        if st.sidebar.button("🚪 Log out", use_container_width=True):
            logout()
            st.switch_page("Home.py")
