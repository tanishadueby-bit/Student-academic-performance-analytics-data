# 🎓 Student Academic Performance Analytics

A beginner-friendly interactive web dashboard built with **Python**, **Streamlit**, **Pandas**, and **Plotly** to analyse student academic performance.

---

## 📁 Project Structure

```
Student-Academic-Performance-Analytics/
│
├── app.py                  ← Main Streamlit dashboard (run this)
│
├── src/                    ← Analysis & chart modules
│   ├── __init__.py
│   ├── data_loader.py      ← Loads CSV, adds computed columns
│   ├── analysis.py         ← Pure data-analysis functions
│   └── charts.py           ← Plotly chart builders
│
├── data/
│   └── students.csv        ← Synthetic sample student data (no real data)
│
├── reports/                ← Folder for any exported reports (auto-created)
│
├── requirements.txt        ← Python package dependencies
└── README.md               ← This file
```

---

## 🚀 How to Run Locally (Step-by-Step)

### Step 1 — Make sure Python is installed

Open a terminal / command prompt and run:

```bash
python --version
```

You need **Python 3.9 or newer**.  Download it from [python.org](https://www.python.org/downloads/) if needed.

---

### Step 2 — (Recommended) Create a virtual environment

A virtual environment keeps this project's packages separate from the rest of your system.

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

You'll see `(venv)` appear in your terminal prompt — that means it's active.

---

### Step 3 — Install the required packages

```bash
pip install -r requirements.txt
```

This installs Streamlit, Pandas, Plotly, and NumPy.

---

### Step 4 — Run the dashboard

```bash
streamlit run app.py
```

Streamlit will print something like:

```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```

Open that URL in your browser and the dashboard will load.

---

## 📊 What the Dashboard Shows

| Tab | What it analyses |
|---|---|
| **📊 Overview** | KPI metrics, pass/fail counts, grade distribution, attendance buckets |
| **📚 Subject Analysis** | Average marks and pass rates for each subject |
| **📅 Semester Analysis** | Subject averages and attendance trends across semesters |
| **👤 Student Profile** | Individual student scores, radar chart, semester progression |
| **⚠️ At-Risk Students** | Students flagged for low marks or poor attendance + download CSV |

---

## 🔧 Sidebar Filters

- **Filter by Semester** — narrow all charts to one or more semesters.

---

## 📐 Business Rules Used

| Rule | Value |
|---|---|
| Pass mark (per subject) | ≥ 40 |
| Minimum attendance | ≥ 75% |
| Needs academic support | Average < 50 OR attendance < 75% |
| Grade A+ | Average ≥ 90 |
| Grade A | Average ≥ 80 |
| Grade B | Average ≥ 70 |
| Grade C | Average ≥ 60 |
| Grade D | Average ≥ 50 |
| Grade F | Average < 50 |

---

## 🗂️ Data Format

The dashboard reads `data/students.csv`.  You can replace it with your own data as long as the columns match:

```
student_id, name, semester, math, physics, chemistry, english,
computer_science, attendance_pct
```

> ⚠️ **The sample data is entirely synthetic.** No real student names or records are used.

---

## 🛠️ Extending the Project

- **Add a subject** — add a column to the CSV and update `SUBJECTS` in [`src/data_loader.py`](src/data_loader.py).
- **Change the pass mark** — edit `PASS_MARK` in [`src/data_loader.py`](src/data_loader.py).
- **Export a report** — use the "Download At-Risk Student List" button on the ⚠️ tab; reports go into `reports/`.
- **Add more semesters** — just add rows to the CSV with `semester: 3`, etc.

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web dashboard framework |
| `pandas` | Data loading and analysis |
| `plotly` | Interactive charts |
| `numpy` | Numerical helpers used internally by pandas/plotly |

---

## 💡 Common Issues

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: streamlit` | Run `pip install -r requirements.txt` inside the virtual environment |
| `FileNotFoundError: data/students.csv` | Make sure you run `streamlit run app.py` from the project root folder |
| Port 8501 already in use | Run `streamlit run app.py --server.port 8502` |
| Charts not showing | Ensure `plotly` is installed: `pip install plotly` |
