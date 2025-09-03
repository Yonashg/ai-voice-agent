import re
from pathlib import Path
import fitz  # PyMuPDF for direct text scanning (fast for indicator lookup)

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

# ----- Directories -----
VECTORSTORE_DIR = Path("vectorstores")
PDF_FOLDER = Path("health_pdfs")
VECTORSTORE_DIR.mkdir(exist_ok=True)
PDF_FOLDER.mkdir(exist_ok=True)


# ----- PDF Text Extraction -----
def extract_pdf_text(pdf_path: Path) -> str:
    """Extract raw text from a PDF using PyMuPDF (line-based, good for regex)."""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text("text") + "\n"
    except Exception as e:
        return f"❌ Error reading PDF: {e}"
    return text


def semantic_pdf_search(pdf_path: Path) -> str:
    """Extract all text from PDF using LangChain loader (for embeddings)."""
    loader = PyPDFLoader(str(pdf_path))
    pages = loader.load()
    return " ".join([page.page_content for page in pages])


# ----- Regex for totals -----
def find_total_price(text: str) -> str | None:
    """Try to extract total price from PDF text using regex."""
    patterns = [
        r"Total\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",
        r"Grand\s*Total\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",
        r"Amount\s*Due\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",
        r"Total Price\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


# ----- Indicator lookup (ANC1_HTS, ART_INIT, etc.) -----
def lookup_pdf_indicator(pdf_filename: str, code: str) -> str:
    """
    Look up an indicator code (e.g., ANC1_HTS) in a PDF and return surrounding context.
    """
    pdf_path = PDF_FOLDER / pdf_filename
    if not pdf_path.exists():
        return f"❌ PDF not found: {pdf_path}"

    text = extract_pdf_text(pdf_path)
    if not text:
        return "❌ Could not extract text from PDF."

    lines = text.splitlines()
    matches = [line.strip() for line in lines if code in line]

    if matches:
        # Highlight the code for clarity
        highlighted = [m.replace(code, f"**{code}**") for m in matches[:3]]
        return "\n".join(highlighted)

    return f"No definition for '{code}' found in {pdf_filename}."


# ----- Build or Load FAISS Vectorstore -----
def build_or_load_vectorstore(pdf_path: Path):
    """Build or load FAISS vectorstore for a given PDF safely."""
    vectorstore_file = VECTORSTORE_DIR / f"{pdf_path.stem}"

    if vectorstore_file.exists():
        return FAISS.load_local(
            str(vectorstore_file),
            embeddings=OllamaEmbeddings(model="mistral"),
            allow_dangerous_deserialization=True  # local file, safe
        )

    loader = PyPDFLoader(str(pdf_path))
    pages = loader.load()
    embeddings = OllamaEmbeddings(model="mistral")
    vectorstore = FAISS.from_documents(pages, embeddings)
    vectorstore.save_local(str(vectorstore_file))
    return vectorstore


# ----- Query PDF (main entry) -----
def query_pdf(pdf_filename: str, query: str) -> str:
    """
    Query a PDF intelligently:
      1️⃣ Regex extraction (totals, invoices, etc.)
      2️⃣ Indicator code lookup (ANC1_HTS, ART_INIT...)
      3️⃣ FAISS semantic search (general queries)
    """
    pdf_path = PDF_FOLDER / pdf_filename
    if not pdf_path.exists():
        return f"❌ PDF file {pdf_filename} not found."

    # --- Extract plain text for regex + code lookup ---
    text = extract_pdf_text(pdf_path)

    # --- Case 1: total/amount queries ---
    if re.search(r"\b(total|grand total|amount due|total price)\b", query, re.IGNORECASE):
        total = find_total_price(text)
        if total:
            return f"💰 The total price in **{pdf_filename}** is **${total}**."
        else:
            return "⚠️ No total price was detected in the document."

    # --- Case 2: indicator code lookup ---
    if re.match(r"^[A-Z0-9_]+$", query.strip()):  # e.g., ANC1_HTS
        return lookup_pdf_indicator(pdf_filename, query.strip())

    # --- Case 3: semantic search fallback ---
    try:
        vectorstore = build_or_load_vectorstore(pdf_path)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(query)

        if docs:
            answers = []
            for i, doc in enumerate(docs, 1):
                snippet = doc.page_content.strip().replace("\n", " ")
                snippet = snippet[:300] + ("..." if len(snippet) > 300 else "")
                answers.append(f"📄 Result {i}: {snippet}")
            return "\n\n".join(answers)

    except Exception as e:
        return f"❌ Error during semantic search: {str(e)}"

    return f"🤔 I could not find anything relevant to '{query}' in {pdf_filename}."
