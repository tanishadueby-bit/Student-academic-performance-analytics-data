"""
analysis.py
-----------
Pure analysis functions that take a DataFrame and return
summary DataFrames or scalar values.

Rules
-----
- No Streamlit imports here — keeping analysis separate from presentation
  makes each half easier to test and to reuse.
- Every function accepts the FILTERED DataFrame that app.py passes in,
  so all results automatically reflect the active sidebar filters.
"""

import pandas as pd
from src.data_loader import SUBJECTS, PASS_ATTENDANCE


# ── Overall KPI summary ───────────────────────────────────────────────────────

def overall_summary(df: pd.DataFrame) -> dict:
    """
    Return headline KPIs as a plain dictionary.

    Keys
    ----
    total_students   — unique student IDs in the filtered set
    pass_rate_pct    — % of rows marked 'Pass'
    avg_score        — mean of the 'average' column (marks %)
    avg_attendance   — mean attendance %
    at_risk_count    — unique students flagged needs_support
    """
    total_students = df["student_id"].nunique()
    pass_rate      = (df["pass_fail"] == "Pass").mean() * 100
    avg_score      = df["average"].mean()
    avg_attendance = df["attendance_pct"].mean()
    at_risk        = df[df["needs_support"]]["student_id"].nunique()

    return {
        "total_students" : int(total_students),
        "pass_rate_pct"  : round(pass_rate, 1),
        "avg_score"      : round(avg_score, 1),
        "avg_attendance" : round(avg_attendance, 1),
        "at_risk_count"  : int(at_risk),
    }


# ── Subject-wise analysis ─────────────────────────────────────────────────────

def subject_averages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return one row per subject with:
    subject, average_mark, pass_rate_pct, highest, lowest

    Only includes subjects that are present as columns in df.
    """
    available = [s for s in SUBJECTS if s in df.columns]
    rows = []
    for subject in available:
        rows.append({
            "subject"       : subject.replace("_", " ").title(),
            "average_mark"  : round(df[subject].mean(), 2),
            "pass_rate_pct" : round((df[subject] >= 40).mean() * 100, 1),
            "highest"       : int(df[subject].max()),
            "lowest"        : int(df[subject].min()),
        })
    return pd.DataFrame(rows)


def subject_averages_for_subject(df: pd.DataFrame, subject: str) -> pd.DataFrame:
    """
    Break down a single subject's average by department and semester.
    Returns columns: group_label, average_mark.
    Useful for the 'filter by subject' deep-dive chart.
    """
    col = subject.lower().replace(" ", "_")
    if col not in df.columns:
        return pd.DataFrame(columns=["group_label", "average_mark"])

    result = (
        df.groupby(["department", "semester"])[col]
        .mean()
        .round(2)
        .reset_index()
    )
    result["group_label"] = (
        result["department"] + " — Sem " + result["semester"].astype(str)
    )
    return result[["group_label", "average_mark"]].rename(
        columns={"average_mark": "average_mark"}
    )


# ── Semester-wise analysis ────────────────────────────────────────────────────

def semester_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return per-semester averages for every subject plus overall average
    and attendance.  Columns are title-cased for display.
    """
    available = [s for s in SUBJECTS if s in df.columns]
    grp    = df.groupby("semester")
    result = grp[available + ["average", "attendance_pct"]].mean().round(2)
    result.columns = [c.replace("_", " ").title() for c in result.columns]
    result = result.reset_index()
    result.rename(columns={"semester": "Semester"}, inplace=True)
    return result


# ── Department-wise analysis ──────────────────────────────────────────────────

