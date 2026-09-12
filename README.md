# Ledger — AI Expense & Resume Tracker

A full-stack web application that uses Google Gemini's multimodal AI to extract structured data from invoices/receipts and resumes — with user accounts, a personal spending dashboard, currency conversion, and PDF report export.

**Live app:** `https://rabia.pythonanywhere.com`

---

## The Problem

Manually copying data from invoices, receipts, and resumes into spreadsheets is slow, repetitive, and error-prone. People tracking personal expenses across multiple currencies, or recruiters screening resumes against job descriptions, waste hours on data entry that could be automated.

## The Solution

A single web app with user accounts where anyone can:

### 📄 Track expenses with AI
- Upload a photo or PDF of a receipt — Gemini reads it directly (no separate OCR step)
- Extracts vendor, date, total, and itemized line items as structured JSON
- Automatically converts any currency to PKR (live exchange rate, with an offline fallback)
- Every receipt is saved to a personal, per-user history with a spending-over-time chart
- Download a formatted PDF expense report at any time

### 🧑‍💼 Screen resumes with AI
- Upload a resume (PDF/DOCX) — extracts name, contact info, skills, experience, education
- Optionally paste a job description to get a 0–100 AI match score with matched/missing skills
- Every screening is saved to a personal resume history

---

## Architecture

```
Browser (login-protected dashboard)
        │
        ▼
   Flask backend ──► Google Gemini API (multimodal extraction + matching)
        │
        ├──► SQLite (users, receipts, resumes — per-user isolated)
        ├──► Currency API (live rate, with a hardcoded fallback for restricted hosting)
        └──► ReportLab (PDF report generation)
```

A second, fully independent automation pipeline (Make.com) also exists for hands-off batch processing: dropping files into Google Drive / a Google Form automatically routes them through the same Flask API into Google Sheets.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI / extraction | Google Gemini API (multimodal — reads images directly) |
| Backend | Python, Flask, Gunicorn |
| Auth & sessions | Flask sessions, werkzeug password hashing |
| Database | SQLite |
| File parsing | PyPDF2, python-docx |
| PDF generation | ReportLab |
| Charts | Chart.js |
| Currency data | Live FX API with a static fallback table |
| Hosting | PythonAnywhere |
| Automation (optional pipeline) | Make.com (Google Drive / Forms / Sheets) |

---

## Key Engineering Decisions

- **No OCR step.** Early versions used Tesseract OCR before sending text to the AI. Switching to Gemini's native image understanding removed a fragile system dependency, simplified deployment, and *improved* accuracy — OCR was misreading numbers in tight-column receipt layouts.
- **Retry logic with model fallback.** API calls automatically retry with exponential backoff and fall back to a secondary model if the primary is overloaded.
- **Network-restricted hosting handled gracefully.** The free hosting tier only allows outbound requests to a domain whitelist. The currency converter detects when the live FX API is unreachable and falls back to a static rate table instead of silently failing — spending totals never show as zero due to a blocked network call.
- **Per-user data isolation.** All receipts and resumes are scoped to the logged-in user's session; delete operations verify ownership before executing.
- **Robust date handling.** Receipt dates arrive in inconsistent formats (`10/07/2020`, `04 Dec 2024`, etc.). Dates are parsed into a normalized ISO format at save time purely for chronological sorting, while the original format is preserved for display.
- **Prompt-level correctness rules.** The extraction prompt explicitly instructs the model to distinguish `TOTAL` from `SUBTOTAL`/`CASH`/`CHANGE` — a bug found and fixed during testing.

---

## Accuracy Results

Tested against 7 real samples with known ground truth (4 invoices, 3 resumes across logistics, marketing, and engineering roles): **100% field-level extraction accuracy.**

Match-scoring was validated against two different job descriptions for the same resume — correctly returning 0/100 for an unrelated role and 88–95/100 for a matching role.

Full test log: [`accuracy_testing_log.md`](./accuracy_testing_log.md)

---

## Running Locally

```bash
git clone https://github.com/khalidrabia671-cloud/ai-ledger-expense-resume-tracker.git
cd ai-ledger-expense-resume-tracker
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Add your Gemini API key and a session secret
echo GEMINI_API_KEY=your_key_here > .env
echo FLASK_SECRET_KEY=any_random_string >> .env

python app.py
```

Then visit `http://127.0.0.1:5000/signup` to create an account.

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey).

## Author

Built as a portfolio project demonstrating full-stack development: authentication, database design, AI API integration, third-party API resilience (fallback handling), PDF generation, and no-code automation orchestration.
