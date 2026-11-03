"""Builds the Student Academic Requisition Form PDF.

Layout follows the institute's official form (A4, 6 numbered sections).
Official-use fields (HoD, Forwarded To, Principal) are drawn blank on purpose.
"""
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

LOGO = Path(__file__).parent / "assets" / "logo.png"
L, R = 40, 555  # left / right margin x
APP_TYPES = ["Bonafide", "Student Certificate", "Scholarship", "NOC",
             "Academic Permission", "Examination", "Internship", "Placement",
             "Other request"]
DECLARATION = ("I certify that the information provided above is correct and that the request "
               "is being submitted for academic purposes. I understand that the request will be "
               "processed as per applicable Institute/University rules and within the stipulated "
               "processing time.")
PROCESSING = ("The request will normally be processed within 4 working days after receiving the "
              "completed form and all required supporting documents. Students are advised to "
              "apply in advance, as incomplete applications may require additional processing time.")


def _safe(text: str) -> str:
    """Helvetica supports Latin-1 only; replace anything else so PDF never crashes."""
    return (text or "").encode("latin-1", "replace").decode("latin-1")


def _label_value(c, x, y, label, value, end_x, size=10):
    """Bold label followed by a value written on an underline that runs to end_x."""
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, label)
    vx = x + stringWidth(label, "Helvetica-Bold", size) + 5
    c.setLineWidth(0.5)
    c.line(vx, y - 2, end_x, y - 2)
    c.setFont("Helvetica", size)
    c.drawString(vx + 2, y, _safe(value))


def _section(c, y, text):
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(L, y, text)


def _checkbox(c, x, y, checked, size=9):
    c.setLineWidth(0.8)
    c.rect(x, y - 1.5, size, size)
    if checked:
        c.setFont("ZapfDingbats", size)
        c.drawString(x + 1, y, "4")  # tick mark


def _paragraph(c, text, x, y, width, font="Helvetica", size=9.5, leading=12.5):
    for line in simpleSplit(text, font, size, width):
        c.setFont(font, size)
        c.drawString(x, y, line)
        y -= leading
    return y


