import os
import sqlite3
from typing import List, Dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.path.join(BASE_DIR, 'knowledge_base.db')


def _connect():
    # Use check_same_thread False if using threads; keep default for now
    return sqlite3.connect(DATABASE_NAME)


def _table_columns(conn, table_name: str) -> List[str]:
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info({table_name})")
        rows = cur.fetchall()
        return [r[1] for r in rows] if rows else []
    except Exception:
        return []


def init_db():
    """
    Initialize database and perform simple migrations:
    - create missing tables
    - add missing columns (using ALTER TABLE ADD COLUMN)
    - create FTS virtual table if supported
    """
    conn = _connect()
    cur = conn.cursor()

    # Documents table with expected schema
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

    # Add missing columns if older DB lacks them
    cols = _table_columns(conn, 'Documents')
    if 'filename' not in cols:
        try:
            cur.execute("ALTER TABLE Documents ADD COLUMN filename TEXT")
        except Exception:
            pass
    if 'content' not in cols:
        try:
            cur.execute("ALTER TABLE Documents ADD COLUMN content TEXT")
        except Exception:
            pass
    if 'status' not in cols:
        try:
            cur.execute("ALTER TABLE Documents ADD COLUMN status TEXT")
        except Exception:
            pass

    # Faqs table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT
        )
    ''')

    # Conversations log (ensure table exists and add missing columns if any)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_query TEXT,
            bot_response TEXT,
            source_doc_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # If an older DB had conversations without source_doc_id, add it now
    conv_cols = _table_columns(conn, 'conversations')
    if 'source_doc_id' not in conv_cols:
        try:
            cur.execute("ALTER TABLE conversations ADD COLUMN source_doc_id INTEGER")
        except Exception:
            # If ALTER TABLE fails for some reason, we keep going (DB may be in a state that needs manual migration)
            pass

    conn.commit()

    # Try to create FTS5 virtual table (if supported)
    try:
        cur.execute('CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(content, docid UNINDEXED)')
        conn.commit()
    except Exception:
        # SQLite might not have FTS5 in this build — ok, fallback to LIKE searches
        pass

    conn.close()


def insert_document(title: str, filename: str, content: str, status: str = 'uploaded') -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO Documents (title, filename, content, status) VALUES (?, ?, ?, ?)",
                (title, filename, content, status))
    doc_id = cur.lastrowid
    conn.commit()
    conn.close()
    return doc_id


def search_documents(query: str, max_chars: int = 2500, limit: int = 5) -> List[Dict]:
    """
    Search documents and return list of matches: [{'id','title','filename','excerpt'}, ...]
    """
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Prefer FTS if available
    try:
        # If documents_fts exists, use it
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents_fts'")
        if cur.fetchone():
            # very simple FTS query
            cur.execute("""
                SELECT d.id, d.title, d.filename, substr(d.content, instr(lower(d.content), lower(?)) - 80, ?) as excerpt
                FROM Documents d
                JOIN documents_fts f ON f.docid = d.id
                WHERE documents_fts MATCH ?
                LIMIT ?
            """, (query, max_chars, query, limit))
            rows = cur.fetchall()
        else:
            # fallback to LIKE
            cur.execute("SELECT id, title, filename, content FROM Documents WHERE lower(content) LIKE ? LIMIT ?",
                        (f"%{query.lower()}%", limit))
            rows = cur.fetchall()
    except Exception:
        # fallback: simple LIKE
        cur.execute("SELECT id, title, filename, content FROM Documents WHERE lower(content) LIKE ? LIMIT ?",
                    (f"%{query.lower()}%", limit))
        rows = cur.fetchall()

    results = []
    for r in rows:
        excerpt = ''
        try:
            excerpt = (r['excerpt'] if 'excerpt' in r.keys() else r['content']) or ''
        except Exception:
            excerpt = r[3] if len(r) > 3 else ''
        if excerpt and len(excerpt) > max_chars:
            excerpt = excerpt[:max_chars]
        results.append({'id': r['id'], 'title': r['title'], 'filename': r.get('filename') if isinstance(r, dict) else (r[2] if len(r) > 2 else None), 'excerpt': excerpt})
    conn.close()
    return results


def list_documents(limit: int = 200) -> List[Dict]:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, title, filename, status, created_at FROM Documents ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_document_by_id(doc_id: int):
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, title, filename, content, status, created_at FROM Documents WHERE id = ?", (doc_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_document(doc_id: int) -> bool:
    conn = _connect()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM Documents WHERE id = ?", (doc_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()
