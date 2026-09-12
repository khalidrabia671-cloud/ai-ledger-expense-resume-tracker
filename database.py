"""
Database Module - SQLite se users aur receipts manage karta hai
Phase 1: Database + User Model
"""

import sqlite3
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "database.db"


def get_connection():
    """Database se connection banata hai."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Rows ko dictionary jaisa access karne ke liye
    return conn


def init_db():
    """
    Database aur tables banata hai (agar pehle se nahi hain).
    Ye app shuru hote waqt ek dafa call hoga.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Receipts table - har receipt ek user se linked hogi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vendor TEXT,
            receipt_date TEXT,
            receipt_date_iso TEXT,
            total REAL,
            currency TEXT,
            total_pkr REAL,
            items_json TEXT,
            filename TEXT,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Resumes table - har resume ek user se linked hogi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            candidate_name TEXT,
            email TEXT,
            phone TEXT,
            skills_json TEXT,
            experience_json TEXT,
            education_json TEXT,
            job_description TEXT,
            match_score INTEGER,
            match_summary TEXT,
            filename TEXT,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized (users + receipts + resumes tables ready)")


# ------------- USER FUNCTIONS -------------

def create_user(username, email, password):
    """
    Naya user banata hai. Password ko hash kar ke store karta hai
    (kabhi bhi plain text password store nahi karte, security ke liye).
    Return: (success: bool, message: str)
    """
    conn = get_connection()
    cursor = conn.cursor()

    password_hash = generate_password_hash(password)
    created_at = datetime.now().isoformat()

    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, created_at)
        )
        conn.commit()
        return True, "User created successfully"
    except sqlite3.IntegrityError:
        return False, "Username or email already exists"
    finally:
        conn.close()


def verify_user(username, password):
    """
    Login credentials check karta hai.
    Return: user dict agar sahi hain, warna None
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        return dict(user)
    return None


def get_user_by_id(user_id):
    """User ki details ID se nikalta hai."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


# ------------- RECEIPT FUNCTIONS -------------

def add_receipt(user_id, vendor, receipt_date, total, currency, items, filename, total_pkr=None, receipt_date_iso=None):
    """Naya receipt record database mein save karta hai."""
    conn = get_connection()
    cursor = conn.cursor()

    items_json = json.dumps(items, ensure_ascii=False)
    uploaded_at = datetime.now().isoformat()

    cursor.execute(
        """INSERT INTO receipts (user_id, vendor, receipt_date, receipt_date_iso, total, currency, total_pkr, items_json, filename, uploaded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, vendor, receipt_date, receipt_date_iso, total, currency, total_pkr, items_json, filename, uploaded_at)
    )
    conn.commit()
    receipt_id = cursor.lastrowid
    conn.close()
    return receipt_id


def get_receipts_for_user(user_id):
    """Ek user ki saari receipts list karta hai, sabse nayi date pehle (date na ho unhe aakhir mein)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM receipts WHERE user_id = ?
           ORDER BY (receipt_date_iso IS NULL), receipt_date_iso DESC""",
        (user_id,)
    )
    receipts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # items_json ko wapas list mein convert karo
    for r in receipts:
        try:
            r["items"] = json.loads(r["items_json"])
        except (json.JSONDecodeError, TypeError):
            r["items"] = []

    return receipts


def delete_receipt(receipt_id, user_id):
    """
    Ek receipt delete karta hai - lekin sirf agar wo isi user ki ho
    (security: koi doosre user ka data delete na kar sake).
    Return: True agar delete hui, False agar nahi mili/uski nahi thi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM receipts WHERE id = ? AND user_id = ?",
        (receipt_id, user_id)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_spending_summary(user_id):
    """
    User ki spending ko date ke hisaab se group karta hai
    (chart banane ke liye - Phase 5 mein use hoga).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT receipt_date, receipt_date_iso, SUM(total_pkr) as day_total
           FROM receipts WHERE user_id = ? AND receipt_date_iso IS NOT NULL AND total_pkr IS NOT NULL
           GROUP BY receipt_date_iso ORDER BY receipt_date_iso""",
        (user_id,)
    )
    summary = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return summary


# ------------- RESUME FUNCTIONS -------------

def add_resume(user_id, candidate_name, email, phone, skills, experience, education,
                job_description, match_score, match_summary, filename):
    """Naya resume record database mein save karta hai."""
    conn = get_connection()
    cursor = conn.cursor()

    uploaded_at = datetime.now().isoformat()

    cursor.execute(
        """INSERT INTO resumes (user_id, candidate_name, email, phone, skills_json,
           experience_json, education_json, job_description, match_score, match_summary,
           filename, uploaded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, candidate_name, email, phone,
         json.dumps(skills, ensure_ascii=False),
         json.dumps(experience, ensure_ascii=False),
         json.dumps(education, ensure_ascii=False),
         job_description, match_score, match_summary, filename, uploaded_at)
    )
    conn.commit()
    resume_id = cursor.lastrowid
    conn.close()
    return resume_id


def get_resumes_for_user(user_id):
    """Ek user ki saari resumes list karta hai, sabse nayi pehle."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC",
        (user_id,)
    )
    resumes = [dict(row) for row in cursor.fetchall()]
    conn.close()

    for r in resumes:
        try:
            r["skills"] = json.loads(r["skills_json"]) if r["skills_json"] else []
            r["experience"] = json.loads(r["experience_json"]) if r["experience_json"] else []
            r["education"] = json.loads(r["education_json"]) if r["education_json"] else []
        except (json.JSONDecodeError, TypeError):
            r["skills"], r["experience"], r["education"] = [], [], []

    return resumes


def delete_resume(resume_id, user_id):
    """Ek resume delete karta hai - sirf agar wo isi user ki ho."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM resumes WHERE id = ? AND user_id = ?",
        (resume_id, user_id)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted
