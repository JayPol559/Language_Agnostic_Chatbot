import os
import sqlite3
from database import DATABASE_NAME, insert_document
import PyPDF2

# Optional OCR
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

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


def ocr_pdf_images(file_path):
    """
    If PyPDF2 fails to extract text (scanned PDF), try OCR. Requires system Tesseract and pytesseract + Pillow installed.
    This simple function will extract each page as image if possible (using PyPDF2 is limited),
    but a robust solution would use pdf2image; to keep dependencies minimal we try basic fallback.
    """
    try:
        # Try pdf2image if available (preferred)
        from pdf2image import convert_from_path
        images = convert_from_path(file_path, dpi=200)
        text = ""
        for img in images:
            try:
                text += pytesseract.image_to_string(img) + "\n"
            except Exception:
                pass
        return text
    except Exception:
        # If pdf2image not available, return empty
        return ""


def process_and_save_pdf(file_path, filename):
    """
    Extracts text from the PDF and saves it into the Documents table (and FTS).
    Returns True on success.
    """
    try:
        text = extract_text_from_pdf(file_path)
        if not text or not text.strip():
            # Try OCR fallback if available
            if OCR_AVAILABLE:
                print("No text found; trying OCR for scanned PDF.")
                text = ocr_pdf_images(file_path)
            else:
                print("No text found and OCR not available.")
        if not text or not text.strip():
            print("No extractable text found in PDF:", filename)
            return False

        # Optionally trim very large files
        max_len = 300000
        if len(text) > max_len:
            text = text[:max_len]

        insert_document(title=filename, url=file_path, content=text, status='uploaded')
        print(f"Saved PDF content for {filename}.")
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
        # combine top N excerpts into one excerpt (short)
        combined = "\n\n".join([s['excerpt'] for s in snippets])
        if len(combined) > max_chars:
            combined = combined[:max_chars]
        # return combined and also first doc metadata
        return {'combined': combined, 'first_doc': snippets[0]}
    except Exception as e:
        print("Error searching documents:", e)
        return None
