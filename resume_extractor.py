"""
Resume/CV Bulk Extractor - Core Logic
Day 5: PDF/DOCX se text nikalna + Gemini se structured data + match score nikalna
"""

import os
import json
import time
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
from google import genai

# .env file se API key load karo
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)


def call_gemini_with_retry(contents, max_retries=4):
    """
    Gemini ko call karta hai. Agar ek model busy (503) ho, to
    dusre (halke/faster) model par switch kar ke try karta hai.
    """
    models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash-lite"]

    for attempt in range(max_retries):
        model_name = models_to_try[attempt % len(models_to_try)]
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
            )
            return response
        except Exception as e:
            error_str = str(e)
            is_retryable = "503" in error_str or "UNAVAILABLE" in error_str or "overloaded" in error_str.lower()

            if is_retryable and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"⏳ {model_name} busy hai, {wait_time}s mein dobara try kar raha hoon...")
                time.sleep(wait_time)
            else:
                raise

    raise Exception("Gemini se connect nahi ho paya, sab retries fail ho gaye")


def clean_json_response(raw_output):
    """Gemini kabhi kabhi ```json fences add kar deta hai, unhe hata dete hain."""
    raw_output = raw_output.strip()
    if raw_output.startswith("```"):
        raw_output = raw_output.split("```")[1]
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()
    return raw_output


def extract_text_from_pdf(pdf_path):
    """PDF resume se text nikalta hai."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"ERROR reading PDF: {e}"


def extract_text_from_docx(docx_path):
    """Word (.docx) resume se text nikalta hai."""
    try:
        doc = Document(docx_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    except Exception as e:
        return f"ERROR reading DOCX: {e}"


def extract_resume_text(file_path):
    """File type dekh kar sahi extraction function call karta hai."""
    ext = file_path.lower().split(".")[-1]
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    elif ext == "docx":
        return extract_text_from_docx(file_path)
    else:
        return f"ERROR: Unsupported file type .{ext} (sirf .pdf aur .docx allowed hain)"


RESUME_EXTRACTION_PROMPT = """You are a resume/CV data extraction assistant.
Extract the following fields from the resume text below and return ONLY valid JSON,
with no extra explanation, no markdown formatting, no ```json fences.

Fields to extract:
- name: candidate's full name (string)
- email: email address (string)
- phone: phone number (string)
- skills: a list of technical/professional skills mentioned (list of strings)
- experience: a list of work experience entries, each with "title", "company", and "duration" (list of objects)
- education: a list of education entries, each with "degree", "institution", and "year" (list of objects)

If a field cannot be found, use null (or empty list [] for list fields).
Return only the JSON object.

Resume text:
---
{resume_text}
---
"""


def extract_resume_data(resume_text):
    """Resume text ko Gemini ko bhejta hai aur structured data nikalta hai."""
    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)

    try:
        response = call_gemini_with_retry(prompt)
        raw_output = clean_json_response(response.text)
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return {"error": "Gemini se valid JSON nahi mila", "raw_response": response.text}
    except Exception as e:
        return {"error": f"Resume extraction failed: {str(e)}"}


MATCH_SCORE_PROMPT = """You are a recruiting assistant. Compare the candidate's resume
data below against the job description, and return ONLY valid JSON with no extra
explanation, no markdown formatting, no ```json fences.

Fields to return:
- match_score: a number from 0 to 100 representing how well the candidate matches the job
- matched_skills: list of skills from the resume that match the job requirements
- missing_skills: list of important skills from the job description that are NOT in the resume
- summary: a short (1-2 sentence) explanation of the score

Resume data:
---
{resume_data}
---

Job description:
---
{job_description}
---

Return only the JSON object.
"""


def calculate_match_score(resume_data, job_description):
    """Resume data ko job description se compare karta hai, match score deta hai."""
    prompt = MATCH_SCORE_PROMPT.format(
        resume_data=json.dumps(resume_data, ensure_ascii=False),
        job_description=job_description
    )

    try:
        response = call_gemini_with_retry(prompt)
        raw_output = clean_json_response(response.text)
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return {"error": "Gemini se valid JSON nahi mila", "raw_response": response.text}
    except Exception as e:
        return {"error": f"Match scoring failed: {str(e)}"}


def process_resume(file_path, job_description=None):
    """
    Poora pipeline: file -> text -> structured resume data -> (optional) match score
    """
    print(f"\n📄 Processing: {file_path}")

    resume_text = extract_resume_text(file_path)
    if resume_text.startswith("ERROR"):
        return {"error": resume_text}

    print(f"✅ Text mil gaya ({len(resume_text)} characters)")

    print("Step 1: Resume data nikala ja raha hai...")
    resume_data = extract_resume_data(resume_text)

    result = {"resume_data": resume_data}

    if job_description:
        print("Step 2: Job description se match score nikala ja raha hai...")
        match_result = calculate_match_score(resume_data, job_description)
        result["match_result"] = match_result

    print("\n✅ RESULT:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    return result


# ------------- TESTING -------------
if __name__ == "__main__":
    test_file = "sample_resume.pdf"  # <-- isay apni file ke naam se replace karo

    sample_job_description = """
    We are looking for a Python Developer with experience in Flask, REST APIs,
    and cloud deployment. Knowledge of AI/ML APIs is a plus. 2+ years experience required.
    """

    if os.path.exists(test_file):
        process_resume(test_file, job_description=sample_job_description)
    else:
        print(f"❌ File nahi mili: {test_file}")
        print("Ek sample resume is folder mein 'sample_resume.pdf' naam se rakho, ya test_file variable update karo.")
