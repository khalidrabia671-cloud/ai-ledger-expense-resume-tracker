"""
Invoice/Receipt Extractor - Flask API
Updated: Naye extractor.py (Gemini multimodal, Tesseract-free) ke sath kaam karta hai
"""

import os
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename

# extractor.py se humara function import karo
from extractor import process_invoice

# resume_extractor.py se humare functions import karo
from resume_extractor import process_resume

# database.py se user/receipt functions import karo
from database import init_db, create_user, verify_user, get_user_by_id, add_receipt, get_receipts_for_user, get_spending_summary, delete_receipt, add_resume, get_resumes_for_user, delete_resume
from currency_converter import convert_to_pkr
from dateutil import parser as date_parser

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-this-in-production")

# Database ready karo (agar tables nahi hain to bana dega)
init_db()

# Sirf ye file types accept karenge (invoice ke liye)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}

# Resume ke liye allowed types
ALLOWED_RESUME_EXTENSIONS = {"pdf", "docx"}

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
        # Poora pipeline chalao: image/pdf -> Gemini -> structured JSON
        result = process_invoice(filepath)

        if "error" in result:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 422  # 422 = Unprocessable Entity

        return jsonify({
            "success": True,
            "filename": filename,
            "data": result
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


def allowed_resume_file(filename):
    """Check karta hai ke resume file extension allowed hai ya nahi."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_RESUME_EXTENSIONS


@app.route("/extract-resume", methods=["POST"])
def extract_resume():
    """
    Resume extraction endpoint. EK YA MULTIPLE resumes accept karta hai
    (batch support), aur optional job description ke sath match score deta hai.

    Form-data fields:
    - files: ek ya zyada resume files (key naam 'files' rakhna, multiple allowed)
    - job_description: (optional) text field, agar diya to match score bhi milega
    """

    # --- Error Handling 1: Koi file nahi bheji ---
    if "files" not in request.files:
        return jsonify({
            "success": False,
            "error": "Koi file nahi mili. Request mein 'files' field ke sath ek ya zyada resumes bhejo."
        }), 400

    files = request.files.getlist("files")

    if len(files) == 0 or all(f.filename == "" for f in files):
        return jsonify({
            "success": False,
            "error": "Koi file select nahi hui."
        }), 400

    # Optional job description
    job_description = request.form.get("job_description", None)

    results = []

    for file in files:
        if file.filename == "":
            continue

        # --- Error Handling 2: Galat file type ---
        if not allowed_resume_file(file.filename):
            results.append({
                "filename": file.filename,
                "success": False,
                "error": f"Ye file type support nahi hai. Sirf allow hai: {', '.join(ALLOWED_RESUME_EXTENSIONS)}"
            })
            continue

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        try:
            result = process_resume(filepath, job_description=job_description)

            if "error" in result:
                results.append({
                    "filename": filename,
                    "success": False,
                    "error": result["error"]
                })
            else:
                results.append({
                    "filename": filename,
                    "success": True,
                    "data": result
                })

        except Exception as e:
            results.append({
                "filename": filename,
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            })

        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    return jsonify({
        "success": True,
        "total_processed": len(results),
        "results": results
    }), 200


def login_required(f):
    """
    Decorator jo check karta hai user login hai ya nahi.
    Agar nahi hai, login page pe bhej deta hai.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Naya account banane ka page."""
    if request.method == "GET":
        return render_template("signup.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not username or not email or not password:
        return render_template("signup.html", error="Saari fields fill karna zaroori hai.")

    if len(password) < 6:
        return render_template("signup.html", error="Password kam se kam 6 characters ka hona chahiye.")

    success, message = create_user(username, email, password)

    if not success:
        return render_template("signup.html", error=message)

    # Signup ke baad seedha login kar do
    user = verify_user(username, password)
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return redirect(url_for("dashboard_home"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    user = verify_user(username, password)

    if not user:
        return render_template("login.html", error="Username ya password galat hai.")

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return redirect(url_for("dashboard_home"))


@app.route("/logout")
def logout():
    """User ko logout karta hai."""
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard_home():
    """Web dashboard ka home page - receipt history aur spending chart ke sath."""
    receipts = get_receipts_for_user(session["user_id"])
    total_spent_pkr = sum(r["total_pkr"] for r in receipts if r["total_pkr"])

    # Chart ke liye data taiyar karo
    summary = get_spending_summary(session["user_id"])
    chart_labels = [s["receipt_date"] for s in summary]
    chart_values = [s["day_total"] for s in summary]

    return render_template(
        "home.html",
        receipts=receipts,
        total_spent=total_spent_pkr,
        username=session.get("username"),
        chart_labels=chart_labels,
        chart_values=chart_values
    )


@app.route("/dashboard/invoice", methods=["GET", "POST"])
@login_required
def dashboard_invoice():
    """
    Invoice extractor ka web page. GET par form dikhata hai,
    POST par file process karke result dikhata hai AUR database mein save karta hai.
    """
    if request.method == "GET":
        return render_template("invoice.html")

    # POST: file upload handle karo
    if "file" not in request.files or request.files["file"].filename == "":
        return render_template("invoice.html", error="Koi file select nahi hui. Sahi file choose karo.")

    file = request.files["file"]

    if not allowed_file(file.filename):
        return render_template("invoice.html", error=f"Ye file type support nahi hai. Sirf allow hai: {', '.join(ALLOWED_EXTENSIONS)}")

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        result = process_invoice(filepath)
        if "error" in result:
            return render_template("invoice.html", error=result["error"])

        # Currency ko PKR mein convert karo (free live exchange rate se)
        total_pkr = convert_to_pkr(result.get("total"), result.get("currency"))

        # Date ko ek standard (ISO) format mein bhi parse karo, sahi sorting ke liye
        # (kyunke receipts mein date alag alag formats mein aati hai)
        receipt_date_iso = None
        raw_date = result.get("date")
        if raw_date:
            try:
                receipt_date_iso = date_parser.parse(raw_date, fuzzy=True).strftime("%Y-%m-%d")
            except (ValueError, OverflowError):
                receipt_date_iso = None  # Agar date samajh na aaye, sorting mein skip ho jayegi

        # Database mein save karo, is user se linked
        add_receipt(
            user_id=session["user_id"],
            vendor=result.get("vendor"),
            receipt_date=result.get("date"),
            total=result.get("total"),
            currency=result.get("currency"),
            items=result.get("items", []),
            filename=filename,
            total_pkr=total_pkr,
            receipt_date_iso=receipt_date_iso
        )

        return render_template("invoice.html", data=result, saved=True)
    except Exception as e:
        return render_template("invoice.html", error=f"Unexpected error: {str(e)}")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route("/dashboard/resume", methods=["GET", "POST"])
@login_required
def dashboard_resume():
    """
    Resume extractor ka web page. GET par form + history dikhata hai,
    POST par file process karke result dikhata hai AUR database mein save karta hai.
    """
    if request.method == "GET":
        resumes = get_resumes_for_user(session["user_id"])
        return render_template("resume.html", resumes=resumes)

    if "file" not in request.files or request.files["file"].filename == "":
        return render_template("resume.html", error="Koi file select nahi hui. Sahi resume choose karo.", resumes=get_resumes_for_user(session["user_id"]))

    file = request.files["file"]

    if not allowed_resume_file(file.filename):
        return render_template("resume.html", error=f"Ye file type support nahi hai. Sirf allow hai: {', '.join(ALLOWED_RESUME_EXTENSIONS)}", resumes=get_resumes_for_user(session["user_id"]))

    job_description = request.form.get("job_description", "").strip() or None

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        result = process_resume(filepath, job_description=job_description)
        if "error" in result:
            return render_template("resume.html", error=result["error"], resumes=get_resumes_for_user(session["user_id"]))

        resume_data = result.get("resume_data", {})
        match_result = result.get("match_result")

        # Database mein save karo, is user se linked
        add_resume(
            user_id=session["user_id"],
            candidate_name=resume_data.get("name"),
            email=resume_data.get("email"),
            phone=resume_data.get("phone"),
            skills=resume_data.get("skills", []),
            experience=resume_data.get("experience", []),
            education=resume_data.get("education", []),
            job_description=job_description,
            match_score=match_result.get("match_score") if match_result else None,
            match_summary=match_result.get("summary") if match_result else None,
            filename=filename
        )

        return render_template(
            "resume.html",
            data=resume_data,
            match=match_result,
            resumes=get_resumes_for_user(session["user_id"])
        )
    except Exception as e:
        return render_template("resume.html", error=f"Unexpected error: {str(e)}", resumes=get_resumes_for_user(session["user_id"]))
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route("/dashboard/delete-resume/<int:resume_id>", methods=["POST"])
@login_required
def delete_resume_route(resume_id):
    """Ek resume ko delete karta hai (sirf logged-in user ki apni resume)."""
    delete_resume(resume_id, session["user_id"])
    return redirect(url_for("dashboard_resume"))


@app.route("/dashboard/delete-receipt/<int:receipt_id>", methods=["POST"])
@login_required
def delete_receipt_route(receipt_id):
    """Ek receipt ko delete karta hai (sirf logged-in user ki apni receipt)."""
    delete_receipt(receipt_id, session["user_id"])
    return redirect(url_for("dashboard_home"))


@app.route("/dashboard/report")
@login_required
def download_report():
    """User ki saari receipts ka PDF report generate kar ke download karta hai."""
    from io import BytesIO
    from flask import send_file
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT

    receipts = get_receipts_for_user(session["user_id"])
    total_pkr = sum(r["total_pkr"] for r in receipts if r["total_pkr"])

    VIOLET = colors.HexColor("#6D3FF0")
    INK = colors.HexColor("#1A1633")
    INK_SOFT = colors.HexColor("#6B6684")
    HEADER_BG = colors.HexColor("#1A1633")
    LIGHT_ROW = colors.HexColor("#F5F3FC")
    LINE = colors.HexColor("#E5E1F5")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.7*inch, bottomMargin=0.7*inch,
        leftMargin=0.65*inch, rightMargin=0.65*inch
    )

    # Har style mein 'leading' explicitly set kiya hai (font size ke hisaab se)
    # taake overlapping na ho - ye reportlab ka common bug hai
    brand_style = ParagraphStyle("Brand", fontName="Helvetica-Bold", fontSize=12, leading=14, textColor=VIOLET)
    title_style = ParagraphStyle("TitleStyle", fontName="Helvetica-Bold", fontSize=24, leading=30, textColor=INK, alignment=TA_LEFT)
    subtitle_style = ParagraphStyle("SubtitleStyle", fontName="Helvetica", fontSize=10, leading=14, textColor=INK_SOFT)
    section_style = ParagraphStyle("SectionHead", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=INK)
    total_label_style = ParagraphStyle("TotalLabel", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.white)
    total_value_style = ParagraphStyle("TotalValue", fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=colors.white)
    footer_style = ParagraphStyle("Footer", fontName="Helvetica", fontSize=8, leading=11, textColor=INK_SOFT)

    story = []

    # --- Header ---
    story.append(Paragraph("LEDGER", brand_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Expense Report", title_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Prepared for {session.get('username')} &nbsp;·&nbsp; {datetime.now().strftime('%d %B %Y')}", subtitle_style))
    story.append(Spacer(1, 24))

    # --- Total banner ---
    total_banner = Table(
        [[Paragraph("TOTAL SPENDING", total_label_style)],
         [Paragraph(f"Rs {total_pkr:,.2f}", total_value_style)]],
        colWidths=[6.6*inch]
    )
    total_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), VIOLET),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("TOPPADDING", (0, 0), (-1, 0), 16),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 18),
    ]))
    story.append(total_banner)
    story.append(Spacer(1, 28))

    # --- Transactions section ---
    story.append(Paragraph("Transactions", section_style))
    story.append(Spacer(1, 10))

    if receipts:
        table_data = [["VENDOR", "DATE", "ORIGINAL", "AMOUNT (PKR)"]]
        for r in receipts:
            original = f"{r['currency'] or ''} {r['total'] or '-'}"
            pkr = f"Rs {r['total_pkr']:,.2f}" if r["total_pkr"] else "-"
            table_data.append([r["vendor"] or "-", r["receipt_date"] or "-", original, pkr])

        table = Table(table_data, colWidths=[2.2*inch, 1.4*inch, 1.4*inch, 1.4*inch], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9.5),
            ("GRID", (0, 1), (-1, -1), 0.5, LINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_ROW]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No receipts recorded yet.", subtitle_style))

    story.append(Spacer(1, 32))
    story.append(Paragraph("Generated automatically by Ledger — AI-powered expense tracking.", footer_style))

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="expense_report.pdf",
        mimetype="application/pdf"
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
