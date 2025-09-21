import os
import sqlite3
from database import DATABASE_NAME
import PyPDF2

def process_and_save_pdf(file_path, filename):
    """
    Extracts text from the PDF and saves it into the Documents table.
    Returns True on success.
    """
    try:
        text = ""
        with open(file_path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            print("No extractable text found in PDF.")
            return False

        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Documents (title, url, content, status) VALUES (?, ?, ?, ?)",
            (filename, file_path, text, 'uploaded')
        )
        conn.commit()
        conn.close()
        print(f"Saved PDF content for {filename}.")
        return True
    except Exception as e:
        print("Failed to process PDF:", e)
        return False


def get_document_content_for_query(query, max_chars=3000):
    """
    Searches Documents for occurrences of `query` and returns a concatenated content snippet.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT content FROM Documents WHERE content LIKE ? LIMIT 10", (f"%{query}%",))
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return None
        combined = "\n\n".join([r['content'] for r in rows])
        # trim to max_chars
        if len(combined) > max_chars:
            combined = combined[:max_chars]
        return combined
    except Exception as e:
        print("Error searching documents:", e)
        return None
