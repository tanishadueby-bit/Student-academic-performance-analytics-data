"""
charts.py
---------
All Plotly chart-building functions.

Rules
-----
- No Streamlit imports here — pure Plotly only.
- Every function accepts a DataFrame (already filtered) and returns a
  go.Figure ready to hand to st.plotly_chart().
- Chart titles are kept short; axis labels carry the detail.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ── Shared design tokens ───────────────────────────────────────────────────────
# Blue-and-white theme to match the dashboard palette
BLUE_SEQ   = "Blues"                          # sequential colourscale
PALETTE    = [                                # categorical palette — blue family first
    "#1f77b4", "#4e9de0", "#7bbcf5",
    "#2ca02c", "#ff7f0e", "#9467bd",
    "#8c564b", "#e377c2",
]
PASS_COLOR = "#2ecc71"   # green
FAIL_COLOR = "#e74c3c"   # red
WARN_COLOR = "#f39c12"   # amber

LAYOUT_DEFAULTS = dict(
    font=dict(family="Segoe UI, Arial, sans-serif", size=13),
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    margin=dict(t=50, b=40, l=40, r=20),
)


def _apply_defaults(fig: go.Figure) -> go.Figure:
    """Apply shared layout defaults to any figure."""
    fig.update_layout(**LAYOUT_DEFAULTS)
    return fig


# ── 1. Subject average marks — horizontal bar ─────────────────────────────────

def subject_avg_bar(subj_df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart of average mark per subject.
    subj_df must have columns: subject, average_mark
    """
    fig = px.bar(
        subj_df.sort_values("average_mark"),
        x="average_mark",
        y="subject",
        orientation="h",
        color="average_mark",
        color_continuous_scale=BLUE_SEQ,
        text="average_mark",
        labels={"average_mark": "Average Mark (/ 100)", "subject": "Subject"},
        title="Average Mark by Subject",
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(coloraxis_showscale=False)
    return _apply_defaults(fig)


# ── 2. Subject pass rate — vertical bar ──────────────────────────────────────

def subject_pass_rate_bar(subj_df: pd.DataFrame) -> go.Figure:
    """
    Vertical bar chart: pass rate % per subject.
    subj_df must have columns: subject, pass_rate_pct
    """
    fig = px.bar(
        subj_df,
        x="subject",
        y="pass_rate_pct",
        color="subject",
        color_discrete_sequence=PALETTE,
        text="pass_rate_pct",
        labels={"pass_rate_pct": "Pass Rate (%)", "subject": "Subject"},
        title="Pass Rate (%) by Subject",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(showlegend=False, yaxis_range=[0, 115])
    return _apply_defaults(fig)


# ── 3. Semester performance trend — line ─────────────────────────────────────

def semester_trend_line(sem_df: pd.DataFrame) -> go.Figure:
    """
    Multi-line chart: subject averages across semesters.
    sem_df must have a 'Semester' column plus one column per subject (title-cased).
    Non-subject columns (Average, Attendance Pct) are excluded automatically.
    """
    EXCLUDE = {"Semester", "Average", "Attendance Pct"}
    subject_cols = [c for c in sem_df.columns if c not in EXCLUDE]

    fig = go.Figure()
    for i, subj in enumerate(subject_cols):
        fig.add_trace(go.Scatter(
            x=sem_df["Semester"].astype(str),
            y=sem_df[subj],
            mode="lines+markers",
            name=subj,
            line=dict(color=PALETTE[i % len(PALETTE)], width=2),
            marker=dict(size=9),
        ))
    fig.update_layout(
        title="Subject Averages Across Semesters",
        xaxis_title="Semester",
        yaxis_title="Average Mark",
        legend_title="Subject",
        yaxis_range=[0, 105],
    )
    return _apply_defaults(fig)


# ── 4. Pass / fail grouped bar ────────────────────────────────────────────────

def pass_fail_bar(pf_df: pd.DataFrame) -> go.Figure:
    """
    Grouped bar: Pass vs Fail count per semester.
    pf_df must have columns: Semester, Status, count
    """
    fig = px.bar(
        pf_df,
        x="Semester",
        y="count",
        color="Status",
        barmode="group",
        color_discrete_map={"Pass": PASS_COLOR, "Fail": FAIL_COLOR},
        labels={"count": "Number of Students"},
        title="Pass / Fail Count per Semester",
        text="count",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis={"type": "category"})
    return _apply_defaults(fig)


# ── 5. Grade distribution — donut ─────────────────────────────────────────────

def grade_pie(df: pd.DataFrame) -> go.Figure:
    """
    Donut chart of grade distribution across the filtered dataset.
    Uses the most recent semester per student.
    """
    latest = (
        df.sort_values("semester")
          .groupby("student_id", as_index=False)
          .last()
    )
    grade_counts = latest["grade"].value_counts().reset_index()
    grade_counts.columns = ["Grade", "Count"]

    # Sort in logical grade order
    order = ["A+", "A", "B", "C", "D", "F"]
    grade_counts["Grade"] = pd.Categorical(
        grade_counts["Grade"], categories=order, ordered=True
    )
    grade_counts = grade_counts.sort_values("Grade")

    grade_colors = {
        "A+": "#1565c0", "A": "#1976d2", "B": "#42a5f5",
        "C": "#f39c12",  "D": "#e67e22", "F": "#e74c3c",
    }
    colors = [grade_colors.get(g, "#999") for g in grade_counts["Grade"]]

    fig = go.Figure(go.Pie(
        labels=grade_counts["Grade"],
        values=grade_counts["Count"],
        hole=0.42,
        marker_colors=colors,
        textinfo="label+percent",
        pull=[0.04] * len(grade_counts),
    ))
    fig.update_layout(title="Grade Distribution")
    return _apply_defaults(fig)


# ── 6. Attendance distribution — colour-coded bar ────────────────────────────

def attendance_bar(att_df: pd.DataFrame) -> go.Figure:
    """
    Bar chart of students per attendance bucket.
    Colours: red for danger zone (<60%), amber for warning (60-75%),
             light-blue for adequate, blue for good.
    att_df must have columns: Attendance Range, Students
    """
    bucket_colors = {
        "< 60%"   : FAIL_COLOR,
        "60–75%"  : WARN_COLOR,
        "75–85%"  : "#4e9de0",
        "85–100%" : "#1f77b4",
    }
    colors = [bucket_colors.get(r, "#999") for r in att_df["Attendance Range"]]

    fig = go.Figure(go.Bar(
        x=att_df["Attendance Range"],
        y=att_df["Students"],
        marker_color=colors,
        text=att_df["Students"],
        textposition="outside",
    ))
    fig.update_layout(
        title="Students by Attendance Range",
        xaxis_title="Attendance Range",
        yaxis_title="Number of Students",
        showlegend=False,
    )
    return _apply_defaults(fig)


# ── 7. Attendance scatter (attendance vs. average mark) ───────────────────────

def attendance_vs_score_scatter(df: pd.DataFrame) -> go.Figure:
    """
    Scatter plot: attendance % (x) vs. average mark (y).
    Points are coloured by pass/fail status.
    A vertical reference line marks the 75% attendance threshold.
    """
    fig = px.scatter(
        df,
        x="attendance_pct",
        y="average",
        color="pass_fail",
        color_discrete_map={"Pass": PASS_COLOR, "Fail": FAIL_COLOR},
        hover_data={"name": True, "student_id": True,
                    "attendance_pct": ":.1f", "average": ":.1f"},
        labels={
            "attendance_pct": "Attendance (%)",
            "average"       : "Average Mark",
            "pass_fail"     : "Result",
            "name"          : "Name",
        },
        title="Attendance vs. Average Mark",
    )
    # Threshold reference lines
    fig.add_vline(x=75,  line_dash="dash", line_color=WARN_COLOR,
                  annotation_text="75% attendance threshold",
                  annotation_position="top left")
    fig.add_hline(y=40,  line_dash="dot",  line_color=FAIL_COLOR,
                  annotation_text="Pass mark (40)",
                  annotation_position="bottom right")
    return _apply_defaults(fig)


# ── 8. Subject deep-dive bar (by department × semester) ───────────────────────

def subject_deepdive_bar(deepdive_df: pd.DataFrame, subject_name: str) -> go.Figure:
    """
    Bar chart of a single subject's average broken down by department+semester.
    deepdive_df must have columns: group_label, average_mark
    """
    fig = px.bar(
        deepdive_df,
        x="group_label",
        y="average_mark",
        color="group_label",
        color_discrete_sequence=PALETTE,
        text="average_mark",
        labels={"average_mark": "Average Mark", "group_label": "Group"},
        title=f"{subject_name} — Average by Department & Semester",
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(showlegend=False, xaxis_title="")
    return _apply_defaults(fig)


# ── 9. Individual student radar chart ────────────────────────────────────────

def student_radar(student_long_df: pd.DataFrame) -> go.Figure:
    """
    Radar / spider chart showing a student's marks per subject,
    with one trace per semester.
    student_long_df must have columns: Semester, Subject, Mark
    """
    subjects  = student_long_df["Subject"].unique().tolist()
    semesters = student_long_df["Semester"].unique().tolist()

    fig = go.Figure()
    for i, sem in enumerate(semesters):
        sem_data = student_long_df[student_long_df["Semester"] == sem]
        marks    = sem_data.set_index("Subject").reindex(subjects)["Mark"].tolist()
        marks   += [marks[0]]   # close the polygon

        fig.add_trace(go.Scatterpolar(
            r=marks,
            theta=subjects + [subjects[0]],
            fill="toself",
            name=sem,
            line_color=PALETTE[i % len(PALETTE)],
            opacity=0.75,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="Subject Performance Radar",
    )
    return _apply_defaults(fig)


# ── 10. Individual student score + attendance line ───────────────────────────

def student_score_line(student_df: pd.DataFrame) -> go.Figure:
    """
    Dual-line chart: student's average mark and attendance % across semesters.
    student_df must have columns: semester, average, attendance_pct
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=student_df["semester"].astype(str),
        y=student_df["average"],
        mode="lines+markers",
        name="Average Mark",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=9),
    ))
    fig.add_trace(go.Scatter(
        x=student_df["semester"].astype(str),
        y=student_df["attendance_pct"],
        mode="lines+markers",
        name="Attendance %",
        line=dict(color=WARN_COLOR, width=2, dash="dash"),
        marker=dict(size=9),
    ))
    fig.add_hline(y=40, line_dash="dot", line_color=FAIL_COLOR,
                  annotation_text="Pass threshold (40)")
    fig.add_hline(y=75, line_dash="dot", line_color=WARN_COLOR,
                  annotation_text="Min attendance (75%)")
    fig.update_layout(
        title="Score & Attendance Progression",
        xaxis_title="Semester",
        yaxis_title="Value",
        yaxis_range=[0, 108],
        legend_title="Metric",
    )
    return _apply_defaults(fig)


# ── 11. Department comparison bar ────────────────────────────────────────────

def department_bar(dept_df: pd.DataFrame) -> go.Figure:
    """
    Grouped bar: avg score and avg attendance side-by-side per department.
    dept_df must have columns: Department, Avg Score, Avg Attendance
    """
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Avg Score",
        x=dept_df["Department"],
        y=dept_df["Avg Score"],
        marker_color="#1f77b4",
        text=dept_df["Avg Score"],
        texttemplate="%{text:.1f}",
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="Avg Attendance %",
        x=dept_df["Department"],
        y=dept_df["Avg Attendance"],
        marker_color="#4e9de0",
        text=dept_df["Avg Attendance"],
        texttemplate="%{text:.1f}%",
        textposition="outside",
    ))
    fig.update_layout(
        barmode="group",
        title="Department Comparison — Score vs. Attendance",
        xaxis_title="Department",
        yaxis_title="Value",
        yaxis_range=[0, 115],
        legend_title="Metric",
    )
    return _apply_defaults(fig)
