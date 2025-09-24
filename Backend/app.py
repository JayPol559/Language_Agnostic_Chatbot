import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

from bot_logic.gemini_api import get_gemini_response_from_source, get_gemini_response_general, translate_text
from bot_logic.data_processor import process_and_save_pdf, get_document_content_for_query, STORAGE_FOLDER
from database import init_db, list_documents, get_document_by_id, delete_document

app = Flask(__name__, static_folder=None)
CORS(app)

# Storage folder: use env STORAGE_FOLDER to allow persistent mount (e.g., Render persistent disk).
STORAGE_FOLDER = os.environ.get('STORAGE_FOLDER') or STORAGE_FOLDER
os.makedirs(STORAGE_FOLDER, exist_ok=True)
UPLOAD_FOLDER = STORAGE_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_language_of_text(text):
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        return 'en'


@app.route('/ask_bot', methods=['POST'])
def ask_bot():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'response': 'Invalid request payload.'}), 400

    user_query = data.get('query', '').strip()
    language = data.get('language', None)

    if not user_query:
        return jsonify({'response': 'Please enter a query.'}), 400

    if not language or language == 'auto':
        language = detect_language_of_text(user_query) or 'en'

    source_info = None
    try:
        # 1) Check FAQs
        conn = sqlite3.connect(os.path.join(BASE_DIR, 'knowledge_base.db'))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT answer FROM faqs WHERE question LIKE ? LIMIT 1", (f"%{user_query}%",))
        faq_row = cur.fetchone()
        conn.close()

        if faq_row:
            response_text = faq_row['answer']
            if language and language != 'en':
                response_text = translate_text(response_text, language)
        else:
            # 2) Search uploaded docs
            doc_search = get_document_content_for_query(user_query)
            if doc_search:
                combined = doc_search['combined']
                first_doc = doc_search.get('first_doc')
                source_info = {'id': first_doc.get('id'), 'title': first_doc.get('title'), 'filename': first_doc.get('filename')}
                response_text = get_gemini_response_from_source(user_query, combined, source_title=source_info['title'], language_code=language)
            else:
                # 3) fallback
                response_text = get_gemini_response_general(user_query, language_code=language)
    except Exception as ex:
        app.logger.error("Error while generating response: %s", ex)
        response_text = "Sorry, an internal error occurred while generating the response."

    # Save conversation
    try:
        conn = sqlite3.connect(os.path.join(BASE_DIR, 'knowledge_base.db'))
        cur = conn.cursor()
        cur.execute('INSERT INTO conversations (user_query, bot_response, source_doc_id) VALUES (?, ?, ?)',
                    (user_query, response_text, source_info['id'] if source_info else None))
        conn.commit()
        conn.close()
    except Exception as ex:
        app.logger.error("Failed to save conversation: %s", ex)

    return jsonify({'response': response_text, 'source': source_info})


@app.route('/admin/upload', methods=['POST'])
def upload_file():
    """
    Accept multiple files (multipart/form-data). Field name must be 'file' (multiple).
    Saves files permanently under STORAGE_FOLDER (unless you delete).
    """
    files = request.files.getlist('file')
    if not files:
        return jsonify({'message': 'No files provided'}), 400

    results = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # To avoid collisions, you can prefix with timestamp or UUID
            import time, uuid
            unique_name = f"{int(time.time())}_{uuid.uuid4().hex}_{filename}"
            saved_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            try:
                file.save(saved_path)
                success = process_and_save_pdf(saved_path, unique_name)
                # IMPORTANT: we KEEP the saved file (do not delete) so it's available until manual deletion
                results.append({'filename': unique_name, 'processed': bool(success)})
            except Exception as ex:
                app.logger.error("Upload failed: %s", ex)
                try:
                    if os.path.exists(saved_path):
                        os.remove(saved_path)
                except Exception:
                    pass
                results.append({'filename': filename, 'processed': False, 'error': str(ex)})
        else:
            results.append({'filename': getattr(file, 'filename', 'unknown'), 'processed': False, 'error': 'Invalid file format'})

    return jsonify({'results': results})


@app.route('/admin/docs', methods=['GET'])
def admin_docs():
    docs = list_documents(limit=1000)
    # attach download URL for each doc
    docs_with_urls = []
    for d in docs:
        filename = d.get('filename')
        download_url = None
        if filename:
            download_url = request.host_url.rstrip('/') + '/uploads/' + filename
        d_copy = dict(d)
        d_copy['download_url'] = download_url
        docs_with_urls.append(d_copy)
    return jsonify({'documents': docs_with_urls})


@app.route('/admin/delete/<int:doc_id>', methods=['POST', 'DELETE'])
def admin_delete(doc_id):
    doc = get_document_by_id(doc_id)
    if not doc:
        return jsonify({'message': 'Not found'}), 404
    filename = doc.get('filename')
    # delete DB entry
    delete_document(doc_id)
    # delete file from storage if exists
    if filename:
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            if os.path.exists(fpath):
                os.remove(fpath)
        except Exception as e:
            app.logger.error("Failed to delete file: %s", e)
    return jsonify({'message': 'Deleted'})


@app.route('/uploads/<path:filename>', methods=['GET'])
def uploaded_file(filename):
    """
    Serve uploaded file. Be careful: for production consider protected endpoints or signed URLs.
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)


@app.route('/')
def home():
    return "Backend is running."

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug_flag = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug_flag)
