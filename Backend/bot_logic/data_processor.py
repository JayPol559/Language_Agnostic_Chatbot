import os
from database import insert_document
import PyPDF2

# Optional OCR
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


def process_and_save_pdf(file_path, saved_filename):
    """
    Extract text, fallback to OCR if needed, then insert into DB.
    We keep the saved file on disk (so it persists until manual deletion).
    """
    try:
        text = extract_text_from_pdf(file_path)
        if not text or not text.strip():
            if OCR_AVAILABLE:
                print("No text via PyPDF2 — trying OCR...")
                text = ocr_pdf(file_path)
            else:
                print("No text and OCR not available.")
        if not text or not text.strip():
            # Insert record with empty content but keep status to indicate no-text
            insert_document(title=saved_filename, filename=saved_filename, content="", status="no_text")
            print("Inserted document record but no text extractable:", saved_filename)
            return False

        max_len = 300000
        if len(text) > max_len:
            text = text[:max_len]

        insert_document(title=saved_filename, filename=saved_filename, content=text, status='uploaded')
        print(f"Saved PDF content for {saved_filename}.")
        return True
    except Exception as e:
        print("Failed to process PDF:", e)
        return False


def get_document_content_for_query(query, max_chars=2500):
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
