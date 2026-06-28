import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re
from utils import theme, components, database, sidebar, auth

# ── Page Config ───────────────────────────────────────────────────
st.set_page_config(page_title="Analytics", page_icon="📈", layout="wide")

# ── Auth Guard ────────────────────────────────────────────────────
auth.require_login()

# ── Initialize Theme & Sidebar ────────────────────────────────────
theme.apply_brand_css()
sidebar.init_sidebar()

# ── Load Data ─────────────────────────────────────────────────────
with st.spinner("📊 Loading analytics data..."):
    df          = database.load_data("master_students")
    grades      = database.load_collection("grades")
    attendance  = database.load_collection("attendance")
    performance = database.load_collection("performance")
    event       = database.load_data("event")
    submissions = database.load_data("submissions")
    groups      = database.load_data("groups")
    courses     = database.load_collection("courses")

if df is None or len(df) == 0:
    st.error("❌ Unable to load core student data (master_students). Cannot continue.")
    st.stop()

brand = theme.get_brand()

# Centralized visibility into what's missing, instead of failing silently
# question-by-question deep in the page.
_collections = {
    "grades": grades, "attendance": attendance, "performance": performance,
    "event": event, "submissions": submissions, "groups": groups, "courses": courses,
}
_missing = [name for name, data in _collections.items() if data is None]
if _missing:
    st.warning(f"⚠️ Some collections are unavailable: {', '.join(_missing)}. "
               f"Related questions below will be skipped.")

