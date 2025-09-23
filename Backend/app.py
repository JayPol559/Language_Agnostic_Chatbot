import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

from bot_logic.gemini_api import get_gemini_response_from_source, get_gemini_response_general, translate_text
from bot_logic.data_processor import process_and_save_pdf, get_document_content_for_query
from database import init_db, insert_document

app = Flask(__name__, static_folder=None)
# For Production: restrict origins list. For quick testing you can keep CORS(app)
CORS(app)

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# optional language detection
def detect_language_of_text(text):
    try:
        from langdetect import detect
        lang = detect(text)
        return lang
    except Exception:
        return 'en'


@app.route('/ask_bot', methods=['POST'])
def ask_bot():
    """
    Expects JSON: { "query": "...", "language": "en" (optional) }
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'response': 'Invalid request payload.'}), 400

    user_query = data.get('query', '').strip()
    language = data.get('language', None)

    if not user_query:
        return jsonify({'response': 'Please enter a query.'}), 400

    # detect language if not provided
    if not language:
        language = detect_language_of_text(user_query) or 'en'

    try:
        # 1) Check FAQs (simple match)
        conn = sqlite3.connect(os.path.join(BASE_DIR, 'knowledge_base.db'))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT answer FROM faqs WHERE question LIKE ? LIMIT 1", (f"%{user_query}%",))
        faq_row = cur.fetchone()
        conn.close()

        if faq_row:
            response_text = faq_row['answer']
            # translate if faq not in user's language
            # (Assume stored FAQs are in English; translate if needed)
            if language and language != 'en':
                response_text = translate_text(response_text, language)
        else:
            # 2) Search uploaded documents (FTS)
            document_content = get_document_content_for_query(user_query)
            if document_content:
                # Use the document excerpt to generate a concise answer in the user's language
                response_text = get_gemini_response_from_source(user_query, document_content, language=language)
            else:
                # 3) Fallback to general model knowledge (concise)
                response_text = get_gemini_response_general(user_query, language=language)

    except Exception as ex:
        app.logger.error("Error while generating response: %s", ex)
        response_text = "Sorry, an internal error occurred while generating the response."

    # Save conversation
    try:
        conn = sqlite3.connect(os.path.join(BASE_DIR, 'knowledge_base.db'))
        conn.execute('INSERT INTO conversations (user_query, bot_response) VALUES (?, ?)', (user_query, response_text))
        conn.commit()
        conn.close()
    except Exception as ex:
        app.logger.error("Failed to save conversation: %s", ex)

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
            # Optionally remove saved_path file if not needed
            try:
                if os.path.exists(saved_path):
                    os.remove(saved_path)
            except Exception:
                pass

            if success:
                return jsonify({'message': 'File uploaded and processed successfully'}), 200
            else:
                return jsonify({'message': 'File processing failed or contains no extractable text'}), 500
        except Exception as ex:
            app.logger.error("Upload failed: %s", ex)
            try:
                if os.path.exists(saved_path):
                    os.remove(saved_path)
            except Exception:
                pass
            return jsonify({'message': 'Server error during upload'}), 500

    return jsonify({'message': 'Invalid file format'}), 400


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug_flag = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug_flag)
