import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables located in Backend/.env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

# Import bot logic modules
from bot_logic.gemini_api import get_gemini_response, translate_text
from bot_logic.data_processor import process_and_save_pdf, get_document_content_for_query
from database import init_db, DATABASE_NAME

app = Flask(__name__, static_folder=None)
# For initial testing allow all origins. In production restrict origins.
CORS(app)
from flask import Flask, jsonify, request
from flask_cors import CORS # Yeh line add karen

app = Flask(__name__)
CORS(app) # Aur yeh line bhi

# Upload config
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/ask_bot', methods=['POST'])
def ask_bot():
    """
    Expects JSON: { "query": "...", "language": "en" }
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'response': 'Invalid request payload.'}), 400

    user_query = data.get('query', '').strip()
    language = data.get('language', 'en')

    if not user_query:
        return jsonify({'response': 'Please enter a query.'}), 400

    conn = get_db_connection()

    try:
        # 1. Search FAQs
        faq_row = conn.execute(
            'SELECT answer FROM faqs WHERE question LIKE ?',
            (f'%{user_query}%',)
        ).fetchone()

        if faq_row:
            response_text = faq_row['answer']
        else:
            # 2. Search uploaded documents
            document_content = get_document_content_for_query(user_query)
            if document_content:
                prompt = f"Based on the following text, answer the question '{user_query}':\n\n{document_content}"
                response_text = get_gemini_response(prompt)
            else:
                # 3. Fallback to Gemini's general knowledge
                prompt = f"Answer the following question about a university or college: {user_query}"
                response_text = get_gemini_response(prompt)

        # 4. Translate if required
        if language and language.lower() not in ['en', 'english']:
            response_text = translate_text(response_text, language)
    except Exception as ex:
        app.logger.error("Error while generating response: %s", ex)
        response_text = "Sorry, an internal error occurred while generating the response."

    # 5. Save the conversation for logging
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
    """
    Handles PDF uploads from the admin panel.
    """
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
            # optionally keep or remove the file; here we remove
            try:
                if os.path.exists(saved_path):
                    os.remove(saved_path)
            except Exception:
                pass

            if success:
                return jsonify({'message': 'File uploaded and processed successfully'}), 200
            else:
                return jsonify({'message': 'File processing failed'}), 500
        except Exception as ex:
            app.logger.error("Upload failed: %s", ex)
            try:
                if os.path.exists(saved_path):
                    os.remove(saved_path)
            except Exception:
                pass
            return jsonify({'message': 'Server error during upload'}), 500

    return jsonify({'message': 'Invalid file format'}), 400


@app.route('/')
def home():
    return "Backend is running. Use the frontend to interact with the chatbot."


if __name__ == '__main__':
    # Initialize DB on startup
    init_db()
    # Optionally run ingest_data() here if desired:
    # from ingest_data import ingest_data
    # ingest_data()
    port = int(os.environ.get('PORT', 5000))
    debug_flag = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug_flag)
