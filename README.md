# AI Document Extractor — Invoice & Resume Automation

Two AI-powered automation tools that extract structured data from unstructured documents (images, PDFs, and Word files) using Google Gemini's multimodal AI, wrapped in a Flask REST API and connected to no-code automation (Make.com) for real-world, hands-off workflows.

**Live API:** `https://rabia.pythonanywhere.com`

---

## The Problem

Manually copying data from invoices, receipts, and resumes into spreadsheets is slow, repetitive, and error-prone. Small businesses processing dozens of receipts a month — or recruiters screening hundreds of resumes — waste hours on data entry that could be automated.

## The Solution

Two connected tools built on the same core architecture:

### 1. Invoice / Receipt Extractor
Drop a photo or PDF of a receipt into a Google Drive folder. The system automatically:
- Reads the image using Gemini's vision capabilities (no separate OCR step required)
- Extracts vendor, date, total, and itemized line items as structured JSON
- Correctly distinguishes `TOTAL` from `SUBTOTAL` even when discounts are applied
- Writes the result to a Google Sheet — fully automated, no manual entry

### 2. Resume / CV Bulk Extractor
Candidates submit resumes via a Google Form. The system automatically:
- Extracts name, contact info, skills, work experience, and education from PDF/DOCX files
- Compares the candidate against a job description using AI
- Produces a 0–100 match score with matched/missing skills and a plain-English summary
- Logs everything to a candidate database in Google Sheets

---

## How It Works

```
Invoice pipeline:
Google Drive (new file) → Make.com → Flask API → Gemini AI → Google Sheets

Resume pipeline:
Google Form (submission) → Make.com → Flask API → Gemini AI → Google Sheets
```

Both tools share one Flask backend with two endpoints (`/extract-invoice` and `/extract-resume`), deployed on PythonAnywhere and orchestrated by Make.com scenarios that handle file transport, error routing, and spreadsheet writes.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI / extraction | Google Gemini API (multimodal — reads images directly) |
| Backend | Python, Flask, Gunicorn |
| File parsing | PyPDF2, python-docx |
| Hosting | PythonAnywhere |
| Automation | Make.com (Google Drive / Forms / Sheets integration) |
| Version control | Git, GitHub |

---

## Key Engineering Decisions

- **No OCR step.** Early versions used Tesseract OCR before sending text to the AI. Switching to Gemini's native image understanding removed a fragile system dependency, simplified deployment (no Docker/system packages needed), and *improved* accuracy — OCR was misreading numbers in tight-column receipt layouts.
- **Retry logic with model fallback.** API calls automatically retry with exponential backoff and fall back to a secondary model if the primary is temporarily overloaded, so transient upstream issues don't break the pipeline.
- **Prompt-level correctness rules.** The extraction prompt explicitly instructs the model to distinguish `TOTAL` from `SUBTOTAL`/`CASH`/`CHANGE` — a bug found and fixed during testing where the model initially picked the pre-discount subtotal.
- **Batch support.** The resume endpoint accepts multiple files in a single request for bulk processing.

---

## Accuracy Results

Tested against 7 real samples with known ground truth (4 invoices, 3 resumes across logistics, marketing, and engineering roles):

**100% field-level extraction accuracy** across vendor/name, date, totals, line items, contact info, skills, experience, and education fields.

Match-scoring was validated against two different job descriptions for the same resume — correctly returning a 0/100 score for an unrelated role and 88–95/100 for a matching role, confirming the scoring logic responds to actual content rather than returning generic values.

Full test log: [`accuracy_testing_log.md`](./accuracy_testing_log.md)

---

## API Reference

### `POST /extract-invoice`
| Field | Type | Description |
|---|---|---|
| `file` | file (jpg/png/pdf) | Invoice or receipt to process |

**Response:**
```json
{
  "success": true,
  "filename": "receipt.jpg",
  "data": {
    "vendor": "Happy Mart",
    "date": "10/07/2020",
    "total": 8.18,
    "currency": "$",
    "items": [{"name": "PEANUTS", "price": 2.46}],
    "items_summary": "PEANUTS ($2.46), TOMATOES ($4.98)"
  }
}
```

### `POST /extract-resume`
| Field | Type | Description |
|---|---|---|
| `files` | file(s) (pdf/docx) | One or more resumes |
| `job_description` | text (optional) | If provided, returns a match score |

**Response:**
```json
{
  "success": true,
  "total_processed": 1,
  "results": [{
    "filename": "resume.pdf",
    "success": true,
    "data": {
      "resume_data": { "name": "...", "skills": ["..."], "experience": ["..."] },
      "match_result": { "match_score": 88, "matched_skills": ["..."], "summary": "..." }
    }
  }]
}
```

---

## Running Locally

```bash
git clone https://github.com/khalidrabia671-cloud/ai-invoice-extractor.git
cd ai-invoice-extractor
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Add your Gemini API key
echo GEMINI_API_KEY=your_key_here > .env

python app.py
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey).

---

## Project Status

Both automation pipelines are built and tested end-to-end. Scheduling is currently manual (Make.com free tier operation limits) — see [Make.com pricing](https://www.make.com/en/pricing) for always-on scheduling options.

## Author

Built as a portfolio project demonstrating AI API integration, REST API design, error handling, and no-code automation orchestration.
