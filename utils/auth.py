import streamlit as st
import hashlib
import hmac


def _hash_password(password, salt):
    """Hash a password with the given salt using SHA-256."""
    return hashlib.sha256((salt + password).encode()).hexdigest()


def _verify_password(password, salt, stored_hash):
    """Constant-time comparison to avoid timing attacks."""
    computed = _hash_password(password, salt)
    return hmac.compare_digest(computed, stored_hash)


def _get_credentials():
    """Read configured users from secrets.toml.

    Expected secrets.toml structure:

        [auth]
        salt = "some-fixed-random-string"

        [auth.users.ahmed]
        password_hash = "..."
        display_name = "Ahmed"

        [auth.users.admin]
        password_hash = "..."
        display_name = "Admin"
    """
    try:
        return st.secrets["auth"]
    except Exception:
        return None


def is_logged_in():
    """Check whether the current session is authenticated."""
    return st.session_state.get("authenticated", False)


def login(username, password):
    """Attempt to log in. Returns (success: bool, message: str)."""
    auth_config = _get_credentials()
    if auth_config is None:
        return False, "Authentication is not configured. Check secrets.toml."

    salt = auth_config.get("salt", "")
    users = auth_config.get("users", {})

    user = users.get(username)
    if user is None:
        return False, "Invalid username or password."

    if _verify_password(password, salt, user.get("password_hash", "")):
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.display_name = user.get("display_name", username)
        return True, "Login successful."

    return False, "Invalid username or password."














# def login(username, password):
#     auth_config = _get_credentials()
#     if auth_config is None:
#         return False, "Authentication is not configured. Check secrets.toml."
#
#     salt = auth_config.get("salt", "")
#
#     try:
#         user = st.secrets["auth"]["users"][username]
#     except KeyError:
#         return False, "Invalid username or password."
#
#     if _verify_password(password, salt, user.get("password_hash", "")):
#         st.session_state.authenticated = True
#         st.session_state.username = username
#         st.session_state.display_name = user.get("display_name", username)
#         return True, "Login successful."
#
#     return False, "Invalid username or password."






# def login(username, password):
#     auth_config = _get_credentials()
#     if auth_config is None:
#         return False, "Authentication is not configured. Check secrets.toml."
#
#     salt = auth_config.get("salt", "")
#
#     try:
#         user = st.secrets["auth"]["users"][username]
#     except KeyError:
#         return False, f"DEBUG: user '{username}' not found in secrets"  # ← مؤقت
#
#     computed = _hash_password(password, salt)
#     if not hmac.compare_digest(computed, user.get("password_hash", "")):
#         return False, f"DEBUG: hash mismatch. computed={computed[:10]}... expected={user.get('password_hash','')[:10]}..."  # ← مؤقت
#
#     st.session_state.authenticated = True
#     st.session_state.username = username
#     st.session_state.display_name = user.get("display_name", username)
#     return True, "Login successful."





def logout():
    """Clear the authenticated session."""
    for key in ("authenticated", "username", "display_name"):
        st.session_state.pop(key, None)


def require_login():
    """Guard for protected pages. Stops the page render and points the
    user to the login page if they are not authenticated.

    Usage: call this as the first line after st.set_page_config() on
    every protected page.
    """
    if not is_logged_in():
        # Hide the auto-generated page nav list (Home/Overview/Analytics)
        # so a visitor who opens this page's URL directly doesn't see or
        # click into other page names while still logged out. This is a
        # UX/discoverability measure, not the actual access control - the
        # st.stop() below is what actually blocks rendering of the page.
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

        st.warning("🔒 Please log in to view this page.")
        if st.button("Go to Login"):
            st.switch_page("Home.py")
        st.stop()