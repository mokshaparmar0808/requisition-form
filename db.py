"""SQLite storage for requisitions."""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "requisitions.db"

STATUSES = ["Pending", "Forwarded", "Approved", "Not Approved", "Clarification Required"]


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS requisitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                req_no TEXT UNIQUE,
                department TEXT, student_name TEXT, roll_no TEXT,
                semester TEXT, division TEXT, email TEXT, mobile TEXT,
                app_type TEXT, purpose TEXT,
                docs_attached TEXT, doc_names TEXT,
                form_date TEXT, signature BLOB,
                status TEXT DEFAULT 'Pending',
                created_at TEXT
            )"""
        )


def save_requisition(d: dict) -> str:
    """Insert a record and return the auto-generated requisition number."""
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO requisitions
               (department, student_name, roll_no, semester, division, email, mobile,
                app_type, purpose, docs_attached, doc_names, form_date, signature, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d["department"], d["student_name"], d["roll_no"], d["semester"], d["division"],
             d["email"], d["mobile"], d["app_type"], d["purpose"], d["docs_attached"],
             d["doc_names"], d["form_date"], d.get("signature"),
             datetime.now().isoformat(timespec="seconds")),
        )
        req_no = f"REQ-{datetime.now().year}-{cur.lastrowid:04d}"
        c.execute("UPDATE requisitions SET req_no=? WHERE id=?", (req_no, cur.lastrowid))
    return req_no


def list_requisitions(search: str = ""):
    q = "SELECT * FROM requisitions"
    params = ()
    if search.strip():
        like = f"%{search.strip()}%"
        q += (" WHERE req_no LIKE ? OR student_name LIKE ? OR roll_no LIKE ?"
              " OR app_type LIKE ? OR department LIKE ?")
        params = (like,) * 5
    q += " ORDER BY id DESC"
    with _conn() as c:
        return [dict(r) for r in c.execute(q, params).fetchall()]


def get_by_req_no(req_no: str):
    with _conn() as c:
        r = c.execute("SELECT * FROM requisitions WHERE req_no=?", (req_no.strip(),)).fetchone()
        return dict(r) if r else None


def update_status(req_no: str, status: str):
    with _conn() as c:
        c.execute("UPDATE requisitions SET status=? WHERE req_no=?", (status, req_no))