def department_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return per-department averages for overall score, attendance, and pass rate.
    """
    grp = df.groupby("department")
    summary = pd.DataFrame({
        "Department"    : grp["average"].mean().round(2).index,
        "Avg Score"     : grp["average"].mean().round(2).values,
        "Avg Attendance": grp["attendance_pct"].mean().round(2).values,
        "Pass Rate %"   : (grp["pass_fail"].apply(lambda s: (s == "Pass").mean() * 100)).round(1).values,
        "Students"      : grp["student_id"].nunique().values,
    })
    return summary.sort_values("Avg Score", ascending=False).reset_index(drop=True)


# ── Student-level detail ──────────────────────────────────────────────────────

def student_detail(df: pd.DataFrame, student_id: str) -> pd.DataFrame:
    """Return all rows for a specific student ID, sorted by semester."""
    return (
        df[df["student_id"] == student_id]
        .sort_values("semester")
        .reset_index(drop=True)
    )


def subject_marks_for_student(df: pd.DataFrame, student_id: str) -> pd.DataFrame:
    """
    Return a 'long' DataFrame for a student, suitable for a radar/bar chart.
    Columns: Semester, Subject, Mark
    """
    student_df = student_detail(df, student_id)
    available  = [s for s in SUBJECTS if s in df.columns]
    rows = []
    for _, row in student_df.iterrows():
        for subj in available:
            rows.append({
                "Semester": f"Semester {int(row['semester'])}",
                "Subject" : subj.replace("_", " ").title(),
                "Mark"    : row[subj],
            })
    return pd.DataFrame(rows)


# ── At-risk / needs support ───────────────────────────────────────────────────

def at_risk_students(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return one row per student who needs academic support,
    using the latest available semester's record per student.
    """
    latest = (
        df.sort_values("semester")
          .groupby("student_id", as_index=False)
          .last()
    )
    at_risk = latest[latest["needs_support"]].copy()
    cols    = ["student_id", "name", "department", "semester",
               "average", "attendance_pct", "pass_fail", "grade"]
    at_risk = at_risk[[c for c in cols if c in at_risk.columns]]
    at_risk.columns = [
        {"student_id": "ID", "name": "Name", "department": "Department",
         "semester": "Last Sem", "average": "Average",
         "attendance_pct": "Attendance %", "pass_fail": "Status",
         "grade": "Grade"}.get(c, c)
        for c in at_risk.columns
    ]
    return at_risk.sort_values("Average").reset_index(drop=True)


# ── Pass / fail breakdown ─────────────────────────────────────────────────────

def pass_fail_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Count of Pass vs Fail per semester."""
    return (
        df.groupby(["semester", "pass_fail"])
          .size()
          .reset_index(name="count")
          .rename(columns={"semester": "Semester", "pass_fail": "Status"})
    )


# ── Attendance buckets ────────────────────────────────────────────────────────

def attendance_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bucket students by attendance range using their latest semester record.
    Returns: Attendance Range, Students
    """
    latest = (
        df.sort_values("semester")
          .groupby("student_id", as_index=False)
          .last()
    )
    bins   = [0, 60, 75, 85, 100]
    labels = ["< 60%", "60–75%", "75–85%", "85–100%"]
    latest = latest.copy()
    latest["bucket"] = pd.cut(
        latest["attendance_pct"], bins=bins, labels=labels, right=True
    )
    counts = (
        latest.groupby("bucket", observed=True)
              .size()
              .reset_index(name="count")
    )
    counts.columns = ["Attendance Range", "Students"]
    return counts


# ── Results table (for display) ───────────────────────────────────────────────

def build_results_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a clean, display-ready table from the filtered DataFrame.
    Columns are title-cased; subject columns use human-readable names.
    low_attendance is kept as a boolean so app.py can use it for highlighting.
    """
    available_subjects = [s for s in SUBJECTS if s in df.columns]

    display_cols = (
        ["student_id", "name", "department", "semester"]
        + available_subjects
        + ["attendance_pct", "average", "grade", "pass_fail", "low_attendance"]
    )
    display_cols = [c for c in display_cols if c in df.columns]

    out = df[display_cols].copy()
    rename_map = {
        "student_id"    : "ID",
        "name"          : "Name",
        "department"    : "Department",
        "semester"      : "Semester",
        "attendance_pct": "Attendance %",
        "average"       : "Average",
        "grade"         : "Grade",
        "pass_fail"     : "Result",
        "low_attendance": "low_attendance",   # keep as-is; used for styling
    }
    for subj in available_subjects:
        rename_map[subj] = subj.replace("_", " ").title()

    out = out.rename(columns=rename_map)
    return out.sort_values(["Semester", "Name"]).reset_index(drop=True)
