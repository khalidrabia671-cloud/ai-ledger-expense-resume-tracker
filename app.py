"""
Invoice/Receipt Extractor - Flask API
Day 3: API endpoint jo file upload accept kare, extraction chalaye, JSON return kare
"""

import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

# extractor.py se humare functions import karo (Day 2 mein bane the)
from extractor import extract_text, get_structured_data

app = Flask(__name__)

# Sirf ye file types accept karenge
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}

# Uploaded files temporarily yahan save hongi
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Max file size: 10 MB (isse bari file reject ho jayegi)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def allowed_file(filename):
    """Check karta hai ke file extension allowed hai ya nahi."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def home():
    """Simple health check - dekhne ke liye ke server chal raha hai."""
    return jsonify({
        "status": "running",
        "message": "Invoice Extractor API is live. POST a file to /extract-invoice"
    })


@app.route("/extract-invoice", methods=["POST"])
def extract_invoice():
    """
    Main endpoint. Ek file (image/pdf) accept karta hai aur
    structured invoice data JSON mein return karta hai.
    """

    # --- Error Handling 1: File bheji hi nahi ---
    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "Koi file nahi mili. Request mein 'file' field ke sath ek file bhejo."
        }), 400

    file = request.files["file"]

    # --- Error Handling 2: File select ki lekin khali bheji ---
    if file.filename == "":
        return jsonify({
            "success": False,
            "error": "File ka naam khali hai. Sahi file select karo."
        }), 400

    # --- Error Handling 3: Galat file type ---
    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "error": f"Ye file type support nahi hai. Sirf allow hai: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    # File ko temporarily save karo
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        # --- Step 1: OCR se text nikalo ---
        raw_text = extract_text(filepath)

        if raw_text.startswith("ERROR"):
            return jsonify({
                "success": False,
                "error": f"Text extraction fail hui: {raw_text}"
            }), 422  # 422 = Unprocessable Entity (blurry/corrupt file)

        if len(raw_text.strip()) == 0:
            return jsonify({
                "success": False,
                "error": "File se koi text nahi mila. Image blurry ho sakti hai ya khali PDF ho sakta hai."
            }), 422

        # --- Step 2: Gemini se structured data nikalo ---
        structured_data = get_structured_data(raw_text)

        return jsonify({
            "success": True,
            "filename": filename,
            "data": structured_data
        }), 200

    except Exception as e:
        # --- Error Handling 4: Koi bhi unexpected error ---
        return jsonify({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }), 500

    finally:
        # Temporary file delete kar do, chahe success ho ya fail
        if os.path.exists(filepath):
            os.remove(filepath)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
