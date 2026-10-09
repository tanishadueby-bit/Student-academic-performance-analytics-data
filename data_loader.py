"""
data_loader.py
--------------
Loads and validates the student CSV data.
Adds computed columns used throughout the dashboard.

Public API
----------
load_data(filepath)          — load the bundled sample CSV
load_from_dataframe(df)      — attach computed columns to any raw DataFrame
validate_uploaded_df(df)     — check an uploaded file has the required columns
REQUIRED_COLUMNS             — set of column names every valid CSV must contain
SUBJECTS                     — ordered list of subject column names
PASS_MARK                    — per-subject pass threshold (40)
PASS_ATTENDANCE              — minimum attendance % (75)
"""

import pandas as pd
from pathlib import Path

# ── Schema constants ──────────────────────────────────────────────────────────

SUBJECTS = ["math", "physics", "chemistry", "english", "computer_science"]

# Columns that MUST be present in any uploaded CSV
REQUIRED_COLUMNS = {"student_id", "name", "semester", "attendance_pct"} | set(SUBJECTS)

PASS_MARK       = 40   # minimum mark per subject to pass
PASS_ATTENDANCE = 75   # minimum attendance % required


# ── Public loaders ────────────────────────────────────────────────────────────

def load_data(filepath: str = "data/students.csv") -> pd.DataFrame:
    """
    Read the bundled sample CSV and return a DataFrame with computed columns.
    Raises FileNotFoundError if the file does not exist.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path.resolve()}")

    raw = pd.read_csv(path)
    return load_from_dataframe(raw)


def load_from_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Attach computed columns to a raw student DataFrame.

    Computed columns added
    ----------------------
    total           — sum of all SUBJECTS marks
    average         — mean of all SUBJECTS marks (rounded 2 dp)
    average_pct     — average expressed as a percentage of max (100), same value
    pass_fail       — 'Pass' if every subject >= PASS_MARK, else 'Fail'
    needs_support   — True when average < 50 OR attendance < PASS_ATTENDANCE
    grade           — letter grade (A+, A, B, C, D, F)
    low_attendance  — True when attendance_pct < PASS_ATTENDANCE  (used for row highlighting)

    The original DataFrame is NOT mutated — a copy is returned.
    """
    df = df.copy()

    # Ensure subject columns are numeric (uploaded CSVs may come in as strings)
    for col in SUBJECTS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "attendance_pct" in df.columns:
        df["attendance_pct"] = pd.to_numeric(df["attendance_pct"], errors="coerce").fillna(0)

    # Only compute subject-based columns when all subjects are present
    available_subjects = [s for s in SUBJECTS if s in df.columns]
    if available_subjects:
        df["total"]       = df[available_subjects].sum(axis=1)
        df["average"]     = df[available_subjects].mean(axis=1).round(2)
        df["average_pct"] = df["average"]   # marks are already out of 100

        subject_pass  = (df[available_subjects] >= PASS_MARK).all(axis=1)
        df["pass_fail"] = subject_pass.map({True: "Pass", False: "Fail"})

    if "average" in df.columns and "attendance_pct" in df.columns:
        df["needs_support"]  = (df["average"] < 50) | (df["attendance_pct"] < PASS_ATTENDANCE)
        df["low_attendance"] = df["attendance_pct"] < PASS_ATTENDANCE

    if "average" in df.columns:
        df["grade"] = df["average"].apply(_letter_grade)

    # Normalise optional department column
    if "department" not in df.columns:
        df["department"] = "General"

    return df


# ── Validation ────────────────────────────────────────────────────────────────

def validate_uploaded_df(df: pd.DataFrame) -> list[str]:
    """
    Check that a DataFrame uploaded by the user contains all required columns.

    Returns
    -------
    list[str]
        Empty list  → file is valid.
        Non-empty   → one error message per missing / invalid column.
    """
    errors = []

    # Missing columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        errors.append(
            f"Missing required column(s): **{', '.join(sorted(missing))}**"
        )

    # Must have at least one data row
    if len(df) == 0:
        errors.append("The uploaded file contains no data rows.")

    # Numeric sanity checks (only when columns are present)
    for subj in SUBJECTS:
        if subj in df.columns:
            if not pd.to_numeric(df[subj], errors="coerce").notna().all():
                errors.append(f"Column **{subj}** contains non-numeric values.")

    if "attendance_pct" in df.columns:
        numeric_att = pd.to_numeric(df["attendance_pct"], errors="coerce")
        if not numeric_att.notna().all():
            errors.append("Column **attendance_pct** contains non-numeric values.")
        elif numeric_att.max() > 100 or numeric_att.min() < 0:
            errors.append("Column **attendance_pct** must be between 0 and 100.")

    return errors


# ── Internal helpers ──────────────────────────────────────────────────────────

def _letter_grade(avg: float) -> str:
    """Return a letter grade for a numeric average (marks out of 100)."""
    if avg >= 90:
        return "A+"
    elif avg >= 80:
        return "A"
    elif avg >= 70:
        return "B"
    elif avg >= 60:
        return "C"
    elif avg >= 50:
        return "D"
    else:
        return "F"
