from __future__ import annotations
import re
from pathlib import Path
import pandas as pd

# Folders / defaults
CSV_FOLDER = Path("health_csvs")
CSV_FOLDER.mkdir(exist_ok=True)

# ---- Helpers ----
def _load_csv(csv_filename: str) -> pd.DataFrame:
    csv_path = CSV_FOLDER / csv_filename
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    # Normalize expected columns if they exist
    for col in ["PatientID", "Name", "Diagnosis", "Treatment", "Facility", "Region", "Cost", "VisitDate"]:
        if col in df.columns:
            # Strip spaces
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip()
    # Ensure Cost is numeric
    if "Cost" in df.columns:
        df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce").fillna(0.0)
    return df


def _icontains(series: pd.Series, text: str) -> pd.Series:
    """Case-insensitive contains, safe for NaN."""
    return series.astype(str).str.contains(re.escape(text), case=False, na=False)


def _clean_answer(values) -> str:
    """Join unique non-empty values as a clean string."""
    uniq = [str(v) for v in pd.unique(pd.Series(values)) if str(v).strip()]
    return ", ".join(uniq) if uniq else "No matching data found in CSV."


# ---- Main entry point ----
def query_csv(csv_filename: str, query: str) -> str:
    """
    Rule-based CSV Q&A using pandas filtering (no embeddings).
    Supports:
      • 'What is the treatment for patient P003?'
      • 'Who was treated at Clinic D for Anemia?'
      • 'What is the total cost of treatments in the North region?'
      • 'List all patients diagnosed with Diabetes'
    Falls back to a broad keyword filter if no specific pattern matches.
    """
    try:
        df = _load_csv(csv_filename)
    except Exception as e:
        return f"❌ Error loading CSV: {e}"

    q = (query or "").strip()
    ql = q.lower()

    # ---------- Pattern 1: Treatment for a specific patient ----------
    # e.g., "What is the treatment for patient P003?"
    m = re.search(r"treatment\s+(?:for|of)\s+patient\s+([a-z0-9\-]+)", ql, re.I)
    if m and "PatientID" in df.columns and "Treatment" in df.columns:
        pid = m.group(1).upper()
        row = df[df["PatientID"].str.upper() == pid]
        if not row.empty:
            return str(row.iloc[0]["Treatment"])
        return f"No matching patient {pid} in CSV."

    # ---------- Pattern 2: Who was treated at <Facility> for <Diagnosis> ----------
    # e.g., "Who was treated at Clinic D for Anemia?"
    m = re.search(r"who\s+was\s+treated\s+at\s+(.+?)\s+for\s+(.+?)\??$", ql, re.I)
    if m and {"Facility", "Diagnosis", "Name"}.issubset(df.columns):
        facility = m.group(1).strip()
        diagnosis = m.group(2).strip()
        sub = df[_icontains(df["Facility"], facility) & _icontains(df["Diagnosis"], diagnosis)]
        if not sub.empty:
            return _clean_answer(sub["Name"].tolist())
        return f"No patients treated at '{facility}' for '{diagnosis}'."

    # ---------- Pattern 3: Total cost in/for <Region> region ----------
    # e.g., "What is the total cost of treatments in the North region?"
    m = re.search(r"(?:total\s+cost|sum\s+of\s+costs?).*?(?:in|for)\s+(?:the\s+)?([a-z]+)\s+region", ql, re.I)
    if m and {"Region", "Cost"}.issubset(df.columns):
        region = m.group(1).strip()
        sub = df[_icontains(df["Region"], region)]
        total = float(sub["Cost"].sum()) if not sub.empty else 0.0
        return f"Total cost in {region.capitalize()} region: {total:.2f}"

    # ---------- Pattern 4: List all patients diagnosed with <Diagnosis> ----------
    # e.g., "List all patients diagnosed with Diabetes"
    m = re.search(r"(?:list\s+all\s+)?patients\s+(?:diagnosed\s+with|with)\s+(.+?)\??$", ql, re.I)
    if m and {"Diagnosis", "PatientID", "Name"}.issubset(df.columns):
        dx = m.group(1).strip()
        sub = df[_icontains(df["Diagnosis"], dx)]
        if not sub.empty:
            # Return names (and optionally IDs) as a comma-separated list
            names = sub["Name"].tolist()
            return _clean_answer(names)
        return f"No patients diagnosed with '{dx}'."

    # ---------- Pattern 5: Cost for a specific patient ----------
    m = re.search(r"(?:cost|bill|amount\s+due).*(?:for\s+patient\s+)([a-z0-9\-]+)", ql, re.I)
    if m and {"PatientID", "Cost"}.issubset(df.columns):
        pid = m.group(1).upper()
        row = df[df["PatientID"].str.upper() == pid]
        if not row.empty:
            return f"{float(row.iloc[0]['Cost']):.2f}"
        return f"No matching patient {pid} in CSV."

    # ---------- Broad fallback: keyword filter across key columns ----------
    cols = [c for c in ["PatientID", "Name", "Diagnosis", "Treatment", "Facility", "Region"] if c in df.columns]
    if cols:
        mask = False
        # Split query into words >3 chars to avoid noise
        tokens = [t for t in re.split(r"\W+", ql) if len(t) > 3]
        for t in tokens:
            term_mask = False
            for c in cols:
                term_mask = term_mask | _icontains(df[c], t)
            mask = term_mask if isinstance(mask, bool) else (mask & term_mask)

        sub = df[mask] if not isinstance(mask, bool) else pd.DataFrame()
        if not sub.empty:
            # Prefer returning Names if available, otherwise PatientIDs
            if "Name" in sub.columns:
                return _clean_answer(sub["Name"].tolist())
            if "PatientID" in sub.columns:
                return _clean_answer(sub["PatientID"].tolist())

    return "No matching data found in CSV."
