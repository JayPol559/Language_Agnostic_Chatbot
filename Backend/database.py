import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.path.join(BASE_DIR, 'knowledge_base.db')


def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()

    # Documents table for uploaded PDFs
    cur.execute('''
    CREATE TABLE IF NOT EXISTS Documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        url TEXT,
        content TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create an FTS5 virtual table for fast full-text search (content only)
    # Note: FTS5 may not be available in extremely old SQLite builds; Render's python image generally supports it.
    try:
        cur.execute('CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(content, docid UNINDEXED)')
    except Exception:
        # If FTS5 not available, we still keep Documents table (search will be fallback LIKE)
        pass

    # FAQs table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS faqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        answer TEXT
    )
    ''')

    # Conversations log
    cur.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_query TEXT,
        bot_response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()


def insert_document(title, url, content, status='uploaded'):
    """
    Inserts into Documents and into documents_fts (if available).
    Returns inserted document id.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Documents (title, url, content, status) VALUES (?, ?, ?, ?)",
        (title, url, content, status)
    )
    doc_id = cur.lastrowid

    # insert into FTS table if exists
    try:
        cur.execute("INSERT INTO documents_fts(rowid, content, docid) VALUES (?, ?, ?)", (doc_id, content, doc_id))
    except Exception:
        # fallback: if FTS not available, ignore
        pass

    conn.commit()
    conn.close()
    return doc_id


def search_documents(query, max_chars=3000, limit=5):
    """
    Searches documents for query. Prefer FTS search; if not available, fallback to LIKE.
    Returns concatenated snippet (trimmed) or None.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    results = []

    # Try FTS search
    try:
        cur.execute("SELECT docid, content FROM documents_fts WHERE documents_fts MATCH ? LIMIT ?", (query, limit))
        rows = cur.fetchall()
        for r in rows:
            results.append(r['content'])
    except Exception:
        # Fallback to naive LIKE search on Documents table
        cur.execute("SELECT content FROM Documents WHERE content LIKE ? LIMIT ?", (f"%{query}%", limit))
        rows = cur.fetchall()
        for r in rows:
            results.append(r['content'])

    conn.close()

    if not results:
        return None

    combined = "\n\n".join(results)
    if len(combined) > max_chars:
        combined = combined[:max_chars]
    return combined
