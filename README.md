# 🎯 HireIQ — AI-Powered CV Screening System

**Phase 1: CV Scoring & Ranking**

A Streamlit web application that reads a job circular, extracts hiring criteria, and automatically ranks uploaded CVs by how well each candidate matches.

---

## 📦 Requirements

- Python 3.10 or higher
- pip

---

## 🚀 Setup & Installation

### 1. Install dependencies

```bash
pip install streamlit pdfminer.six python-docx sqlalchemy pandas plotly python-dotenv
```

### 2. Run the application

```bash
cd hireiq
streamlit run app.py
```

The app opens automatically in your browser at `http://localhost:8501`

---

## 🗂️ Project Structure

```
hireiq/
├── app.py                      ← Main Streamlit application (run this)
├── requirements.txt            ← Python dependencies
├── modules/
│   ├── pdf_converter.py        ← PDF → plain text
│   ├── circular_parser.py      ← Extract job criteria from circular
│   ├── cv_extractor.py         ← Extract candidate info from CV text
│   └── scorer.py               ← Scoring engine + ranking logic
├── database/
│   └── models.py               ← SQLite database models
├── sample_data/
│   └── job_circular.txt        ← Sample job circular to test with
└── data/
    ├── circulars/
    ├── cvs/
    └── exports/
```

---

## 📋 How to Use

### Step 1 — Upload Job Circular
- Upload a `.txt` file of the job circular, OR click **"Use Sample Circular"** to test immediately
- Click **"Extract Job Criteria"**
- Review the extracted criteria (gender preference, age range, education, experience, skills)

### Step 2 — Upload CVs
- Upload one or more PDF CV files

### Step 3 — Run Screening
- Click **"Screen All CVs"**
- Switch to the **Ranked Results** tab to see candidates ranked #1 to #N

### Ranked Results tab
- See all candidates sorted by match score
- Download results as CSV
- View score charts and radar profile for top candidate

### Candidate Detail tab
- Click **"View Details"** on any candidate for a full breakdown
- See exactly which criteria they passed/failed and why
- Update candidate status: Pending / Selected / Rejected / Hold

---

## ⚖️ Scoring Weights (Adjustable)

Use the sidebar sliders to change how each criterion is weighted:

| Criterion | Default | What it checks |
|-----------|---------|----------------|
| Education | 30 pts  | Degree level + field of study match |
| Experience | 25 pts | Years of work experience |
| Skills | 20 pts | Keyword skills found in CV |
| Age | 15 pts | Within stated age range |
| Gender | 10 pts | Matches stated gender preference |

Weights are rescaled automatically if they don't sum to 100.

---

## 📝 Notes

- All data stays on your local machine (SQLite database)
- CV text extraction works best on text-based PDFs (not scanned images)
- For scanned PDFs, OCR support can be added in a future version
- The database (`hireiq.db`) is saved in the `database/` folder

---

## 🗺️ Roadmap

- **Phase 2** — Voice-to-text interview notes (OpenAI Whisper)
- **Phase 3** — WhatsApp notifications for selected candidates (Twilio)