# ── Header ────────────────────────────────────────────────────────
st.markdown(f"""
<div style="border-bottom:2px solid {brand['primary']}; margin-bottom:24px; padding-bottom:12px;">
    <h1 style="color:{brand['primary']}; margin:0;">📈 Analytics & Insights</h1>
    <p style="color:{brand['font_color']}; margin:4px 0 0 0;">
    Answer business questions which help to make right decision
    </p>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# Shared helpers — computed once, reused across questions instead
# of being recomputed (and re-derived inconsistently) in each one.
# ════════════════════════════════════════════════════════════════

@st.cache_data
def compute_attendance_per_student(_attendance):
    """Per-student attendance rate from the attendance collection."""
    return (
        _attendance
        .groupby("student_id")["status"]
        .apply(lambda x: (x == "attended").mean())
        .reset_index()
        .rename(columns={"status": "attendance_rate"})
    )


@st.cache_data
def compute_grade_per_student(_grades):
    """Per-student average score from the grades collection."""
    return (
        _grades
        .groupby("student_id")["score"]
        .mean()
        .reset_index()
        .rename(columns={"score": "avg_grade"})
    )


@st.cache_data
def compute_active_days_per_student(_event):
    """Per-student count of distinct active days from the event collection."""
    ev = _event.copy()
    ev["date"] = pd.to_datetime(ev["event_datetime"]).dt.date
    return (
        ev.groupby("student_id")["date"]
        .nunique()
        .reset_index(name="active_days")
    )


@st.cache_data
def compute_failed_concepts(_performance, threshold=50):
    """Per-student count of distinct concepts failed (score_pct < threshold)."""
    return (
        _performance[_performance["score_pct"] < threshold]
        .groupby("student_id")["concept_id"]
        .nunique()
        .reset_index(name="failed_concepts")
    )


def get_date_col(frame, candidates):
    """Return the first candidate column name present in frame, or None."""
    for c in candidates:
        if c in frame.columns:
            return c
    return None


# Precompute shared aggregates once, only if their source data is present.
attendance_per_student = compute_attendance_per_student(attendance) if attendance is not None else None
grade_per_student = compute_grade_per_student(grades) if grades is not None else None
active_days_per_student = compute_active_days_per_student(event) if event is not None else None
failed_concepts = compute_failed_concepts(performance) if performance is not None else None


# ══════════════════════════════════════════════════════════════════
# Q1: Attendance by Group
# ══════════════════════════════════════════════════════════════════
components.q_header(1, "What is the attendance rate per group, and which groups sit well below the platform average?",
                    "MEDIUM", 4)

try:
    if attendance is not None and groups is not None:
        attendance_by_group = (
            attendance
            .groupby("group_id")["status"]
            .apply(lambda x: (x == "attended").mean())
            .reset_index()
            .rename(columns={"status": "attendance_rate"})
        )

        attendance_by_group = attendance_by_group.merge(
            groups[["group_id", "group_name", "instructor", "course_id"]],
            on="group_id",
            how="left"
        )

        platform_avg = attendance["status"].eq("attended").mean()
        attendance_by_group["below_average"] = attendance_by_group["attendance_rate"] < platform_avg
        attendance_by_group = attendance_by_group.sort_values("attendance_rate")

        fig = px.bar(
            attendance_by_group,
            x="group_name",
            y="attendance_rate",
            color="below_average",
            color_discrete_map={True: "#e74c3c", False: "#3498db"},
            text=attendance_by_group["attendance_rate"].apply(lambda x: f"{x:.1%}"),
            title="Attendance Rate per Group vs Platform Average",
            labels={"attendance_rate": "Attendance Rate", "group_name": "Group", "below_average": "Below Average"},
            hover_data=["instructor", "course_id"]
        )
        fig.add_hline(y=platform_avg, line_dash="dash", line_color="black",
                      annotation_text=f"Platform Avg: {platform_avg:.1%}", annotation_position="top right")
        fig.update_traces(textposition="outside")
        fig.update_layout(height=550, yaxis_tickformat=".0%", showlegend=True)
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        below_avg = attendance_by_group[attendance_by_group["below_average"]]
        worst = attendance_by_group.loc[attendance_by_group["attendance_rate"].idxmin()]
        components.insight(
            f"Platform average attendance is {platform_avg:.1%}. "
            f"{len(below_avg)} group(s) fall below average. "
            f"{worst['group_name']} has the lowest rate at {worst['attendance_rate']:.1%}."
        )
    else:
        st.info("Attendance or Groups data not available.")
except Exception as e:
    st.info(f"Attendance by group not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q2: Average Score by Assessment Type
# ══════════════════════════════════════════════════════════════════
components.q_header(2, "How are scores distributed by assessment type? Where is performance most volatile?",
                    "MEDIUM", 4)

try:
    if grades is not None:
        volatility_stats = grades.groupby("type")["score"].agg(
            mean="mean", std="std"
        ).reset_index()
        stats_sorted = volatility_stats.sort_values("mean", ascending=False)
        overall_avg = grades["score"].mean()

        fig = px.bar(
            stats_sorted, x="type", y="mean", color="type",
            text=stats_sorted["mean"].apply(lambda x: f"{x:.0f}%"),
            title="Average Score by Assessment Type",
            labels={"mean": "Average Score (%)", "type": "Assessment Type"},
            color_discrete_sequence=brand["palette"]
        )
        fig.add_hline(y=overall_avg, line_dash="dash", line_color="gray",
                      annotation_text=f"Overall Avg: {overall_avg:.0f}%", annotation_position="top right")
        fig.update_traces(textposition="outside", textfont_size=16)
        fig.update_layout(height=500, showlegend=False, font=dict(size=14), yaxis_range=[0, 100])
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        volatile = volatility_stats.loc[volatility_stats["std"].idxmax(), "type"]
        components.insight(f"'{volatile}' assessments show the highest score variance — "
                           f"indicating inconsistent student performance on this type.")
    else:
        st.info("grades collection not found in Atlas.")
except Exception as e:
    st.info(f"grades collection not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q3: Grade Distribution by Course
# ══════════════════════════════════════════════════════════════════
components.q_header(3, "Which course has the highest and lowest average grade, and how does grade spread differ?",
                    "MEDIUM", 5)

try:
    if grades is not None and courses is not None:
        course_grades = (
            grades
            .groupby("course_id")["score"]
            .agg(avg_grade="mean", std_grade="std", n_assessments="count")
            .reset_index()
        )

        course_grades = course_grades.merge(
            courses[["course_id", "course_name", "category", "difficulty_level"]],
            on="course_id", how="left"
        ).sort_values("avg_grade", ascending=False)

        overall_avg_g = grades["score"].mean()

        fig = px.bar(
            course_grades,
            x="course_name", y="avg_grade", color="difficulty_level",
            text=course_grades["avg_grade"].apply(lambda x: f"{x:.1f}%"),
            title="Average Grade by Course",
            labels={"avg_grade": "Average Grade (%)", "course_name": "Course"},
            color_discrete_sequence=brand["palette"]
        )
        fig.add_hline(y=overall_avg_g, line_dash="dash", line_color="black",
                      annotation_text=f"Overall Avg: {overall_avg_g:.1f}%", annotation_position="top right")
        fig.update_traces(textposition="outside")
        fig.update_layout(height=550)
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        best  = course_grades.loc[course_grades["avg_grade"].idxmax()]
        worst = course_grades.loc[course_grades["avg_grade"].idxmin()]
        components.insight(
            f"'{best['course_name']}' leads with {best['avg_grade']:.1f}% avg grade "
            f"(std: {best['std_grade']:.1f}), "
            f"while '{worst['course_name']}' scores lowest at {worst['avg_grade']:.1f}% "
            f"(std: {worst['std_grade']:.1f}) — "
            f"a {best['avg_grade'] - worst['avg_grade']:.1f} point gap suggesting curriculum difficulty differences."
        )
    else:
        st.info("Grades or Courses data not available.")
except Exception as e:
    st.info(f"Course grades not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q4: Attendance Bands vs Grade
# ══════════════════════════════════════════════════════════════════
components.q_header(4,
                    "Is there a relationship between attendance rate and average grade? Quantify and show the trend.",
                    "HARD", 6)

try:
    if attendance_per_student is not None and grade_per_student is not None:
        student_perf = attendance_per_student.merge(grade_per_student, on="student_id", how="inner")

        def attendance_band(rate):
            if rate < 0.60:
                return "Low (<60%)"
            elif rate < 0.80:
                return "Medium (60-80%)"
            else:
                return "High (80%+)"

        student_perf["attendance_band"] = student_perf["attendance_rate"].apply(attendance_band)

        band_order = ["Low (<60%)", "Medium (60-80%)", "High (80%+)"]
        band_summary_att = (
            student_perf
            .groupby("attendance_band")["avg_grade"]
            .agg(avg_grade_in_band="mean", n_students="count")
            .reset_index()
        )
        band_summary_att["attendance_band"] = pd.Categorical(
            band_summary_att["attendance_band"], categories=band_order, ordered=True
        )
        band_summary_att = band_summary_att.sort_values("attendance_band")

        fig = px.bar(
            band_summary_att, x="attendance_band", y="avg_grade_in_band",
            text=band_summary_att["avg_grade_in_band"].apply(lambda x: f"{x:.1f}%"),
            color="attendance_band",
            color_discrete_map={"Low (<60%)": "#e74c3c", "Medium (60-80%)": "#f39c12", "High (80%+)": "#27ae60"},
            title="Average Grade by Attendance Level",
            labels={"avg_grade_in_band": "Average Grade (%)", "attendance_band": "Attendance Level"},
        )
        fig.update_traces(textposition="outside", textfont_size=16)
        fig.update_layout(height=500, showlegend=False, font=dict(size=14), yaxis_range=[0, 100])
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        corr = student_perf["attendance_rate"].corr(student_perf["avg_grade"])
        strength = "a strong positive relationship" if corr > 0.5 else \
                   "a moderate positive relationship" if corr > 0.3 else "a weak relationship"
        components.insight(f"Pearson correlation = {corr:.2f} — {strength} "
                           f"between attending sessions and scoring higher grades.")
    else:
        st.info("Attendance or Grades data not available.")
except Exception as e:
    st.info(f"Attendance vs grade analysis not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q5: Engagement vs Academic Performance
# ══════════════════════════════════════════════════════════════════
components.q_header(5, "Does engagement (login frequency and total video-watch time) relate to academic performance?",
                    "HARD", 6)

try:
    if event is not None and grades is not None:
        engagement_per_student = (
            event
            .groupby("student_id")
            .agg(
                total_events=("event_id", "count"),
                total_duration_minutes=("duration_seconds", lambda x: x.sum() / 60),
                active_days=("event_datetime", lambda x: pd.to_datetime(x).dt.date.nunique())
            )
            .reset_index()
        )

        engagement_perf = engagement_per_student.merge(grade_per_student, on="student_id", how="inner")

        engagement_perf["engagement_band"] = pd.qcut(
            engagement_perf["active_days"], q=3, labels=["Low", "Medium", "High"], duplicates="drop"
        )

        band_summary = (
            engagement_perf
            .groupby("engagement_band", observed=True)["avg_grade"]
            .agg(avg_grade_in_band="mean", n_students="count")
            .reset_index()
        )

        fig = px.bar(
            band_summary,
            x="engagement_band", y="avg_grade_in_band",
            text=band_summary["avg_grade_in_band"].apply(lambda x: f"{x:.1f}%"),
            color="engagement_band",
            color_discrete_map={"Low": "#e74c3c", "Medium": "#f39c12", "High": "#27ae60"},
            title="Average Grade by Engagement Level (Active Days)",
            labels={"avg_grade_in_band": "Average Grade (%)", "engagement_band": "Engagement Level"},
            category_orders={"engagement_band": ["Low", "Medium", "High"]}
        )
        fig.update_traces(textposition="outside", textfont_size=16)
        fig.update_layout(height=500, showlegend=False, font=dict(size=14), yaxis_range=[0, 100])
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        corr_events   = engagement_perf["total_events"].corr(engagement_perf["avg_grade"])
        corr_duration = engagement_perf["total_duration_minutes"].corr(engagement_perf["avg_grade"])
        corr_days     = engagement_perf["active_days"].corr(engagement_perf["avg_grade"])

        trend_msg = "More active students tend to score higher." if corr_days > 0.3 else \
                    "Engagement alone does not strongly predict grades — quality may matter more than quantity."
        components.insight(
            f"Correlations with avg grade — "
            f"Active Days: {corr_days:.2f} | "
            f"Total Events: {corr_events:.2f} | "
            f"Watch Time: {corr_duration:.2f}. {trend_msg}"
        )
    else:
        st.info("Event or Grades data not available.")
except Exception as e:
    st.info(f"Engagement analysis not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q6: Concept Failure Rates
# ══════════════════════════════════════════════════════════════════
components.q_header(6, "Which concepts have the highest failure rate, and which courses do they belong to?", "HARD", 6)

try:
    if grades is not None:
        course_fail = (
            grades.groupby("course_id")
            .agg(fail_rate=("score", lambda x: (x < 60).mean()))
            .reset_index()
        )
        if courses is not None and "course_name" in courses.columns:
            course_fail = course_fail.merge(courses[["course_id", "course_name"]], on="course_id", how="left")
        else:
            course_fail["course_name"] = course_fail["course_id"]
        course_fail = course_fail.sort_values("fail_rate", ascending=False)

        fig1 = px.bar(
            course_fail, x="course_name", y="fail_rate",
            text=course_fail["fail_rate"].apply(lambda x: f"{x:.0%}"),
            color="fail_rate",
            color_continuous_scale=["#27ae60", "#f39c12", "#e74c3c"],
            title="Failure Rate by Course",
            labels={"fail_rate": "Failure Rate", "course_name": "Course"},
        )
        fig1.update_traces(textposition="outside", textfont_size=15)
        fig1.update_layout(height=500, font=dict(size=13), yaxis_tickformat=".0%",
                           yaxis_range=[0, 1], coloraxis_showscale=False)
        components.apply_theme(fig1)
        st.plotly_chart(fig1, use_container_width=True)

        title_col = "assessment_title" if "assessment_title" in grades.columns else \
                    ("title" if "title" in grades.columns else "type")

        concept_stats = (
            grades.groupby([title_col, "course_id"])
            .agg(fail_rate=("score", lambda x: (x < 60).mean()), total_attempts=("score", "count"))
            .reset_index()
        )
        if courses is not None and "course_name" in courses.columns:
            concept_stats = concept_stats.merge(courses[["course_id", "course_name"]], on="course_id", how="left")
        else:
            concept_stats["course_name"] = concept_stats["course_id"]
        concept_stats.rename(columns={title_col: "assessment_title"}, inplace=True)

        dominant_course = concept_stats.groupby("course_name")["fail_rate"].mean().idxmax()
        others = concept_stats[
            (concept_stats["course_name"] != dominant_course) &
            (concept_stats["total_attempts"] >= min(30, concept_stats["total_attempts"].quantile(0.25)))
        ].sort_values("fail_rate", ascending=False).head(10).copy()
        others["label"] = others["assessment_title"] + " — " + others["course_name"]

        fig2 = px.bar(
            others, x="fail_rate", y="label", orientation="h", color="course_name",
            text=others["fail_rate"].apply(lambda x: f"{x:.0%}"),
            title=f"Top Failure Rates — Excluding {dominant_course}",
            labels={"fail_rate": "Failure Rate", "label": ""},
            color_discrete_sequence=brand["palette"]
        )
        fig2.update_traces(textposition="outside", textfont_size=14)
        fig2.update_layout(height=500, font=dict(size=13), xaxis_tickformat=".0%",
                           yaxis={"categoryorder": "total ascending"})
        components.apply_theme(fig2)
        st.plotly_chart(fig2, use_container_width=True)

        worst_course = course_fail.iloc[0]
        components.insight(f"'{worst_course['course_name']}' has the highest failure rate at {worst_course['fail_rate']:.0%} — "
                           f"this is the biggest curriculum weak spot.")
    else:
        st.info("grades collection not found.")
except Exception as e:
    st.info(f"grades collection not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q7: Mastery Trend Over Time (Weakest Concept)
# ══════════════════════════════════════════════════════════════════
components.q_header(7,
                    "For the weakest concept, how does cohort mastery change over time across successive assessments?",
                    "HARD", 6)

try:
    if grades is not None:
        title_col = "assessment_title" if "assessment_title" in grades.columns else \
                    ("title" if "title" in grades.columns else "type")

        fail_rate_by_course = grades.groupby("course_id")["score"].apply(lambda x: (x < 60).mean())
        dominant_course_id = fail_rate_by_course.idxmax()

        dominant_course_name = dominant_course_id
        if courses is not None and "course_name" in courses.columns:
            match = courses[courses["course_id"] == dominant_course_id]["course_name"]
            if len(match):
                dominant_course_name = match.values[0]

        course_grades = grades[grades["course_id"] == dominant_course_id].copy()

        def extract_order(title):
            order_map = {"quiz": 1, "assignment": 2, "practical": 3, "midterm": 4, "final": 5}
            title_lower = str(title).lower()
            for key, base in order_map.items():
                if key in title_lower:
                    num = re.search(r'\d+', title_lower)
                    return base * 10 + (int(num.group()) if num else 0)
            return 99

        course_grades["order"] = course_grades[title_col].apply(extract_order)

        mastery_over_time = (
            course_grades
            .groupby(title_col)
            .agg(
                order=("order", "first"),
                fail_rate=("score", lambda x: (x < 60).mean()),
                avg_score=("score", "mean"),
                n_students=("score", "count")
            )
            .reset_index()
            .sort_values("order")
        )
        mastery_over_time.columns = ["assessment_title", "order", "fail_rate", "avg_score", "n_students"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=mastery_over_time["assessment_title"],
            y=mastery_over_time["fail_rate"],
            mode="lines+markers+text",
            text=mastery_over_time["fail_rate"].apply(lambda x: f"{x:.0%}"),
            textposition="top center",
            textfont=dict(size=13),
            line=dict(color="#e74c3c", width=3),
            marker=dict(
                size=14,
                color=mastery_over_time["fail_rate"].apply(
                    lambda x: "#e74c3c" if x >= 0.60 else "#f39c12" if x >= 0.40 else "#27ae60"
                )
            ),
            name="Failure Rate"
        ))
        fig.add_hline(y=0.60, line_dash="dash", line_color="darkred",
                      annotation_text="Critical Zone (60%+)", annotation_position="top left")
        fig.update_layout(
            title=f"{dominant_course_name} — Is Mastery Improving Over Time?",
            xaxis_title="Assessment (in order)",
            yaxis_title="Failure Rate",
            yaxis_tickformat=".0%",
            yaxis_range=[0, 1],
            height=500,
            font=dict(size=13),
            showlegend=False
        )
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        first = mastery_over_time["fail_rate"].iloc[0]
        last = mastery_over_time["fail_rate"].iloc[-1]
        delta = last - first
        trend_word = "improving 📈" if delta < 0 else "declining 📉" if delta > 0 else "flat ⚠️"
        components.insight(f"Failure rate for '{dominant_course_name}' went from {first:.0%} to {last:.0%} — {trend_word}.")
    else:
        st.info("Grades data not available.")
except Exception as e:
    st.info(f"Mastery trend not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q8: Submission Timing vs Score
# ══════════════════════════════════════════════════════════════════
components.q_header(8, "Do students who submit assignments late tend to score lower? Show the effect.", "HARD", 6)

try:
    if submissions is not None and grades is not None:
        sub = submissions.copy()
        sub["deadline"]     = pd.to_datetime(sub["deadline"])
        sub["submitted_at"] = pd.to_datetime(sub["submitted_at"])
        sub["buffer_hours"] = (sub["deadline"] - sub["submitted_at"]).dt.total_seconds() / 3600

        sub_grades = sub.merge(
            grades[["student_id", "assessment_id", "score"]],
            on=["student_id", "assessment_id"],
            how="inner"
        )

        def buffer_band(hours):
            if hours < 0:
                return "🔴 Late"
            elif hours < 12:
                return "🟡 Last Minute (<12hrs)"
            else:
                return "🟢 On Time (12+ hrs)"

        band_order = ["🔴 Late", "🟡 Last Minute (<12hrs)", "🟢 On Time (12+ hrs)"]
        sub_grades["submission_band"] = sub_grades["buffer_hours"].apply(buffer_band)

        band_summary = (
            sub_grades
            .groupby("submission_band")["score"]
            .agg(avg_score="mean", n_students="count")
            .reset_index()
        )
        band_summary["submission_band"] = pd.Categorical(
            band_summary["submission_band"], categories=band_order, ordered=True
        )
        band_summary = band_summary.sort_values("submission_band")

        fig = px.bar(
            band_summary,
            x="submission_band", y="avg_score",
            text=band_summary.apply(
                lambda r: f"{r['avg_score']:.1f}%<br>({r['n_students']:,} submissions)", axis=1
            ),
            color="submission_band",
            color_discrete_map={
                "🔴 Late": "#e74c3c",
                "🟡 Last Minute (<12hrs)": "#f39c12",
                "🟢 On Time (12+ hrs)": "#27ae60"
            },
            title="Does Submitting Early Lead to Better Scores?",
            labels={"avg_score": "Average Score (%)", "submission_band": "Submission Timing"},
            category_orders={"submission_band": band_order}
        )
        fig.update_traces(textposition="outside", textfont_size=14)
        fig.update_layout(height=500, font=dict(size=13), yaxis_range=[0, 100], showlegend=False)
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        late_avg   = band_summary[band_summary["submission_band"] == "🔴 Late"]["avg_score"]
        ontime_avg = band_summary[band_summary["submission_band"] == "🟢 On Time (12+ hrs)"]["avg_score"]
        if len(late_avg) and len(ontime_avg):
            components.insight(
                f"On-time submitters score {ontime_avg.values[0]:.1f}% vs {late_avg.values[0]:.1f}% for late ones — "
                f"a {ontime_avg.values[0] - late_avg.values[0]:.1f} point advantage for early submission."
            )
    else:
        st.info("Submissions or Grades data not available.")
except Exception as e:
    st.info(f"Submission data not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q9: Attendance & Engagement Over Time
# ══════════════════════════════════════════════════════════════════
components.q_header(9, "Plot attendance and engagement over the 6-month term. Is there a dip window?", "HARD", 6)

# weekly_combined is reused as a display variable only within this block;
# nothing later in the page depends on it.
try:
    if attendance is not None:
        date_col_att = get_date_col(attendance, ["session_datetime", "date"])
        attendance_dt = attendance.copy()
        attendance_dt[date_col_att] = pd.to_datetime(attendance_dt[date_col_att])
        attendance_dt["week"] = attendance_dt[date_col_att].dt.to_period("W").apply(lambda x: x.start_time)

        attendance_weekly = (
            attendance_dt.groupby("week")
            .agg(attendance_rate=("status", lambda x: (x == "attended").mean()))
            .reset_index()
        )

        term_start = attendance_dt[date_col_att].min()
        term_end   = attendance_dt[date_col_att].max()

        if event is not None:
            ev_date_col = get_date_col(event, ["event_datetime", "date"])
            event_dt = event.copy()
            event_dt[ev_date_col] = pd.to_datetime(event_dt[ev_date_col])
            event_dt["week"] = event_dt[ev_date_col].dt.to_period("W").apply(lambda x: x.start_time)

            ev_weekly = (
                event_dt[
                    (event_dt[ev_date_col] >= term_start) & (event_dt[ev_date_col] <= term_end)
                ]
                .groupby("week")
                .agg(events_per_week=("event_id", "count"))
                .reset_index()
            )
        else:
            ev_weekly = pd.DataFrame(columns=["week", "events_per_week"])

        weekly_combined = (
            attendance_weekly
            .merge(ev_weekly, on="week", how="outer")
            .sort_values("week")
            .fillna(0)
        )

        weekly_combined["attendance_z"] = (
            (weekly_combined["attendance_rate"] - weekly_combined["attendance_rate"].mean())
            / weekly_combined["attendance_rate"].std()
        )
        weekly_combined["events_z"] = (
            (weekly_combined["events_per_week"] - weekly_combined["events_per_week"].mean())
            / weekly_combined["events_per_week"].std()
        )
        weekly_combined["combined_dip_score"] = (
            weekly_combined["attendance_z"] + weekly_combined["events_z"]
        )
        dip_week = weekly_combined.loc[weekly_combined["combined_dip_score"].idxmin()]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=weekly_combined["week"], y=weekly_combined["attendance_rate"],
            mode="lines+markers", name="Attendance Rate",
            line=dict(color="#3498db", width=3), yaxis="y1"
        ))
        fig.add_trace(go.Scatter(
            x=weekly_combined["week"], y=weekly_combined["events_per_week"],
            mode="lines+markers", name="Engagement (Events/Week)",
            line=dict(color="#e67e22", width=3), yaxis="y2"
        ))
        fig.update_layout(
            title="Attendance & Engagement Over the Term",
            xaxis_title="Week",
            yaxis=dict(title="Attendance Rate", tickformat=".0%", side="left"),
            yaxis2=dict(title="Events per Week", overlaying="y", side="right"),
            height=550, font=dict(size=13),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        components.insight(
            f"Strongest dip window detected in week of {dip_week['week'].strftime('%b %d, %Y')} — "
            f"attendance at {dip_week['attendance_rate']:.1%} & {int(dip_week['events_per_week'])} events "
            f"(combined dip score: {dip_week['combined_dip_score']:.2f}). "
            f"This may signal mid-term burnout or an external event worth investigating."
        )
    else:
        st.info("Attendance collection not found.")
except Exception as e:
    st.info(f"Attendance/engagement trend not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q10: Age Band Analysis
# ══════════════════════════════════════════════════════════════════
components.q_header(10, "Bucket students into age bands and compare avg grade, attendance, and engagement.", "HARD", 6)

try:
    required_cols = {"age", "avg_grade", "attendance_rate", "total_events"}
    if required_cols.issubset(df.columns):
        df_q10 = df.copy()
        df_q10["age_band"] = pd.cut(df_q10["age"], bins=[0, 20, 25, 30, 100],
                                    labels=["≤20", "21-25", "26-30", "30+"])

        band_summary_q10 = df_q10.groupby("age_band", observed=True).agg(
            avg_grade=("avg_grade", "mean"),
            attendance_rate=("attendance_rate", "mean"),
            total_events=("total_events", "mean")
        ).reset_index()
        band_summary_q10["age_band"] = band_summary_q10["age_band"].astype(str)

        fig = px.bar(
            band_summary_q10, x="age_band", y="avg_grade",
            text=band_summary_q10["avg_grade"].apply(lambda x: f"{x:.1f}%"),
            title="Average Grade by Age Group",
            labels={"avg_grade": "Average Grade (%)", "age_band": "Age Group"},
            color_discrete_sequence=brand["palette"]
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=450, showlegend=False, yaxis_range=[0, 100])
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        best_age = band_summary_q10.loc[band_summary_q10["avg_grade"].idxmax()]
        age_desc = "older" if best_age["age_band"] == "30+" else "younger"
        components.insight(f"The {best_age['age_band']} age group shows the highest avg grade at {best_age['avg_grade']:.1f} — "
                           f"suggesting {age_desc} students may be more academically focused.")
    else:
        missing_cols = required_cols - set(df.columns)
        st.info(f"master_students is missing columns needed for this analysis: {', '.join(missing_cols)}.")
except Exception as e:
    st.info(f"Age band analysis not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q11: Student Segmentation
# ══════════════════════════════════════════════════════════════════
components.q_header(11, "Build a student segmentation using attendance, engagement, avg grade and failed concepts.",
                    "VERY HARD", 9)

try:
    if all(x is not None for x in [grade_per_student, attendance_per_student, active_days_per_student, failed_concepts]):
        from scipy.stats import zscore

        seg_df = (
            grade_per_student
            .merge(attendance_per_student, on="student_id", how="outer")
            .merge(active_days_per_student, on="student_id", how="outer")
            .merge(failed_concepts, on="student_id", how="outer")
            .fillna(0)
        )

        seg_df["composite_score"] = (
            zscore(seg_df["avg_grade"]) +
            zscore(seg_df["attendance_rate"]) +
            zscore(seg_df["active_days"]) -
            zscore(seg_df["failed_concepts"])
        )

        seg_df["segment"] = pd.qcut(
            seg_df["composite_score"], q=4,
            labels=["Disengaged At-Risk", "Struggling", "Steady Performer", "High Achiever"],
            duplicates="drop"
        )

        segment_summary = seg_df.groupby("segment", observed=True).agg(
            avg_grade=("avg_grade", "mean"),
            attendance_rate=("attendance_rate", "mean"),
            active_days=("active_days", "mean"),
            failed_concepts=("failed_concepts", "mean"),
            n_students=("student_id", "count")
        ).reset_index()

        fig = px.bar(
            segment_summary, x="segment", y="n_students", text="n_students", color="segment",
            color_discrete_map={
                "Disengaged At-Risk": "#e74c3c",
                "Struggling": "#f39c12",
                "Steady Performer": "#3498db",
                "High Achiever": "#27ae60"
            },
            title="Student Segments",
            labels={"n_students": "Number of Students", "segment": "Segment"}
        )
        fig.update_layout(height=450, showlegend=False)
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        at_risk = (seg_df["segment"] == "Disengaged At-Risk").sum()
        components.insight(
            f"{at_risk} students are classified as Disengaged At-Risk — low engagement AND low grades. "
            f"These should be the first priority for instructor intervention."
        )
    else:
        st.info("Grades, Attendance, Event, or Performance data not available for segmentation.")
except Exception as e:
    st.info(f"Student segmentation not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q12: Real vs Stated Group Sizes
# ══════════════════════════════════════════════════════════════════
components.q_header(
    12,
    "Compute true group sizes and compare to self-reported counts in groups.csv.",
    "VERY HARD",
    9
)

try:
    if groups is not None and "group_id" in df.columns and "stated_num_students" in groups.columns:
        true_size = (
            df.groupby("group_id")["student_id"]
              .nunique()
              .reset_index(name="actual_size")
        )

        group_compare = (
            groups[["group_id", "group_name", "stated_num_students"]]
            .merge(true_size, on="group_id", how="left")
        )

        group_compare["actual_size"] = group_compare["actual_size"].fillna(0).astype(int)
        group_compare["discrepancy"] = group_compare["actual_size"] - group_compare["stated_num_students"]
        group_compare = group_compare.sort_values("discrepancy", key=abs, ascending=False)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=group_compare["group_name"], y=group_compare["stated_num_students"],
            name="Stated", marker_color="#95a5a6"
        ))
        fig.add_trace(go.Bar(
            x=group_compare["group_name"], y=group_compare["actual_size"],
            name="Actual", marker_color="#3498db"
        ))
        fig.update_layout(barmode="group", title="Stated vs Actual Group Size",
                          height=500, yaxis_title="Number of Students")
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        flagged_groups = group_compare[group_compare["discrepancy"].abs() >= 3]
        max_diff = group_compare.iloc[0]

        components.insight(
            f"'{max_diff['group_name']}' shows the largest discrepancy. "
            f"Reported size: {max_diff['stated_num_students']}, "
            f"actual size: {max_diff['actual_size']} "
            f"({max_diff['discrepancy']:+d} students). "
            f"{len(flagged_groups)} group(s) differ by at least 3 students."
        )
    else:
        st.info("Groups data (with stated_num_students) not available for this comparison.")
except Exception as e:
    st.info(f"Group size comparison not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q13: Group Sizes with Merge Recommendation
# ══════════════════════════════════════════════════════════════════
components.q_header(13, "Identify the smallest group and find its closest counterpart by concept profile.", "VERY HARD", 9)

try:
    if "group_id" in df.columns and "student_id" in df.columns:
        group_sizes = df.groupby("group_id")["student_id"].count().reset_index(name="actual_size")
        group_sizes = group_sizes.rename(columns={"group_id": "group_name"}).sort_values("actual_size")

        smallest_id = group_sizes.iloc[0]["group_name"]
        second_smallest_id = group_sizes.iloc[1]["group_name"] if len(group_sizes) > 1 else None

        colors = group_sizes["group_name"].apply(
            lambda g: "#e74c3c" if g == smallest_id else "#27ae60" if g == second_smallest_id else "#3498db"
        )

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=group_sizes["group_name"], y=group_sizes["actual_size"],
            marker_color=colors,
            text=group_sizes["actual_size"], textposition="outside"
        ))

        smallest_size = group_sizes.iloc[0]["actual_size"]
        if second_smallest_id:
            fig.add_annotation(
                x=smallest_id, y=smallest_size + 2,
                text=f"Recommended: Merge into {second_smallest_id}",
                showarrow=True, arrowhead=2,
                ax=80, ay=-40, font=dict(size=13, color="#e74c3c")
            )

        fig.update_layout(
            title=f"Group Sizes — {smallest_id} Flagged for Merge",
            xaxis_title="Group", yaxis_title="Number of Students",
            height=550, font=dict(size=13), showlegend=False
        )
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        components.insight(f"'{smallest_id}' is the smallest group with only {smallest_size} students — "
                           f"too small to be statistically viable. Consider merging with {second_smallest_id or 'the closest group'}.")
    else:
        st.info("master_students is missing group_id/student_id columns.")
except Exception as e:
    st.info(f"Group merge recommendation not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q14: At-Risk Student Ranking
# ══════════════════════════════════════════════════════════════════
components.q_header(
    14,
    "Combine low attendance, declining engagement and failed concepts into an at-risk ranking.",
    "VERY HARD",
    9
)

try:
    if event is not None and attendance_per_student is not None and failed_concepts is not None \
            and {"student_id", "full_name", "group_id"}.issubset(df.columns):

        ev_date_col = get_date_col(event, ["event_datetime", "date"])
        ev2 = event.copy()
        ev2["date"] = pd.to_datetime(ev2[ev_date_col])

        mid_point = ev2["date"].min() + (ev2["date"].max() - ev2["date"].min()) / 2
        ev2["half"] = ev2["date"].apply(lambda x: "first" if x < mid_point else "second")

        engagement_half = (
            ev2.groupby(["student_id", "half"])["event_id"]
               .count()
               .unstack(fill_value=0)
        )
        engagement_half["engagement_change"] = (
            engagement_half.get("second", 0) - engagement_half.get("first", 0)
        )
        engagement_half = engagement_half.reset_index()[["student_id", "engagement_change"]]

        risk_df = (
            attendance_per_student
            .merge(engagement_half, on="student_id", how="outer")
            .merge(failed_concepts, on="student_id", how="outer")
            .merge(
                df[["student_id", "full_name", "group_id"]].drop_duplicates(),
                on="student_id", how="left"
            )
            .fillna(0)
        )

        risk_df["risk_score"] = (
            (1 - risk_df["attendance_rate"]) * 40 +
            (risk_df["engagement_change"] < 0).astype(int) * 20 +
            risk_df["failed_concepts"] * 5
        )

        top10_at_risk = risk_df.sort_values("risk_score", ascending=False).head(10)

        fig = px.bar(
            top10_at_risk.sort_values("risk_score"),
            x="risk_score", y="full_name", orientation="h",
            text=top10_at_risk.sort_values("risk_score")["risk_score"].apply(lambda x: f"{x:.0f}"),
            title="Top 10 At-Risk Students",
            labels={"risk_score": "Risk Score", "full_name": "Student"},
            color_discrete_sequence=["#e74c3c"]
        )
        fig.update_layout(height=500, showlegend=False)
        components.apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        top1 = top10_at_risk.iloc[0]
        components.insight(
            f"'{top1['full_name']}' has the highest risk score ({top1['risk_score']:.0f}). "
            f"Attendance: {top1['attendance_rate']:.1%}, "
            f"engagement change: {top1['engagement_change']:+.0f} events, "
            f"failed concepts: {top1['failed_concepts']:.0f}. "
            f"This student should be prioritized for intervention."
        )
    else:
        st.info("Event, Attendance, or Performance data not available for risk ranking.")
except Exception as e:
    st.info(f"At-risk ranking not available: {str(e)}")

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# Q15: Group Performance Trend (Slope-Based)
# ══════════════════════════════════════════════════════════════════
components.q_header(15, "Track each group's average grade across successive assessments. Who is trending up/down?",
                    "VERY HARD", 9)

try:
    if grades is not None:
        date_col_g = get_date_col(grades, ["date", "submitted_at"])
        group_col = "group_id" if "group_id" in grades.columns else None

        if date_col_g and group_col:
            grades_dt = grades.copy()
            grades_dt[date_col_g] = pd.to_datetime(grades_dt[date_col_g])
            grades_dt["month"] = grades_dt[date_col_g].dt.to_period("M").astype(str)
            trend_raw = grades_dt.groupby(["month", group_col])["score"].mean().reset_index()
            trend_raw.columns = ["month", "group_name", "avg_score"]

            def compute_slope(group_df):
                group_df = group_df.sort_values("month").reset_index(drop=True)
                if len(group_df) < 2:
                    return 0
                x = np.arange(len(group_df))
                return np.polyfit(x, group_df["avg_score"], 1)[0]

            slopes = trend_raw.groupby("group_name").apply(compute_slope).reset_index()
            slopes.columns = ["group_name", "slope"]
            slopes["direction"] = slopes["slope"].apply(
                lambda s: "Improving" if s > 0.5 else "Declining" if s < -0.5 else "Stable"
            )

            fig = px.bar(
                slopes.sort_values("slope"),
                x="group_name", y="slope", color="direction",
                color_discrete_map={"Improving": "#27ae60", "Stable": "#95a5a6", "Declining": "#e74c3c"},
                title="Group Performance Trend Over the Term",
                labels={"slope": "Trend (points/assessment)", "group_name": "Group"}
            )
            fig.update_layout(height=500)
            components.apply_theme(fig)
            st.plotly_chart(fig, use_container_width=True)

            improving = slopes[slopes["direction"] == "Improving"]["group_name"].tolist()
            declining = slopes[slopes["direction"] == "Declining"]["group_name"].tolist()
            components.insight(f"Groups trending UP 📈: {', '.join(improving) if improving else 'None'} — "
                               f"Groups trending DOWN 📉: {', '.join(declining) if declining else 'None'}.")
        else:
            st.info("grades collection missing date or group_id column.")
    else:
        st.info("Grades data not available.")
except Exception as e:
    st.info(f"Group performance trend not available: {str(e)}")

# ── Footer ────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
components.copyright_footer("Kayfa")