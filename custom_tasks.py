import os
import re
from pdf_utils import query_pdf, PDF_FOLDER
from csv_utils import query_csv, CSV_FOLDER

# ----- Discover available files -----
pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith(".pdf")] if PDF_FOLDER.exists() else []
csv_files = [f for f in os.listdir(CSV_FOLDER) if f.lower().endswith(".csv")] if CSV_FOLDER.exists() else []

# ----- Keywords for structured (CSV) queries -----
CSV_KEYWORDS = [
    "patient", "patientid", "diagnosed", "diagnosis", "treatment", "facility", "clinic",
    "region", "cost", "price", "amount", "bill", "visit", "who was treated", "what is the name of patient with"
]


def _looks_structured(q: str) -> bool:
    ql = (q or "").lower()
    return any(k in ql for k in CSV_KEYWORDS)


def _looks_like_indicator(q: str) -> bool:
    """
    Detect indicator-style codes like ANC1_HTS, ART_INIT, etc.
    Rule: all caps + underscore + optional digits.
    """
    return bool(re.match(r"^[A-Z0-9_]{4,}$", q.strip()))


# ----- Main Router -----
def handle_task(user_input: str) -> str:
    """
    Routing logic:
      1️⃣ Built-in quick answers.
      2️⃣ Indicator-style queries (ANC1_HTS → PDFs).
      3️⃣ Structured queries → CSV first.
      4️⃣ If no CSV match → PDFs.
      5️⃣ Fallback generic answer.
    """
    q = (user_input or "").strip()
    ql = q.lower()

    # ---- Built-in quick answers ----
    if "blood pressure" in ql:
        return "Normal blood pressure is around 120 over 80."
    if "viral load" in ql:
        return "Viral load monitoring helps track HIV treatment success."
    if "data report" in ql:
        return "Fetching your facility's data report..."

    # ---- Case 1: Indicator codes (ANC1_HTS etc.) ----
    if _looks_like_indicator(q):
        for pdf_name in pdf_files:
            try:
                resp = query_pdf(pdf_name, q)
                if resp and "No definition" not in resp and "not found" not in resp:
                    return resp
            except Exception:
                continue

    # ---- Case 2: Structured query → CSVs ----
    if _looks_structured(q):
        csv_any_match = False
        for csv_name in csv_files:
            try:
                resp = query_csv(csv_name, q)
                if isinstance(resp, str) and resp.strip() and "No matching data" not in resp and "❌" not in resp:
                    return resp
                if isinstance(resp, str) and "No matching data" not in resp:
                    csv_any_match = True
            except Exception:
                csv_any_match = csv_any_match or False

        # fallthrough to PDFs if CSVs gave no solid answer

    # ---- Case 3: Fallback → PDFs ----
    for pdf_name in pdf_files:
        try:
            resp = query_pdf(pdf_name, q)
            if isinstance(resp, str) and resp.strip() and "I could not find" not in resp:
                return resp
        except Exception:
            continue

    # ---- Final fallback ----
    return "🤔 I'm not sure how to help with that. Try asking about a patient, a diagnosis, a facility, a region, or an indicator like ANC1_HTS."
