import os
import requests

# === Config ===
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL') or "models/gemini-1.5-flash"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Supported languages
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


def call_generative_api(prompt, max_output_tokens=180, temperature=0.1, timeout=30):
    """
    Core Gemini API caller (v1beta generateContent endpoint).
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")

    url = f"{BASE_URL}/{GEMINI_MODEL}:generateContent"
    params = {"key": GEMINI_API_KEY}

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
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

        # === Parse Gemini response ===
        if isinstance(data, dict) and "candidates" in data and len(data["candidates"]) > 0:
            cand0 = data["candidates"][0]
            if "content" in cand0 and "parts" in cand0["content"]:
                parts = cand0["content"]["parts"]
                if parts and "text" in parts[0]:
                    return parts[0]["text"]

        # fallback
        return str(data)

    except requests.exceptions.HTTPError as http_err:
        print(f"Generative API HTTP error: {http_err} - response text: {getattr(http_err.response, 'text', '')}")
        return "I'm sorry — the language model could not generate an answer right now (HTTP error)."
    except Exception as e:
        print("Generative API call failed:", e)
        return "I'm sorry — I couldn't contact the language model right now."


def get_gemini_response_from_source(question, source_text, source_title=None, language_code='en'):
    """
    Answer concisely using ONLY the provided source_text.
    """
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
    return call_generative_api(prompt, max_output_tokens=140, temperature=0.05)


def get_gemini_response_general(question, language_code='en'):
    """
    General fallback Q&A when no source docs are matched.
    """
    lang_name = LANG_CODE_TO_NAME.get(language_code, language_code)
    prompt = (
        f"You are an assistant for university/college info. "
        f"Answer concisely (ONE short sentence) in {lang_name}. "
        f"Question: {question}\n"
        f"If you cannot confidently answer, say: "
        f"'I don't see that information in the provided documents.'"
    )
    return call_generative_api(prompt, max_output_tokens=110, temperature=0.05)


def translate_text(text, target_language_code):
    """
    Translate short text into target language.
    """
    lang_name = LANG_CODE_TO_NAME.get(target_language_code, target_language_code)
    prompt = f"Translate the following text into {lang_name} and keep it short:\n\n{text}"
    return call_generative_api(prompt, max_output_tokens=140, temperature=0.1)
