import PyPDF2
import sqlite3

DATABASE = 'database/chatbot.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def process_and_save_pdf(file_path, file_name):
    """
    Extracts text from a PDF file and saves it to the database.
    """
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        
        conn = get_db_connection()
        conn.execute('INSERT INTO documents (title, content) VALUES (?, ?)', (file_name, text))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return False

def get_document_content_for_query(query):
    """
    Fetches relevant document content from the database based on a query.
    (This is a simple search, can be improved with advanced techniques)
    """
    conn = get_db_connection()
    # Simple search for a keyword match in document titles
    documents = conn.execute('SELECT content FROM documents WHERE title LIKE ?', (f'%{query}%',)).fetchall()
    conn.close()
    
    if documents:
        # For simplicity, returning content of the first matching document
        return documents[0]['content']
    return None
