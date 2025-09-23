import os
import sqlite3
from database import DATABASE_NAME, insert_document
import PyPDF2

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


def process_and_save_pdf(file_path, filename):
    """
    Extracts text from the PDF and saves it into the Documents table (and FTS).
    Returns True on success.
    """
    try:
        text = extract_text_from_pdf(file_path)
        if not text or not text.strip():
            print("No extractable text found in PDF:", filename)
            return False

        # Optionally trim very large files
        max_len = 200000  # keep up to ~200k chars
        if len(text) > max_len:
            text = text[:max_len]

        # Insert into DB via helper (this inserts into Documents and FTS if available)
        insert_document(title=filename, url=file_path, content=text, status='uploaded')
        print(f"Saved PDF content for {filename}.")
        return True
    except Exception as e:
        print("Failed to process PDF:", e)
        return False


def get_document_content_for_query(query, max_chars=3000):
    """
    Wrapper around database.search_documents
    """
    try:
        from database import search_documents
        snippet = search_documents(query, max_chars=max_chars)
        return snippet
    except Exception as e:
        print("Error searching documents:", e)
        return None