def generate_pdf(d: dict) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Requisition {d.get('req_no', '')}")

    # ---------- Header box ----------
    top, bottom = 810, 752
    c.setLineWidth(1)
    c.rect(L, bottom, R - L, top - bottom)
    c.line(235, bottom, 235, top)
    c.drawImage(ImageReader(str(LOGO)), L + 8, top - 34, width=88, height=88 * 73 / 199,
                mask="auto")
    c.setFont("Helvetica", 6.5)
    c.drawString(L + 6, bottom + 12, "(Autonomous College Affiliated to University of Mumbai)")
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(395, top - 24, "STUDENT ACADEMIC")
    c.drawCentredString(395, top - 42, "REQUISITION FORM")

    # ---------- Department / Outward no / Date ----------
    _label_value(c, L, 730, "Name of the Department.:", d["department"], 320)
    _label_value(c, 335, 730, "Department Outward No.:", "", R)  # filled by institute
    _label_value(c, L, 710, "Date:", d["form_date"], 190)
    if d.get("req_no"):
        c.setFont("Helvetica", 8)
        c.drawRightString(R, 712, f"Requisition No.: {d['req_no']}")

    # ---------- Processing time ----------
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(L, 686, "Processing Time:")
    off = stringWidth("Processing Time: ", "Helvetica-Bold", 9.5)
    lines = simpleSplit("x" * 1 + PROCESSING, "Helvetica", 9.5, R - L - off)  # first-line width
    first = simpleSplit(PROCESSING, "Helvetica", 9.5, R - L - off)[0]
    c.setFont("Helvetica", 9.5)
    c.drawString(L + off, 686, first)
    rest = PROCESSING[len(first):].strip()
    y = _paragraph(c, rest, L, 673.5, R - L)
    c.setLineWidth(0.4)
    c.line(L, y + 6, R, y + 6)

    # ---------- 1. Student details ----------
    _section(c, 630, "1. STUDENT DETAILS")
    _label_value(c, L, 610, "Name of Student:", d["student_name"], R)
    _label_value(c, L, 588, "Roll No.:", d["roll_no"], 190)
    _label_value(c, 215, 588, "Semester:", d["semester"], 330)
    _label_value(c, 355, 588, "Division:", d["division"], R)
    contact = f"{d['email']}  /  {d['mobile']}"
    _label_value(c, L, 566, "Email / Mobile:", contact, R)

    # Application type: same wording as the form, chosen option is boxed + bold
    c.setFont("Helvetica", 10)
    c.drawString(L, 543, "Application for \u2013")
    x, y = L + stringWidth("Application for \u2013 ", "Helvetica", 10), 543
    for i, opt in enumerate(APP_TYPES):
        chosen = opt == d["app_type"]
        font = "Helvetica-Bold" if chosen else "Helvetica"
        sep = " /" if i < len(APP_TYPES) - 1 else "."
        w = stringWidth(opt, font, 10)
        if x + w + 12 > R:
            x, y = L, y - 16
        if chosen:
            c.setLineWidth(0.9)
            c.roundRect(x - 2, y - 3.5, w + 4, 13.5, 2)
        c.setFont(font, 10)
        c.drawString(x, y, opt)
        c.setFont("Helvetica", 10)
        c.drawString(x + w + 1, y, sep)
        x += w + stringWidth(sep, "Helvetica", 10) + 6

    # ---------- 2. Purpose ----------
    _section(c, 487, "2. PURPOSE / BRIEF DETAILS OF REQUEST")
    c.setLineWidth(0.4)
    ly = 468
    wrapped = simpleSplit(_safe(d["purpose"]), "Helvetica", 10, R - L - 4)[:5]
    for i in range(5):
        c.line(L, ly - 3, R, ly - 3)
        if i < len(wrapped):
            c.setFont("Helvetica", 10)
            c.drawString(L + 2, ly, wrapped[i])
        ly -= 18

    # ---------- 3. Supporting documents ----------
    _section(c, 372, "3. SUPPORTING DOCUMENTS")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(L, 352, "Documents attached:")
    yes = d["docs_attached"] == "Yes"
    _checkbox(c, 160, 352, yes); c.setFont("Helvetica", 10); c.drawString(174, 352, "Yes")
    _checkbox(c, 215, 352, not yes); c.drawString(229, 352, "No")
    c.setFont("Helvetica", 10)
    c.drawString(L, 330, "Document name(s), if applicable:")
    names = simpleSplit(_safe(d["doc_names"]), "Helvetica", 10, R - 205)[:2]
    c.setLineWidth(0.5)
    c.line(205, 328, R, 328)
    if names:
        c.drawString(207, 330, names[0])
    if len(names) > 1:
        c.line(L, 312, R, 312)
        c.drawString(L + 2, 314, names[1])

    # ---------- 4. Student declaration ----------
    _section(c, 292, "4. STUDENT DECLARATION")
    y = _paragraph(c, DECLARATION, L, 276, R - L, size=9.5)
    sy = y - 20
    c.setFont("Helvetica", 10)
    c.drawString(L, sy, "Student Signature:")
    sx = L + stringWidth("Student Signature: ", "Helvetica", 10) + 4
    if d.get("signature"):
        try:
            c.drawImage(ImageReader(BytesIO(d["signature"])), sx + 2, sy - 2, width=90, height=26,
                        preserveAspectRatio=True, anchor="sw", mask="auto")
        except Exception:
            pass
    c.line(sx, sy - 2, sx + 105, sy - 2)
    c.drawString(300, sy, "Date:")
    c.line(328, sy - 2, 420, sy - 2)
    c.drawString(331, sy, d["form_date"])

    # ---------- 5. HoD (blank for institute) ----------
    hy = sy - 42
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(L, hy, "5. HoD Signature:")
    c.line(145, hy - 2, 270, hy - 2)
    c.drawString(290, hy, "Remarks:")
    c.line(345, hy - 2, R, hy - 2)
    c.setFont("Helvetica-Bold", 9.5)
    fy = hy - 20
    c.drawString(L, fy, "Forwarded to")
    _paragraph(c, "(VICE PRINCIPAL/ CHIEF ACADEMIC OFFICER/ ACCOUNTS/ SPORTS/ PLACEMENT CELL/ "
                  "SCHOLARSHIP CELL/ EXAM CELL) (if required)", L + 62, fy, R - L - 62,
               font="Helvetica", size=9.5)
    gy = fy - 40
    c.setFont("Helvetica-Bold", 10)
    c.drawString(L, gy, "Signature:")
    c.line(100, gy - 2, 240, gy - 2)
    c.drawString(270, gy, "Remarks:")
    c.line(325, gy - 2, R, gy - 2)

    # ---------- 6. Principal office use only (blank) ----------
    py = gy - 32
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(L, py, "6. PRINCIPAL OFFICE USE ONLY")
    dy = py - 22
    c.setFont("Helvetica", 10)
    c.drawString(L, dy, "Decision by Principal.:")
    x = L + stringWidth("Decision by Principal.: ", "Helvetica", 10) + 8
    for label in ("Approved", "Not Approved", "Clarification Required"):
        _checkbox(c, x, dy, False)
        c.setFont("Helvetica", 10)
        c.drawString(x + 14, dy, label)
        x += 14 + stringWidth(label, "Helvetica", 10) + 22
    ry = dy - 22
    c.drawString(L, ry, "Remarks (if any):")
    c.line(L + 95, ry - 2, R, ry - 2)
    sy2 = ry - 24
    c.drawString(L, sy2, "Principal Signature:")
    c.line(L + 100, sy2 - 2, 300, sy2 - 2)

    c.showPage()
    c.save()
    return buf.getvalue()
