"""
app.py
------
Student Academic Performance Analytics — Streamlit Dashboard

Entry point.  Run with:
    streamlit run app.py

Architecture
------------
1.  Data loading  — src/data_loader.py
2.  Analysis      — src/analysis.py      (pure functions, no Streamlit)
3.  Charts        — src/charts.py        (pure Plotly, no Streamlit)
4.  This file     — layout, filters, and wiring everything together

All charts and summary cards update automatically when the sidebar
filters change, because every analysis function receives the already-
filtered DataFrame.
"""

import io
import zipfile

import pandas as pd
import streamlit as st

# ── Local modules ─────────────────────────────────────────────────────────────
from src.data_loader import (
    PASS_ATTENDANCE,
    REQUIRED_COLUMNS,
    SUBJECTS,
    load_data,
    load_from_dataframe,
    validate_uploaded_df,
)
from src.analysis import (
    at_risk_students,
    attendance_distribution,
    build_results_table,
    department_summary,
    overall_summary,
    pass_fail_counts,
    semester_summary,
    student_detail,
    subject_averages,
    subject_averages_for_subject,
    subject_marks_for_student,
)
from src.charts import (
    attendance_bar,
    attendance_vs_score_scatter,
    department_bar,
    grade_pie,
    pass_fail_bar,
    semester_trend_line,
    student_radar,
    student_score_line,
    subject_avg_bar,
    subject_deepdive_bar,
    subject_pass_rate_bar,
)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG  (must be the very first Streamlit call)
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Student Academic Performance Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# THEME / GLOBAL CSS
# Professional blue-and-white palette:
#   Primary blue  #1a3a6b
#   Accent blue   #2c5aa0
#   Light bg      #f0f4ff
#   Border        #ccd9f0
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <style>
    /* ── Page background ───────────────────────────────────────── */
    [data-testid="stAppViewContainer"] { background: #f7f9fc; }
    [data-testid="stSidebar"]          { background: #1a3a6b; }

    /* ── Sidebar text ──────────────────────────────────────────── */
    [data-testid="stSidebar"] * { color: #e8eef8 !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stTextInput label { color: #b0c4e8 !important; }

    /* ── Metric cards ──────────────────────────────────────────── */
    [data-testid="metric-container"] {
        background    : #ffffff;
        border        : 1px solid #ccd9f0;
        border-top    : 4px solid #2c5aa0;
        border-radius : 8px;
        padding       : 16px 20px;
        box-shadow    : 0 1px 4px rgba(44,90,160,0.08);
    }

    /* ── Section headings ──────────────────────────────────────── */
    h1 { color: #1a3a6b; }
    h2 { color: #1a3a6b; border-bottom: 2px solid #ccd9f0; padding-bottom: 6px; }
    h3 { color: #2c5aa0; }

    /* ── Tab bar ───────────────────────────────────────────────── */
    [data-testid="stTabs"] button[aria-selected="true"] {
        color       : #1a3a6b !important;
        border-bottom: 3px solid #1a3a6b !important;
        font-weight : 700;
    }

    /* ── Low-attendance row highlight in tables ────────────────── */
    /* Applied via Pandas Styler — the CSS class name is set there  */

    /* ── Upload zone ───────────────────────────────────────────── */
    [data-testid="stFileUploader"] {
        border    : 2px dashed #2c5aa0;
        border-radius: 8px;
        padding   : 10px;
    }

    /* ── Divider ───────────────────────────────────────────────── */
    hr { border-color: #ccd9f0; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# Priority: uploaded file > default sample data
# The result is cached so the CSV is not re-parsed on every widget interaction.
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="Loading data…")
def _load_default() -> pd.DataFrame:
    """Load and process the bundled sample CSV."""
    return load_data("data/students.csv")


def _load_uploaded(file_bytes: bytes) -> tuple[pd.DataFrame | None, list[str]]:
    """
    Parse an uploaded CSV, validate it, and return (processed_df, errors).
    Returns (None, errors) when validation fails.
    """
    try:
        raw = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:
        return None, [f"Could not parse the CSV file: {exc}"]

    errors = validate_uploaded_df(raw)
    if errors:
        return None, errors

    return load_from_dataframe(raw), []


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — upload, filters, search
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    # ── Brand header ──────────────────────────────────────────────────────────
    st.markdown(
        "<div style='text-align:center;padding:16px 0 8px'>"
        "<span style='font-size:2.4rem'>🎓</span>"
        "<h2 style='color:#ffffff!important;margin:4px 0 0;font-size:1.1rem;"
        "border:none;padding:0'>Academic Analytics</h2>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='border-color:#3a5a9b;margin:0 0 16px'>", unsafe_allow_html=True)

    # ── CSV Upload ─────────────────────────────────────────────────────────────
    st.markdown("#### 📂 Data Source")
    uploaded_file = st.file_uploader(
        "Upload your own CSV",
        type=["csv"],
        help=(
            "Required columns: student_id, name, semester, "
            "math, physics, chemistry, english, computer_science, attendance_pct.\n\n"
            "Optional: department"
        ),
    )

    # Resolve active dataset
    upload_errors: list[str] = []
    if uploaded_file is not None:
        df_raw, upload_errors = _load_uploaded(uploaded_file.read())
        if df_raw is not None:
            df_full = df_raw
            st.success(f"✅ Loaded **{len(df_full)}** rows from uploaded file.")
        else:
            df_full = _load_default()   # fall back to sample data on error
    else:
        df_full = _load_default()

    # Show upload validation errors immediately (non-blocking)
    if upload_errors:
        for err in upload_errors:
            st.error(err)
        st.info("Showing sample data instead.")

    st.markdown("<hr style='border-color:#3a5a9b;margin:12px 0'>", unsafe_allow_html=True)

    # ── Filter: Semester ───────────────────────────────────────────────────────
    st.markdown("#### 🔍 Filters")
    all_semesters = sorted(df_full["semester"].unique())
    selected_semesters = st.multiselect(
        "Semester",
        options=all_semesters,
        default=all_semesters,
        format_func=lambda x: f"Semester {x}",
    )

    # ── Filter: Department ─────────────────────────────────────────────────────
    all_departments = sorted(df_full["department"].unique())
    selected_departments = st.multiselect(
        "Department",
        options=all_departments,
        default=all_departments,
    )

    # ── Filter: Subject (for deep-dive chart only) ────────────────────────────
    subject_display_names = [s.replace("_", " ").title() for s in SUBJECTS]
    selected_subject = st.selectbox(
        "Subject (deep-dive chart)",
        options=subject_display_names,
    )

    st.markdown("<hr style='border-color:#3a5a9b;margin:12px 0'>", unsafe_allow_html=True)

    # ── Student search ─────────────────────────────────────────────────────────
    st.markdown("#### 🔎 Student Search")
    search_query = st.text_input(
        "Search by name or ID",
        placeholder="e.g. Alice or S001",
    ).strip()

    st.markdown("<hr style='border-color:#3a5a9b;margin:12px 0'>", unsafe_allow_html=True)

    # ── Legend / rules ─────────────────────────────────────────────────────────
    st.markdown(
        "<small style='color:#90a8d0'>"
        "🔴 Pass mark: 40 per subject<br>"
        "🟠 Min attendance: 75%<br>"
        "⚠️ Support flag: avg &lt; 50 or attendance &lt; 75%"
        "</small>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# APPLY FILTERS
# Everything below uses df_filtered.  All analysis functions receive this
# DataFrame, so every chart and card automatically reflects the active filters.
# ══════════════════════════════════════════════════════════════════════════════

# Guard against empty multiselect (keep all if nothing selected)
active_semesters   = selected_semesters   or all_semesters
active_departments = selected_departments or all_departments

df_filtered = df_full[
    (df_full["semester"].isin(active_semesters)) &
    (df_full["department"].isin(active_departments))
].copy()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(
    "<h1 style='margin-bottom:2px'>🎓 Student Academic Performance Analytics</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "An interactive dashboard to explore student marks, attendance, "
    "subject-wise performance, semester trends, and students who may need "
    "academic support.  Use the **sidebar** to filter by semester, department, "
    "or search for a specific student."
)

# Show active filter pills
filter_pills = (
    f"**Semesters:** {', '.join(str(s) for s in active_semesters)} &nbsp;|&nbsp; "
    f"**Departments:** {', '.join(active_departments)} &nbsp;|&nbsp; "
    f"**Rows:** {len(df_filtered):,}"
)
st.caption(filter_pills)
st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# NAVIGATION TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_overview, tab_subjects, tab_semesters, tab_students, tab_atrisk, tab_dept = st.tabs([
    "📊 Overview",
    "📚 Subjects",
    "📅 Semesters",
    "👤 Student Profile",
    "⚠️ At-Risk",
    "🏫 Departments",
])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# Shows: KPI summary cards, pass/fail chart, grade donut, attendance bar,
#        attendance-vs-score scatter, raw data table.
# ════════════════════════════════════════════════════════════════════════════

with tab_overview:

    st.header("Overall Performance Snapshot")

    # ── KPI cards ──────────────────────────────────────────────────────────
    kpi = overall_summary(df_filtered)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(
        "👥 Total Students",
        kpi["total_students"],
        help="Unique student IDs in the filtered data.",
    )
    c2.metric(
        "✅ Pass Rate",
        f"{kpi['pass_rate_pct']}%",
        help="Percentage of records where every subject ≥ 40.",
    )
    c3.metric(
        "📈 Avg Mark",
        f"{kpi['avg_score']}%",
        help="Mean of all subject averages.",
    )
    c4.metric(
        "🗓️ Avg Attendance",
        f"{kpi['avg_attendance']}%",
        help="Mean attendance percentage.",
    )
    c5.metric(
        "⚠️ Need Support",
        kpi["at_risk_count"],
        help="Students with average < 50 or attendance < 75%.",
        delta=None,
    )

    st.divider()

    # ── Row 1: pass/fail bar + grade donut ──────────────────────────────────
    row1_l, row1_r = st.columns(2)
    with row1_l:
        pf_df = pass_fail_counts(df_filtered)
        if not pf_df.empty:
            st.plotly_chart(pass_fail_bar(pf_df), use_container_width=True)
        else:
            st.info("No pass/fail data to display.")

    with row1_r:
        st.plotly_chart(grade_pie(df_filtered), use_container_width=True)

    # ── Row 2: attendance distribution + scatter ────────────────────────────
    row2_l, row2_r = st.columns(2)
    with row2_l:
        att_df = attendance_distribution(df_filtered)
        st.plotly_chart(attendance_bar(att_df), use_container_width=True)

    with row2_r:
        st.plotly_chart(
            attendance_vs_score_scatter(df_filtered), use_container_width=True
        )

    st.divider()

    # ── Student results table with search + highlight ───────────────────────
    st.subheader("📋 Student Results Table")
    st.caption(
        "Rows with attendance below 75% are highlighted in amber. "
        "Use the search box in the sidebar to filter by name or ID."
    )

    results_df = build_results_table(df_filtered)

    # Apply search filter from sidebar
    if search_query:
        mask = (
            results_df["Name"].str.contains(search_query, case=False, na=False) |
            results_df["ID"].str.contains(search_query, case=False, na=False)
        )
        results_df = results_df[mask]
        if results_df.empty:
            st.warning(f"No students found matching **'{search_query}'**.")

    # Separate the styling flag before rendering
    low_att_flag = results_df.pop("low_attendance") if "low_attendance" in results_df.columns else None

    def _highlight_low_attendance(row: pd.Series) -> list[str]:
        """Return amber background style for rows with low attendance."""
        if low_att_flag is not None and low_att_flag.iloc[row.name]:
            return ["background-color: #fff3cd; color: #7d4e00"] * len(row)
        return [""] * len(row)

    styled = results_df.style.apply(_highlight_low_attendance, axis=1).format(
        {"Average": "{:.1f}", "Attendance %": "{:.1f}"}
    )

    st.dataframe(styled, use_container_width=True, height=420)

    # ── Download filtered results — ZIP with CSV + Excel ───────────────────
    # Build Excel sheet in memory
    _xl_buf = io.BytesIO()
    results_df.to_excel(_xl_buf, index=False, sheet_name="Filtered Results", engine="openpyxl")
    _xl_bytes = _xl_buf.getvalue()

    # Build ZIP in memory containing both files
    _zip_buf = io.BytesIO()
    with zipfile.ZipFile(_zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as _zf:
        _zf.writestr("filtered_results.csv",   results_df.to_csv(index=False).encode("utf-8"))
        _zf.writestr("filtered_results.xlsx",  _xl_bytes)
    _zip_bytes = _zip_buf.getvalue()

    dl_col1, dl_col2, dl_col3 = st.columns(3)
    dl_col1.download_button(
        label="⬇️  Download as CSV",
        data=results_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_results.csv",
        mime="text/csv",
        help="Downloads the filtered table as a CSV file.",
    )
    dl_col2.download_button(
        label="⬇️  Download as Excel",
        data=_xl_bytes,
        file_name="filtered_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Downloads the filtered table as an Excel (.xlsx) file.",
    )
    dl_col3.download_button(
        label="⬇️  Download ZIP (CSV + Excel)",
        data=_zip_bytes,
        file_name="filtered_results.zip",
        mime="application/zip",
        help="Downloads a ZIP archive containing both the CSV and Excel files.",
    )


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — SUBJECTS
# Shows: subject summary table, average-marks bar, pass-rate bar,
#        single-subject deep-dive by department × semester.
# ════════════════════════════════════════════════════════════════════════════

with tab_subjects:

    st.header("Subject-Wise Performance")
    st.caption(
        "All charts reflect the active semester and department filters. "
        "Select a subject in the sidebar to see the deep-dive breakdown."
    )

    subj_df = subject_averages(df_filtered)

    # ── Summary table ───────────────────────────────────────────────────────
    st.subheader("Summary by Subject")
    st.dataframe(
        subj_df.style
               .background_gradient(subset=["average_mark"], cmap="Blues")
               .format({"average_mark": "{:.1f}", "pass_rate_pct": "{:.1f}%"}),
        use_container_width=True,
    )

    st.divider()

    # ── Charts: average marks + pass rate ───────────────────────────────────
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(subject_avg_bar(subj_df), use_container_width=True)
    with col_r:
        st.plotly_chart(subject_pass_rate_bar(subj_df), use_container_width=True)

    st.divider()

    # ── Deep-dive for the selected subject ──────────────────────────────────
    st.subheader(f"🔬 Deep Dive: {selected_subject}")
    deepdive_df = subject_averages_for_subject(df_filtered, selected_subject)
    if deepdive_df.empty:
        st.info("Not enough data for the selected subject / filters.")
    else:
        st.plotly_chart(
            subject_deepdive_bar(deepdive_df, selected_subject),
            use_container_width=True,
        )

    # ── Quick insight banner ─────────────────────────────────────────────────
    if not subj_df.empty:
        best  = subj_df.loc[subj_df["average_mark"].idxmax(), "subject"]
        worst = subj_df.loc[subj_df["average_mark"].idxmin(), "subject"]
        st.info(
            f"✅ **Strongest subject:** {best}  \n"
            f"⚠️ **Weakest subject:** {worst}  \n"
            f"📈 **Class average across all subjects:** "
            f"{df_filtered['average'].mean():.1f} / 100"
        )


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — SEMESTERS
# Shows: semester summary table, subject-trend line, attendance trend.
# ════════════════════════════════════════════════════════════════════════════

with tab_semesters:

    st.header("Semester-Wise Performance Trends")

    if len(active_semesters) < 2:
        st.warning(
            "Select **at least two semesters** from the sidebar "
            "to see trend charts."
        )
    else:
        sem_df = semester_summary(df_filtered)

        st.subheader("Semester Summary Table")
        st.dataframe(
            sem_df.style.format(precision=1),
            use_container_width=True,
        )

        st.divider()

        # Subject trend line
        st.plotly_chart(semester_trend_line(sem_df), use_container_width=True)

        st.divider()

        # Attendance trend table
        st.subheader("Average Attendance by Semester")
        att_trend = (
            df_filtered.groupby("semester")["attendance_pct"]
            .mean()
            .round(1)
            .reset_index()
            .rename(columns={"semester": "Semester", "attendance_pct": "Avg Attendance %"})
        )
        st.dataframe(
            att_trend.style.format({"Avg Attendance %": "{:.1f}%"}),
            use_container_width=True,
        )


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — STUDENT PROFILE
# Shows: searchable student picker, KPI cards, radar chart,
#        score/attendance line, full record table.
# ════════════════════════════════════════════════════════════════════════════

with tab_students:

    st.header("Individual Student Profile")
    st.caption("Select a student from the dropdown, or use the sidebar search to pre-fill.")

    # Build a list of unique students from the FULL dataset (not filtered)
    # so a student isn't hidden by the semester/department filter here.
    student_options = (
        df_full[["student_id", "name"]]
        .drop_duplicates("student_id")
        .sort_values("name")
    )
    student_labels = {
        row["student_id"]: f"{row['name']} ({row['student_id']})"
        for _, row in student_options.iterrows()
    }

    # If there is an active search query that matches exactly one student, pre-select.
    default_idx = 0
    if search_query:
        for idx, (sid, label) in enumerate(student_labels.items()):
            if (
                search_query.lower() in label.lower() or
                search_query.upper() == sid.upper()
            ):
                default_idx = idx
                break

    chosen_sid = st.selectbox(
        "Select a student",
        options=list(student_labels.keys()),
        format_func=lambda sid: student_labels[sid],
        index=default_idx,
    )

    student_df      = student_detail(df_full, chosen_sid)
    student_long_df = subject_marks_for_student(df_full, chosen_sid)

    if student_df.empty:
        st.warning("No records found for this student.")
    else:
        latest = student_df.iloc[-1]

        # ── KPI cards ──────────────────────────────────────────────────────
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        sc1.metric("Name",           latest["name"])
        sc2.metric("Department",     latest["department"])
        sc3.metric("Latest Average", f"{latest['average']:.1f}")
        sc4.metric("Attendance",     f"{latest['attendance_pct']}%")
        sc5.metric("Grade / Result", f"{latest['grade']} / {latest['pass_fail']}")

        # Support alert
        if latest["needs_support"]:
            st.error(
                f"⚠️ **{latest['name']}** is flagged for academic support — "
                f"average: **{latest['average']:.1f}**, "
                f"attendance: **{latest['attendance_pct']}%**."
            )
        else:
            st.success(
                f"✅ **{latest['name']}** is performing within acceptable thresholds."
            )

        st.divider()

        # ── Charts: progression line + radar ───────────────────────────────
        ch_l, ch_r = st.columns(2)
        with ch_l:
            st.plotly_chart(student_score_line(student_df), use_container_width=True)
        with ch_r:
            if not student_long_df.empty:
                st.plotly_chart(student_radar(student_long_df), use_container_width=True)

        # ── Full record table ───────────────────────────────────────────────
        st.subheader("Full Academic Record")
        available_subj = [s for s in SUBJECTS if s in student_df.columns]
        display_cols   = (
            ["semester"] + available_subj +
            ["attendance_pct", "average", "grade", "pass_fail"]
        )
        display_cols = [c for c in display_cols if c in student_df.columns]

        st.dataframe(
            student_df[display_cols]
            .rename(columns={
                c: c.replace("_", " ").title() for c in display_cols
            })
            .style.format({"Average": "{:.1f}"}),
            use_container_width=True,
        )


# ════════════════════════════════════════════════════════════════════════════
# TAB 5 — AT-RISK STUDENTS
# Shows: flagged student table with colour coding, recommended actions,
#        download button.
# ════════════════════════════════════════════════════════════════════════════

with tab_atrisk:

    st.header("⚠️ Students Who May Need Academic Support")
    st.markdown(
        "A student is flagged when their **average mark is below 50** "
        "OR their **attendance is below 75%**.  "
        "The table uses the student's **most recent semester** record."
    )

    # Always use the full dataset for at-risk decisions (filters shouldn't
    # hide a student who needs support from another semester/department).
    risk_df = at_risk_students(df_full)

    if risk_df.empty:
        st.success("🎉 No students are currently flagged for academic support.")
    else:
        st.warning(
            f"**{len(risk_df)} student(s)** may need academic support "
            f"({len(risk_df)} unique IDs)."
        )

        # Colour severity levels
        def _risk_row_style(row: pd.Series) -> list[str]:
            avg = row.get("Average", 100)
            if avg < 40:
                return ["background-color:#ffd6d6; color:#7b1a1a"] * len(row)
            elif avg < 50:
                return ["background-color:#fff3cd; color:#7d4e00"] * len(row)
            else:   # attendance issue only
                return ["background-color:#fff8e1; color:#5a4000"] * len(row)

        st.dataframe(
            risk_df.style.apply(_risk_row_style, axis=1).format(
                {"Average": "{:.1f}", "Attendance %": "{:.1f}%"}
            ),
            use_container_width=True,
        )

        # Colour legend
        st.markdown(
            "<small>"
            "🔴 <b>Red</b> — failing (average &lt; 40) &nbsp;|&nbsp; "
            "🟡 <b>Yellow</b> — borderline (average 40–50) &nbsp;|&nbsp; "
            "🟠 <b>Amber</b> — attendance concern only"
            "</small>",
            unsafe_allow_html=True,
        )

        st.divider()

        # Recommended actions table
        st.subheader("📋 Recommended Actions")
        st.markdown(
            """
| Situation | Recommended Action |
|---|---|
| Average < 40 (failing) | Immediate academic counselling + remedial classes |
| Average 40–50 | Weekly progress reviews + extra tutoring |
| Attendance < 75% | Attendance improvement plan + guardian notification |
| Flagged in multiple semesters | Dedicated mentor assignment |
            """
        )

        st.divider()

        # Download at-risk list — ZIP with CSV + Excel
        _risk_xl_buf = io.BytesIO()
        risk_df.to_excel(_risk_xl_buf, index=False, sheet_name="At-Risk Students", engine="openpyxl")
        _risk_xl_bytes = _risk_xl_buf.getvalue()

        _risk_zip_buf = io.BytesIO()
        with zipfile.ZipFile(_risk_zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as _zf:
            _zf.writestr("at_risk_students.csv",  risk_df.to_csv(index=False).encode("utf-8"))
            _zf.writestr("at_risk_students.xlsx", _risk_xl_bytes)
        _risk_zip_bytes = _risk_zip_buf.getvalue()

        risk_dl1, risk_dl2, risk_dl3 = st.columns(3)
        risk_dl1.download_button(
            label="⬇️  Download as CSV",
            data=risk_df.to_csv(index=False).encode("utf-8"),
            file_name="at_risk_students.csv",
            mime="text/csv",
        )
        risk_dl2.download_button(
            label="⬇️  Download as Excel",
            data=_risk_xl_bytes,
            file_name="at_risk_students.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        risk_dl3.download_button(
            label="⬇️  Download ZIP (CSV + Excel)",
            data=_risk_zip_bytes,
            file_name="at_risk_students.zip",
            mime="application/zip",
        )


# ════════════════════════════════════════════════════════════════════════════
# TAB 6 — DEPARTMENTS
# Shows: department summary table, department comparison bar chart.
# ════════════════════════════════════════════════════════════════════════════

with tab_dept:

    st.header("Department-Wise Comparison")

    dept_df = department_summary(df_filtered)

    st.subheader("Department Summary Table")
    st.dataframe(
        dept_df.style
               .background_gradient(subset=["Avg Score"], cmap="Blues")
               .format({
                   "Avg Score"     : "{:.1f}",
                   "Avg Attendance": "{:.1f}",
                   "Pass Rate %"   : "{:.1f}%",
               }),
        use_container_width=True,
    )

    st.divider()

    st.plotly_chart(department_bar(dept_df), use_container_width=True)

    # Best / worst
    if not dept_df.empty:
        best_dept  = dept_df.iloc[0]["Department"]
        worst_dept = dept_df.iloc[-1]["Department"]
        st.info(
            f"🏆 **Best performing department:** {best_dept}  \n"
            f"📉 **Lowest average department:** {worst_dept}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.markdown(
    "<div style='text-align:center;color:#8a9bbf;font-size:12px;padding:8px 0'>"
    "Student Academic Performance Analytics &nbsp;·&nbsp; "
    "Built with Streamlit &amp; Plotly &nbsp;·&nbsp; "
    "Synthetic sample data only — no real student information"
    "</div>",
    unsafe_allow_html=True,
)
