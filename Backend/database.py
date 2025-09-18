import sqlite3

DATABASE_NAME = "knowledge_base.db"

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Documents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Documents (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            content TEXT,
            status TEXT NOT NULL
        )
    ''')

    # FAQs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS FAQs (
            id INTEGER PRIMARY KEY,
            question TEXT NOT NULL UNIQUE,
            answer TEXT NOT NULL
        )
    ''')

    # Conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Conversations (
            id INTEGER PRIMARY KEY,
            user_query TEXT NOT NULL,
            bot_response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database and tables created successfully!")
