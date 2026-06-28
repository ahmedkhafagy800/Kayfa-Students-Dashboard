import streamlit as st
from utils import theme, components, database, sidebar, auth

# ── Page Config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Kayfa Dashboard",
    page_icon="📊",
    layout="wide"
)

theme.apply_brand_css()
brand = theme.get_brand()


# ════════════════════════════════════════════════════════════════
# NOT LOGGED IN → show login form, stop here
# ════════════════════════════════════════════════════════════════
if not auth.is_logged_in():
    sidebar.hide_page_nav()
    sidebar.init_sidebar()

    logo_b64 = sidebar.get_logo_base64()
    logo_html = (
                    f'<img src="data:image/jpeg;base64,{logo_b64}" width="290" '
                    f'style="display:block; margin:-130px auto -120px auto;"/>'
        if logo_b64 else ""
    )

    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        st.markdown(f"""
        <div style="text-align:center; margin-top:60px; margin-bottom:24px;">
            {logo_html}
            <h1 style="color:{brand['primary']}; margin:0;">Kayfa Dashboard</h1>
            <p style="color:{brand['font_color']}; opacity:0.75; margin-top:6px;">
                Sign in to view student analytics
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    success, message = auth.login(username, password)
                    if success:
                        st.rerun()
                    else:
                        st.error(message)

        components.copyright_footer("Kayfa")

    st.stop()


# ════════════════════════════════════════════════════════════════
# LOGGED IN → show the dashboard home page
# ════════════════════════════════════════════════════════════════
sidebar.init_sidebar()

# ── Load Data ─────────────────────────────────────────────────────
df = database.load_data("master_students")
if df is None or len(df) == 0:
    st.error("❌ Unable to load student data.")
    st.stop()

# ── Header ────────────────────────────────────────────────────────
logo_b64 = sidebar.get_logo_base64()
logo_html = (
    f'<img src="data:image/jpeg;base64,{logo_b64}" width="180"/>'
    if logo_b64 else ""
)

st.markdown(f"""
<div style="display:flex; align-items:center; padding:16px 0 24px 0;
            border-bottom:2px solid {brand['primary']}; margin-bottom:32px;">
    {logo_html}
    <div style="margin-left:20px;">
        <h1 style="margin:0; color:{brand['primary']}; font-size:2.2rem;">
            Kayfa Learning Dashboard
        </h1>
        <p style="margin:6px 0 0 0; color:{brand['font_color']}; font-size:1rem;">
            Student performance & engagement analytics — powered by MongoDB Atlas
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── KPI Cards ─────────────────────────────────────────────────────
total_students = len(df)
avg_grade      = df["avg_grade"].mean() if "avg_grade" in df.columns else float("nan")
avg_attendance = df["attendance_rate"].mean() if "attendance_rate" in df.columns else float("nan")
avg_late       = df["late_submission_rate"].mean() if "late_submission_rate" in df.columns else float("nan")
total_groups   = df["group_id"].nunique() if "group_id" in df.columns else 0
total_courses  = df["course_id"].nunique() if "course_id" in df.columns else 0


def pd_isna(value):
    import math
    try:
        return value is None or math.isnan(value)
    except TypeError:
        return False


def fmt(value, suffix=""):
    """Format a numeric KPI value, showing 'N/A' instead of 'nan' when missing."""
    if pd_isna(value):
        return "N/A"
    return f"{value:{suffix}}"


col1, col2, col3, col4, col5, col6 = st.columns(6)

for col, icon, value, label in [
    (col1, "👥", f"{total_students:,}",            "Total Students"),
    (col2, "📚", f"{total_courses}",                "Courses"),
    (col3, "🏫", f"{total_groups}",                 "Groups"),
    (col4, "🎯", fmt(avg_grade, ".1f"),              "Avg Grade"),
    (col5, "✅", fmt(avg_attendance, ".1%"),         "Attendance Rate"),
    (col6, "⏰", fmt(avg_late, ".1%"),               "Late Submissions"),
]:
    col.markdown(f"""
    <div class="kpi-card">
        <div style="font-size:1.8rem;">{icon}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Divider ───────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)

# ── Navigation Cards ──────────────────────────────────────────────
st.markdown(f"<h3 style='color:{brand['primary']}'>🧭 Navigate</h3>", unsafe_allow_html=True)

nav1, nav2 = st.columns(2)

with nav1:
    st.markdown(f"""
    <div class="kpi-card" style="text-align:left; padding:24px;">
        <div style="font-size:2rem;">👥</div>
        <div style="font-size:1.2rem; font-weight:600; color:{brand['primary']}; margin:8px 0 4px;">
            Overview
        </div>
        <div style="color:{brand['font_color']}; font-size:0.9rem;">
            Student demographics — age, gender, city, group distribution
        </div>
    </div>
    """, unsafe_allow_html=True)

with nav2:
    st.markdown(f"""
    <div class="kpi-card" style="text-align:left; padding:24px;">
        <div style="font-size:2rem;">📈</div>
        <div style="font-size:1.2rem; font-weight:600; color:{brand['primary']}; margin:8px 0 4px;">
            Analytics
        </div>
        <div style="color:{brand['font_color']}; font-size:0.9rem;">
            Answer business questions which help to make right decision
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
components.copyright_footer("Kayfa")


