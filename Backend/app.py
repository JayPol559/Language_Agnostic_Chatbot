
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import sqlite3
import os

# Load environment variables from .env file
load_dotenv()

# Import logic modules
from bot_logic.gemini_api import get_gemini_response, translate_text
from bot_logic.data_processor import process_and_save_pdf, get_document_content_for_query

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

DATABASE = 'knowledge_base.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/ask_bot', methods=['POST'])
def ask_bot():
    """
    Handles student queries, processes them, and returns a response.
    """
    data = request.json
    user_query = data.get('query')
    language = data.get('language', 'en')
    
    if not user_query:
        return jsonify({'response': 'Please enter a query.'}), 400

    conn = get_db_connection()
    
    # 1. Search for a direct match in FAQs
    faq_answer = conn.execute('SELECT answer FROM faqs WHERE question LIKE ?', (f'%{user_query}%',)).fetchone()
    
    if faq_answer:
        response_text = faq_answer['answer']
    else:
        # 2. Search for relevant content in uploaded documents
        document_content = get_document_content_for_query(user_query)
        
        if document_content:
            # Use Gemini to generate a summary from the document content
            prompt = f"Based on the following text, answer the question '{user_query}':\n\n{document_content}"
            response_text = get_gemini_response(prompt)
        else:
            # 3. Fallback to Gemini's general knowledge
            response_text = get_gemini_response(f"Answer the following question about a university or college: {user_query}")
            
    # 4. Translate the final response if necessary
    if language.lower() not in ['en', 'english']:
        response_text = translate_text(response_text, language)

    # 5. Save the conversation for logging
    conn.execute('INSERT INTO conversations (user_query, bot_response) VALUES (?, ?)', (user_query, response_text))
    conn.commit()
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
    
    if file and file.filename.endswith('.pdf'):
        # Save the file to a temporary location
        file_path = os.path.join(os.getcwd(), file.filename)
        file.save(file_path)
        
        # Process and save to database
        if process_and_save_pdf(file_path, file.filename):
            os.remove(file_path) # Clean up temp file
            return jsonify({'message': 'File uploaded and processed successfully'}), 200
        else:
            os.remove(file_path)
            return jsonify({'message': 'File processing failed'}), 500
    
    return jsonify({'message': 'Invalid file format'}), 400

@app.route('/')
def home():
    """
    Serves the main frontend application.
    """
    return "Backend is running. Access the frontend to use the chatbot."

if __name__ == '__main__':
    # Database setup and data ingestion
    init_db()
    ingest_data()
    
    app.run(debug=True, port=8000)
