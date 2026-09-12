"""
Invoice/Receipt Data Extractor - Core Logic
Updated: Ab Tesseract OCR ki zaroorat nahi - Gemini seedha image dekh kar
structured data nikalta hai (multimodal AI). Isse deployment simple ho jati hai.
"""

import os
import json
import base64
import time
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from google import genai
from google.genai import types

# .env file se API key load karo
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

EXTRACTION_PROMPT = """You are an invoice/receipt data extraction assistant.
Look at this invoice/receipt and extract the following fields.
Return ONLY valid JSON, with no extra explanation, no markdown formatting, no ```json fences.

Fields to extract:
- vendor: the name of the store/company (string)
- date: the invoice/receipt date (string, keep original format)
- total: the FINAL amount actually paid (number, no currency symbol)
- currency: the ISO currency CODE (e.g. "USD", "PKR", "EUR", "GBP"), not a symbol.
  If you see "$" assume "USD" unless context suggests otherwise (e.g. "Rs" or "₨" means "PKR").
- items: a list of items, each with "name" and "price" (list of objects)

IMPORTANT RULES for "total":
- Receipts often show MULTIPLE amounts labeled "SUBTOTAL" (before discounts) and one final "TOTAL".
- Always use the value next to the line that says exactly "TOTAL" (not "SUBTOTAL").
- If there is a discount/loyalty line, the correct total is AFTER the discount is applied, not before.
- Do not confuse "SUBTOTAL", "CASH", or "CHANGE" with "TOTAL".

If a field cannot be found, use null for that field.
Return only the JSON object.
"""


def clean_json_response(raw_output):
    """Gemini kabhi kabhi ```json fences add kar deta hai, unhe hata dete hain."""
    raw_output = raw_output.strip()
    if raw_output.startswith("```"):
        raw_output = raw_output.split("```")[1]
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()
    return raw_output


def call_gemini_with_retry(contents, max_retries=4):
    """
    Gemini ko call karta hai. Agar ek model busy (503) ho, to
    dusre (halke/faster) model par switch kar ke try karta hai,
    saath mein thora wait bhi karta hai (exponential backoff).
    """
    # In dono models ke beech switch karenge - agar ek busy ho to dusra try karo
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
                wait_time = 2 ** attempt  # 1s, 2s, 4s, 8s...
                print(f"⏳ {model_name} busy hai, {wait_time}s mein dusre model se dobara try kar raha hoon... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise  # Agar retryable nahi hai, ya sab attempts khatam ho gaye, error aage bhej do

    raise Exception("Gemini se connect nahi ho paya, sab retries fail ho gaye")


def get_mime_type(file_path):
    """File extension se mime type nikalta hai."""
    ext = file_path.lower().split(".")[-1]
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
    return mime_map.get(ext, "image/jpeg")


def process_image(image_path):
    """
    Image (JPG/PNG) ko seedha Gemini ko bhejta hai - koi separate OCR step nahi.
    Gemini khud image dekh kar structured data nikalta hai.
    """
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        mime_type = get_mime_type(image_path)

        response = call_gemini_with_retry([
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            EXTRACTION_PROMPT,
        ])

        raw_output = clean_json_response(response.text)
        return json.loads(raw_output)

    except json.JSONDecodeError:
        return {"error": "Gemini se valid JSON nahi mila", "raw_response": response.text}
    except Exception as e:
        return {"error": f"Image processing failed: {str(e)}"}


def process_pdf(pdf_path):
    """
    PDF se text nikal kar (agar text-based PDF hai) Gemini ko bhejta hai.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        text = text.strip()

        if len(text) == 0:
            return {"error": "PDF se koi text nahi mila. Ye scanned/image-based PDF ho sakta hai."}

        response = call_gemini_with_retry(
            f"{EXTRACTION_PROMPT}\n\nText to extract from:\n---\n{text}\n---"
        )

        raw_output = clean_json_response(response.text)
        return json.loads(raw_output)

    except json.JSONDecodeError:
        return {"error": "Gemini se valid JSON nahi mila", "raw_response": response.text}
    except Exception as e:
        return {"error": f"PDF processing failed: {str(e)}"}


def process_invoice(file_path):
    """
    Poora pipeline: file type dekh kar sahi function call karta hai.
    """
    ext = file_path.lower().split(".")[-1]

    print(f"\n📄 Processing: {file_path}")

    if ext in ["jpg", "jpeg", "png"]:
        result = process_image(file_path)
    elif ext == "pdf":
        result = process_pdf(file_path)
    else:
        result = {"error": f"Unsupported file type: .{ext}"}

    print("\n✅ RESULT:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Ek readable "items_summary" field bhi add karo, taake Google Sheets
    # jaisi jagah par ye clean text ki tarah dikhe (JSON ki jagah)
    if isinstance(result, dict) and "items" in result and isinstance(result["items"], list):
        currency = result.get("currency") or ""
        parts = []
        for item in result["items"]:
            name = item.get("name", "Unknown")
            price = item.get("price")
            if price is not None:
                parts.append(f"{name} ({currency}{price})")
            else:
                parts.append(name)
        result["items_summary"] = ", ".join(parts)

    return result


# ------------- TESTING -------------
if __name__ == "__main__":
    test_file = "sample_invoice.jpg"

    if os.path.exists(test_file):
        process_invoice(test_file)
    else:
        print(f"❌ File nahi mili: {test_file}")
