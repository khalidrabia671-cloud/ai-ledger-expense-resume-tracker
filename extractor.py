"""
Invoice/Receipt Data Extractor - Core Logic
Day 2: OCR se text nikalna + Gemini se structured data banana
"""

import os
import json
from dotenv import load_dotenv
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from PyPDF2 import PdfReader
from google import genai

# .env file se API key load karo
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)


def preprocess_image(img):
    """
    OCR accuracy behtar karne ke liye image ko clean karta hai:
    grayscale + resize (bara) + sharpen + contrast.
    Receipts mein chhoti/tight numbers ke liye ye zaroori hai.
    """
    # Grayscale mein convert karo
    img = img.convert("L")

    # Image ko bara karo (2x) - chhote text ko OCR behtar parhta hai
    width, height = img.size
    img = img.resize((width * 2, height * 2), Image.LANCZOS)

    # Halka sharpen karo
    img = img.filter(ImageFilter.SHARPEN)

    # Auto-contrast lagao taake faint numbers bhi clear hon
    img = ImageOps.autocontrast(img)

    return img


def extract_text_from_image(image_path):
    """
    Image (JPG/PNG) se OCR ke zariye text nikalta hai.
    Pehle image preprocess karta hai taake accuracy behtar ho.
    """
    try:
        img = Image.open(image_path)
        img = preprocess_image(img)

        # --psm 6: treat image as a single uniform block of text
        # Ye receipts/invoices ke columns ke liye behtar kaam karta hai
        custom_config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, config=custom_config)
        return text.strip()
    except Exception as e:
        return f"ERROR reading image: {e}"


def extract_text_from_pdf(pdf_path):
    """
    PDF se text nikalta hai (agar PDF text-based hai, scanned image nahi).
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"ERROR reading PDF: {e}"


def extract_text(file_path):
    """
    File ka type dekh kar sahi extraction function call karta hai.
    """
    ext = file_path.lower().split(".")[-1]
    if ext in ["jpg", "jpeg", "png"]:
        return extract_text_from_image(file_path)
    elif ext == "pdf":
        return extract_text_from_pdf(file_path)
    else:
        return f"ERROR: Unsupported file type .{ext}"


def get_structured_data(raw_text):
    """
    Raw OCR text ko Gemini ko bhejta hai aur structured JSON wapas mangta hai.
    """
    prompt = f"""You are an invoice/receipt data extraction assistant.
Extract the following fields from the text below and return ONLY valid JSON,
with no extra explanation, no markdown formatting, no ```json fences.

Fields to extract:
- vendor: the name of the store/company (string)
- date: the invoice/receipt date (string, keep original format)
- total: the FINAL amount actually paid (number, no currency symbol)
- currency: the currency symbol or code if visible (string, e.g. "PKR", "$")
- items: a list of items, each with "name" and "price" (list of objects)

IMPORTANT RULES for "total":
- Receipts often show MULTIPLE amounts labeled "SUBTOTAL" (before discounts) and one final "TOTAL".
- Always use the value next to the line that says exactly "TOTAL" (not "SUBTOTAL").
- If there is a discount/loyalty line, the correct total is AFTER the discount is applied, not before.
- Do not confuse "SUBTOTAL", "CASH", or "CHANGE" with "TOTAL".

If a field cannot be found, use null for that field.

Text to extract from:
---
{raw_text}
---

Return only the JSON object.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    raw_output = response.text.strip()

    # Kabhi kabhi model ```json fences add kar deta hai, unhe hata dete hain
    if raw_output.startswith("```"):
        raw_output = raw_output.split("```")[1]
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()

    try:
        data = json.loads(raw_output)
        return data
    except json.JSONDecodeError:
        return {"error": "Gemini se valid JSON nahi mila", "raw_response": raw_output}


def process_invoice(file_path):
    """
    Poora pipeline: file -> OCR text -> structured JSON
    """
    print(f"\n📄 Processing: {file_path}")

    print("Step 1: Text extract ho raha hai (OCR)...")
    raw_text = extract_text(file_path)

    if raw_text.startswith("ERROR"):
        print(f"❌ {raw_text}")
        return None

    print(f"✅ Text mil gaya ({len(raw_text)} characters)")
    print("\n--- Raw extracted text (preview) ---")
    print(raw_text[:300] + ("..." if len(raw_text) > 300 else ""))

    print("\nStep 2: Gemini se structured data nikala ja raha hai...")
    structured = get_structured_data(raw_text)

    print("\n✅ RESULT:")
    print(json.dumps(structured, indent=2, ensure_ascii=False))

    return structured


# ------------- TESTING -------------
if __name__ == "__main__":
    # Yahan apni sample invoice/receipt ka path likho
    test_file = "sample_invoice2.jpg"  # <-- isay apni file ke naam se replace karo

    if os.path.exists(test_file):
        process_invoice(test_file)
    else:
        print(f"❌ File nahi mili: {test_file}")
        print("Ek sample invoice/receipt image is folder mein 'sample_invoice.jpg' naam se rakho, ya test_file variable update karo.")
