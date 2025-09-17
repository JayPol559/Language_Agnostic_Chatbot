import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("AIzaSyDimyRfkF7a8Nj84IE8D4PVrZgFVH7WHp4"))

model = genai.GenerativeModel('gemini-pro')

def get_gemini_response(prompt):
    """
    Sends a prompt to the Gemini API and returns the generated text.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "I'm sorry, I'm unable to connect to the AI service right now."

def translate_text(text, target_language):
    """
    Translates text to the target language using Gemini.
    """
    prompt = f"Translate the following text to {target_language}: '{text}'"
    return get_gemini_response(prompt)
