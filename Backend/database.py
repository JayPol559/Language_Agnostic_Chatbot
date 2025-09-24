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
    # If the SQLite build supports FTS5, this will be created; otherwise fallback uses LIKE.
    try:
        cur.execute('CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(content, docid UNINDEXED)')
    except Exception:
        # Some SQLite builds might not include FTS5; fallback is supported.
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
        source_doc_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()


def insert_document(title, url, content, status='uploaded'):
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


def search_documents(query, max_chars=2500, limit=5):
    """
    Search documents and return a best excerpt and the source doc metadata.
    Returns: list of dicts: [{id, title, excerpt}, ...] or [].
    """
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    results = []

    # Try FTS search first
    try:
        cur.execute("SELECT docid, content FROM documents_fts WHERE documents_fts MATCH ? LIMIT ?", (query, limit))
        rows = cur.fetchall()
        for r in rows:
            docid = r['docid']
            content = r['content']
            # fetch title for docid
            cur2 = conn.cursor()
            cur2.execute("SELECT title FROM Documents WHERE id = ?", (docid,))
            row_meta = cur2.fetchone()
            title = row_meta['title'] if row_meta else f"Document {docid}"
            excerpt = content[:max_chars]
            results.append({'id': docid, 'title': title, 'excerpt': excerpt})
    except Exception:
        # fallback to LIKE search
        cur.execute("SELECT id, title, content FROM Documents WHERE content LIKE ? LIMIT ?", (f"%{query}%", limit))
        rows = cur.fetchall()
        for r in rows:
            excerpt = (r['content'] or '')[:max_chars]
            results.append({'id': r['id'], 'title': r['title'], 'excerpt': excerpt})

    conn.close()
    return results


def list_documents(limit=100):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, title, status, created_at FROM Documents ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_document_by_id(doc_id):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, title, url, content, status, created_at FROM Documents WHERE id = ?", (doc_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None
