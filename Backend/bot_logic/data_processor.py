import os
from database import insert_document
import PyPDF2

# Optional OCR dependencies
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_FOLDER = os.environ.get('STORAGE_FOLDER') or os.path.join(BASE_DIR, 'storage', 'uploads')
os.makedirs(STORAGE_FOLDER, exist_ok=True)


def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for page in reader.pages:
                try:
                    page_text = page.extract_text()
                except Exception:
                    page_text = None
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print("PDF read error:", e)
    return text


def ocr_pdf(file_path):
    """
    Convert PDF pages to images (pdf2image) and OCR them (pytesseract).
    Requires poppler (pdf2image) and tesseract installed on the system.
    """
    if not OCR_AVAILABLE:
        return ""
    try:
        images = convert_from_path(file_path, dpi=200)
    except Exception as e:
        print("pdf2image convert_from_path failed:", e)
        return ""

    text = ""
    for img in images:
        try:
            page_text = pytesseract.image_to_string(img)
            text += page_text + "\n"
        except Exception as e:
            print("pytesseract failed on page:", e)
    return text


def process_and_save_pdf(file_path, filename):
    """
    Extract text (PyPDF2), fallback to OCR if needed, and insert into DB.
    file_path: absolute path where file is stored (we keep it)
    filename: stored filename (basename)
    Returns True on success.
    """
    try:
        text = extract_text_from_pdf(file_path)
        if not text or not text.strip():
            if OCR_AVAILABLE:
                print("No text found with PyPDF2; trying OCR.")
                text = ocr_pdf(file_path)
            else:
                print("No text found and OCR not available.")
        if not text or not text.strip():
            print("No extractable text found in PDF:", filename)
            return False

        # limit to a reasonable size
        max_len = 300000
        if len(text) > max_len:
            text = text[:max_len]

        # Save into DB: filename stored relative (basename)
        insert_document(title=filename, filename=filename, content=text, status='uploaded')
        print(f"Saved PDF content for {filename}.")
        return True
    except Exception as e:
        print("Failed to process PDF:", e)
        return False


def get_document_content_for_query(query, max_chars=2500):
    """
    Returns combined excerpt and first document metadata if any matches.
    """
    try:
        from database import search_documents
        snippets = search_documents(query, max_chars=max_chars, limit=3)
        if not snippets:
            return None
        combined = "\n\n".join([s['excerpt'] for s in snippets])
        if len(combined) > max_chars:
            combined = combined[:max_chars]
        return {'combined': combined, 'first_doc': snippets[0], 'all': snippets}
    except Exception as e:
        print("Error searching documents:", e)
        return None
