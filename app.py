"""Web-Based Student Academic Requisition Form with PDF Generation (Streamlit)."""
import os
import re
from datetime import date

import pandas as pd
import streamlit as st

import db
from pdf_generator import APP_TYPES, DECLARATION, generate_pdf

st.set_page_config(page_title="Student Academic Requisition Form", page_icon="📝", layout="centered")
db.init_db()

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
MOBILE_RE = re.compile(r"^[6-9]\d{9}$")  # Indian 10-digit mobile number
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # change before deploying


def validate(f: dict, accepted: bool) -> list:
    errors = []
    required = {"department": "Name of Department", "student_name": "Student Name",
                "roll_no": "Roll Number", "semester": "Semester", "division": "Division",
                "purpose": "Purpose / Brief Details"}
    for key, label in required.items():
        if not f[key].strip():
            errors.append(f"{label} is required.")
    if not f["email"].strip():
        errors.append("Email is required.")
    elif not EMAIL_RE.match(f["email"].strip()):
        errors.append("Enter a valid email address (example: name@gmail.com).")
    if not f["mobile"].strip():
        errors.append("Mobile number is required.")
    elif not MOBILE_RE.match(f["mobile"].strip()):
        errors.append("Mobile number must be exactly 10 digits and start with 6, 7, 8 or 9.")
    if f["docs_attached"] == "Yes" and not f["doc_names"].strip():
        errors.append("Please write the name(s) of the supporting document(s).")
    if not accepted:
        errors.append("You must accept the Student Declaration.")
    return errors


def pdf_filename(roll: str, name: str) -> str:
    clean = lambda s: re.sub(r"[^A-Za-z0-9]+", "_", s.strip()).strip("_")
    return f"Requisition_{clean(roll)}_{clean(name)}.pdf"


# ---------------------------------------------------------------- student page
def student_page():
    st.title("Student Academic Requisition Form")
    st.caption("Fill the form, accept the declaration and download your PDF.")

    with st.form("req_form"):
        st.subheader("1. Student Details")
        department = st.text_input("Name of Department *")
        student_name = st.text_input("Student Name *")
        c1, c2, c3 = st.columns(3)
        roll_no = c1.text_input("Roll Number *")
        semester = c2.selectbox("Semester *", ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"])
        division = c3.text_input("Division *", max_chars=3)
        c4, c5 = st.columns(2)
        email = c4.text_input("Email *")
        mobile = c5.text_input("Mobile Number *", max_chars=10)
        app_type = st.radio("Application for *", APP_TYPES, horizontal=True)

        st.subheader("2. Purpose / Brief Details of Request")
        purpose = st.text_area("Purpose *", max_chars=450, height=120)

        st.subheader("3. Supporting Documents")
        docs_attached = st.radio("Documents attached?", ["Yes", "No"], index=1, horizontal=True)
        doc_names = st.text_input("Document name(s), if applicable", max_chars=150)

        st.subheader("4. Student Declaration")
        st.info(DECLARATION)
        accepted = st.checkbox("I accept the above declaration.")
        sig_file = st.file_uploader("Student signature (optional, PNG/JPG)", type=["png", "jpg", "jpeg"])
        form_date = st.date_input("Date", value=date.today(), format="DD/MM/YYYY")

        submitted = st.form_submit_button("Generate PDF", type="primary")

    if submitted:
        data = dict(department=department.strip(), student_name=student_name.strip(),
                    roll_no=roll_no.strip(), semester=semester, division=division.strip().upper(),
                    email=email.strip(), mobile=mobile.strip(), app_type=app_type,
                    purpose=purpose.strip(), docs_attached=docs_attached,
                    doc_names=doc_names.strip() if docs_attached == "Yes" else "",
                    form_date=form_date.strftime("%d-%m-%Y"),
                    signature=sig_file.getvalue() if sig_file else None)
        errors = validate(data, accepted)
        if errors:
            st.session_state.pop("result", None)
            for e in errors:
                st.error(e)
        else:
            data["req_no"] = db.save_requisition(data)
            st.session_state["result"] = (data["req_no"], generate_pdf(data),
                                          pdf_filename(data["roll_no"], data["student_name"]))

    if "result" in st.session_state:
        req_no, pdf_bytes, fname = st.session_state["result"]
        st.success(f"Form submitted. Your requisition number is **{req_no}**. Keep it for status tracking.")
        st.download_button("Download PDF", pdf_bytes, file_name=fname, mime="application/pdf")


# ---------------------------------------------------------------- status page
def status_page():
    st.title("Track Application Status")
    req_no = st.text_input("Enter your Requisition Number (example: REQ-2026-0001)")
    if st.button("Check status") and req_no:
        rec = db.get_by_req_no(req_no.upper())
        if rec:
            st.success(f"**{rec['req_no']}** - {rec['app_type']} - Status: **{rec['status']}**")
        else:
            st.error("No application found with this number.")


# ---------------------------------------------------------------- admin page
def admin_page():
    st.title("Admin Dashboard")
    if not st.session_state.get("admin_ok"):
        pw = st.text_input("Admin password", type="password")
        if st.button("Login"):
            if pw == ADMIN_PASSWORD:
                st.session_state["admin_ok"] = True
                st.rerun()
            else:
                st.error("Wrong password.")
        return

    search = st.text_input("Search (requisition no, name, roll no, type, department)")
    rows = db.list_requisitions(search)
    st.write(f"{len(rows)} record(s)")
    if rows:
        df = pd.DataFrame(rows).drop(columns=["signature"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Download all as CSV", df.to_csv(index=False).encode(), "requisitions.csv", "text/csv")

        st.subheader("Update status / re-download PDF")
        pick = st.selectbox("Requisition", [r["req_no"] for r in rows])
        rec = next(r for r in rows if r["req_no"] == pick)
        new_status = st.selectbox("Status", db.STATUSES, index=db.STATUSES.index(rec["status"]))
        if st.button("Save status"):
            db.update_status(pick, new_status)
            st.success("Status updated.")
            st.rerun()
        st.download_button("Download PDF of this record", generate_pdf(rec),
                           file_name=pdf_filename(rec["roll_no"], rec["student_name"]),
                           mime="application/pdf")


page = st.sidebar.radio("Menu", ["Fill Requisition Form", "Track Status", "Admin Dashboard"])
{"Fill Requisition Form": student_page, "Track Status": status_page, "Admin Dashboard": admin_page}[page]()
