import os
import requests

# 🔑 Gemini API key (direct paste kar sakte ho yahan agar env set nahi hai)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or "YOUR_API_KEY_HERE"

# ✅ Sirf working model
GEMINI_MODEL = "models/gemini-1.5-flash"

# ✅ Correct Base URL
BASE_URL = "https://generativelanguage.googleapis.com/v1"

# Language codes mapping
LANG_CODE_TO_NAME = {
    'en': 'English',
    'hi': 'Hindi',
    'gu': 'Gujarati',
    'mr': 'Marathi',
    'bn': 'Bengali',
    'ta': 'Tamil',
    'te': 'Telugu',
    'kn': 'Kannada',
    'ml': 'Malayalam',
}


def call_generative_api(prompt, max_output_tokens=512, temperature=0.7, timeout=30):
    """
    Call Gemini API (v1 + gemini-1.5-flash only).
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")

    url = f"{BASE_URL}/{GEMINI_MODEL}:generateContent"
    params = {"key": GEMINI_API_KEY}

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens
        }
    }

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(url, params=params, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        # ✅ Parse Gemini response
        if "candidates" in data and data["candidates"]:
            cand0 = data["candidates"][0]
            if "content" in cand0 and "parts" in cand0["content"]:
                parts = cand0["content"]["parts"]
                if parts and "text" in parts[0]:
                    return parts[0]["text"]

        return str(data)

    except Exception as e:
        print("Generative API call failed:", str(e))
        return "I'm sorry — the Gemini API call failed."


def get_gemini_response_from_source(question, source_text, source_title=None, language_code='en'):
    lang_name = LANG_CODE_TO_NAME.get(language_code, language_code)
    prompt = (
        f"You are an assistant. Use ONLY the following source excerpt to answer the question. "
        f"Do NOT invent facts. If the answer is not present, respond exactly: "
        f"'I don't see that information in the provided documents.'\n\n"
        f"Source title: {source_title or 'Source'}\n\n"
        f"Source excerpt:\n{source_text}\n\n"
        f"Question: {question}\n"
        f"Answer in {lang_name}. Be concise — ONE short sentence. "
        f"At the end include the source title in parentheses."
    )
    return call_generative_api(prompt, max_output_tokens=400, temperature=0.05)


def get_gemini_response_general(question, language_code='en'):
    lang_name = LANG_CODE_TO_NAME.get(language_code, language_code)
    prompt = (
        f"You are an assistant for university/college info. "
        f"Answer concisely (ONE short sentence) in {lang_name}. "
        f"Question: {question}\n"
        f"If you cannot confidently answer, say: "
        f"'I don't see that information in the provided documents.'"
    )
    return call_generative_api(prompt, max_output_tokens=300, temperature=0.05)


def translate_text(text, target_language_code):
    if not text:
        return text
    lang_name = LANG_CODE_TO_NAME.get(target_language_code, target_language_code)
    prompt = f"Translate the following text into {lang_name} and keep it short:\n\n{text}"
    return call_generative_api(prompt, max_output_tokens=300, temperature=0.1)
