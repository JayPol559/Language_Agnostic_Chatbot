import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables from .env file in Backend/
load_dotenv()

# Import logic modules (assumes these modules exist in backend repo)
from bot_logic.gemini_api import get_gemini_response, translate_text
from bot_logic.data_processor import process_and_save_pdf, get_document_content_for_query

app = Flask(__name__)
# In production, restrict origins: CORS(app, origins=["https://your-frontend.example.com"])
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'knowledge_base.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Create tables if they don't exist
    cur.execute('''
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT
        )
    ''')
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/ask_bot', methods=['POST'])
def ask_bot():
    data = request.get_json(force=True)
    user_query = data.get('query')
    language = data.get('language', 'en')

    if not user_query:
        return jsonify({'response': 'Please enter a query.'}), 400

    conn = get_db_connection()

    # 1. Search FAQs (basic LIKE search)
    faq_row = conn.execute('SELECT answer FROM faqs WHERE question LIKE ?', (f'%{user_query}%',)).fetchone()
    if faq_row:
        response_text = faq_row['answer']
    else:
        # 2. Search uploaded documents
        document_content = get_document_content_for_query(user_query)
        if document_content:
            prompt = f"Based on the following text, answer the question '{user_query}':\n\n{document_content}"
            response_text = get_gemini_response(prompt)
        else:
            # 3. Fallback to Gemini general knowledge
            response_text = get_gemini_response(f"Answer the following question about a university or college: {user_query}")

    # Translate if needed
    if language and language.lower() not in ('en', 'english'):
        try:
            response_text = translate_text(response_text, language)
        except Exception as ex:
            app.logger.error("Translation failed: %s", ex)

    # Save conversation
    try:
        conn.execute('INSERT INTO conversations (user_query, bot_response) VALUES (?, ?)', (user_query, response_text))
        conn.commit()
    except Exception as ex:
        app.logger.error("Failed to save conversation: %s", ex)
    finally:
        conn.close()

    return jsonify({'response': response_text})

@app.route('/admin/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(saved_path)
            success = process_and_save_pdf(saved_path, filename)
            # Clean up local file if desired
            try:
                os.remove(saved_path)
            except Exception:
                pass

            if success:
                return jsonify({'message': 'File uploaded and processed successfully'}), 200
            else:
                return jsonify({'message': 'File processing failed'}), 500
        except Exception as ex:
            app.logger.error("Upload failed: %s", ex)
            # Attempt cleanup
            try:
                if os.path.exists(saved_path):
                    os.remove(saved_path)
            except Exception:
                pass
            return jsonify({'message': 'Server error during upload'}), 500

    return jsonify({'message': 'Invalid file format'}), 400

@app.route('/')
def home():
    return "Backend is running. Visit the frontend to use the chatbot."

if __name__ == '__main__':
    init_db()
    # Optionally ingest data on startup (comment out if you don't want automatic scraping)
    # from ingest_data import ingest_data
    # ingest_data()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', '0') == '1')
