import streamlit as st
import plotly.express as px

from utils import theme, components, database, sidebar, auth

# ── Page Config ───────────────────────────────────────────────────
st.set_page_config(page_title="Overview", page_icon="👥", layout="wide")

# ── Auth Guard ────────────────────────────────────────────────────
auth.require_login()

# ── Initialize Theme & Sidebar ────────────────────────────────────
theme.apply_brand_css()
sidebar.init_sidebar()

# ── Load Data with Error Handling ─────────────────────────────────
with st.spinner("📊 Loading student demographics..."):
    df = database.load_data("master_students")

if df is None or len(df) == 0:
    st.error("❌ Unable to load student data.")
    st.stop()

brand = theme.get_brand()

# ── Header ────────────────────────────────────────────────────────
st.markdown(f"""
<div style="border-bottom:2px solid {brand['primary']}; margin-bottom:24px; padding-bottom:12px;">
    <h1 style="color:{brand['primary']}; margin:0;">👥 Students Overview</h1>
    <p style="color:{brand['font_color']}; margin:4px 0 0 0;">
        Demographics and distribution across {df['group_id'].nunique()} groups and {df['course_id'].nunique()} courses
    </p>
</div>
""", unsafe_allow_html=True)

# ── Row 1: Groups & Gender ────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    try:
        grp = df.groupby("group_id")["student_id"].count().reset_index()
        grp.columns = ["Group", "Count"]

        if len(grp) == 0:
            st.warning("⚠️ No group data available")
        else:
            largest = grp.loc[grp["Count"].idxmax()]
            smallest = grp.loc[grp["Count"].idxmin()]

            fig = px.bar(grp, x="Group", y="Count", title="Students per Group",
                         color="Group", color_discrete_sequence=brand['palette'])
            st.plotly_chart(components.apply_theme(fig), use_container_width=True)

            components.insight(f"📊 {largest['Group']} is the largest group with {largest['Count']} students, "
                               f"while {smallest['Group']} is the smallest with {smallest['Count']} — "
                               f"a {largest['Count'] - smallest['Count']}-student gap worth balancing.")
    except Exception as e:
        st.error(f"❌ Error visualizing group distribution: {str(e)}")

with col2:
    try:
        gender = df["gender"].value_counts()

        if len(gender) == 0:
            st.warning("⚠️ No gender data available")
        else:
            male_pct = gender.get("Male", 0) / len(df) * 100
            female_pct = gender.get("Female", 0) / len(df) * 100

            fig = px.pie(df, names="gender", title="Gender Distribution",
                         color_discrete_sequence=brand['palette'], hole=0.4)
            st.plotly_chart(components.apply_theme(fig), use_container_width=True)

            balance_msg = 'a relatively balanced split' if abs(
                male_pct - female_pct) < 15 else 'a notable gender gap that may warrant targeted outreach'
            components.insight(
                f"👫 Males represent {male_pct:.1f}% of students vs {female_pct:.1f}% females — {balance_msg}.")
    except Exception as e:
        st.error(f"❌ Error visualizing gender distribution: {str(e)}")

# ── Row 2: Age & City ─────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    try:
        avg_age = df["age"].mean()
        min_age = df["age"].min()
        max_age = df["age"].max()

        fig = px.histogram(df, x="age", title="Age Distribution",
                           nbins=15, color_discrete_sequence=[brand['palette'][0]])
        st.plotly_chart(components.apply_theme(fig), use_container_width=True)

        age_profile = 'young adult' if avg_age < 25 else 'mature'
        components.insight(f"🎓 Students range from {min_age} to {max_age} years old, "
                           f"with an average age of {avg_age:.1f} — indicating a predominantly {age_profile} learner base.")
    except Exception as e:
        st.error(f"❌ Error visualizing age distribution: {str(e)}")

with col4:
    try:
        city = df["city"].value_counts().reset_index()

        if len(city) == 0:
            st.warning("⚠️ No city data available")
        else:
            city.columns = ["City", "Count"]
            top_city = city.iloc[0]
            bottom_city = city.iloc[-1]

            fig = px.bar(city, x="City", y="Count", title="Students per City",
                         color="City", color_discrete_sequence=brand['palette'])
            st.plotly_chart(components.apply_theme(fig), use_container_width=True)

            components.insight(f"🌍 {top_city['City']} leads with {top_city['Count']} students, "
                               f"while {bottom_city['City']} has only {bottom_city['Count']} — "
                               f"suggesting geographic expansion opportunity in smaller cities.")
    except Exception as e:
        st.error(f"❌ Error visualizing city distribution: {str(e)}")

# ── Row 3: Difficulty Level ──────────────────────────────────────
try:
    diff = df["difficulty_level"].value_counts().reset_index()

    if len(diff) == 0:
        st.warning("⚠️ No difficulty level data available")
    else:
        diff.columns = ["Difficulty", "Count"]
        top_diff = diff.iloc[0]

        fig = px.bar(diff, x="Difficulty", y="Count", title="Students per Difficulty Level",
                     color="Difficulty", color_discrete_sequence=brand['palette'])
        st.plotly_chart(components.apply_theme(fig, height=350), use_container_width=True)

        level_profile = 'entry-level' if top_diff['Difficulty'] == 'Beginner' else top_diff['Difficulty'].lower()
        components.insight(f"📚 Most students ({top_diff['Count']}) are enrolled in {top_diff['Difficulty']} courses — "
                           f"indicating the platform's primary audience prefers {level_profile} content.")
except Exception as e:
    st.error(f"❌ Error visualizing difficulty levels: {str(e)}")

# ── Footer ────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align:center; color:{brand['font_color']}; font-size:0.85rem; opacity:0.7;">
    <p>Total Students Analyzed: <strong>{len(df):,}</strong> | Groups: <strong>{df['group_id'].nunique()}</strong> | Courses: <strong>{df['course_id'].nunique()}</strong></p>
</div>
""", unsafe_allow_html=True)
components.copyright_footer("Kayfa")