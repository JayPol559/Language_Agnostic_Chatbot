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
        filename TEXT,
        content TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create an FTS5 virtual table for fast full-text search (content only)
    try:
        cur.execute('CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(content, docid UNINDEXED)')
    except Exception:
        # Some SQLite builds may not include FTS5; fallback handled in search.
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


def insert_document(title, filename, content, status='uploaded'):
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Documents (title, filename, content, status) VALUES (?, ?, ?, ?)",
        (title, filename, content, status)
    )
    doc_id = cur.lastrowid
    # insert into FTS table if exists
    try:
        cur.execute("INSERT INTO documents_fts(rowid, content, docid) VALUES (?, ?, ?)", (doc_id, content, doc_id))
    except Exception:
        pass
    conn.commit()
    conn.close()
    return doc_id


def search_documents(query, max_chars=2500, limit=5):
    """
    Returns list of matches: [{'id','title','filename','excerpt'}, ...]
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
            content = r['content'] or ''
            cur2 = conn.cursor()
            cur2.execute("SELECT title, filename FROM Documents WHERE id = ?", (docid,))
            meta = cur2.fetchone()
            title = meta['title'] if meta else f"Document {docid}"
            filename = meta['filename'] if meta else None
            excerpt = content[:max_chars]
            results.append({'id': docid, 'title': title, 'filename': filename, 'excerpt': excerpt})
    except Exception:
        # Fallback to LIKE search
        cur.execute("SELECT id, title, filename, content FROM Documents WHERE content LIKE ? LIMIT ?", (f"%{query}%", limit))
        rows = cur.fetchall()
        for r in rows:
            excerpt = (r['content'] or '')[:max_chars]
            results.append({'id': r['id'], 'title': r['title'], 'filename': r['filename'], 'excerpt': excerpt})

    conn.close()
    return results


def list_documents(limit=200):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, title, filename, status, created_at FROM Documents ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_document_by_id(doc_id):
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, title, filename, content, status, created_at FROM Documents WHERE id = ?", (doc_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_document(doc_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM Documents WHERE id = ?", (doc_id,))
    try:
        cur.execute("DELETE FROM documents_fts WHERE rowid = ?", (doc_id,))
    except Exception:
        pass
    conn.commit()
    conn.close()
    return True
