import os
import requests

# Read API key and model from environment variables
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

# Default Gemini model (latest stable options: gemini-1.5-flash / gemini-1.5-pro)
GEMINI_MODEL = os.environ.get('GEMINI_MODEL') or "models/gemini-1.5-flash"

# Base URL for Gemini (use v1beta for Gemini models)
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Map common language codes to display names the model understands better
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
    # add more as needed
}


def call_generative_api(prompt, max_output_tokens=512, temperature=0.7, timeout=30):
    """
    Call the Gemini API with correct format.
    Endpoint:
      POST https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")

    url = f"{BASE_URL}/{GEMINI_MODEL}:generateContent"
    params = {"key": GEMINI_API_KEY}

    # Gemini expects `contents` instead of `prompt`
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
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

        # Parse Gemini response
        if isinstance(data, dict) and "candidates" in data and len(data["candidates"]) > 0:
            cand0 = data["candidates"][0]
            if "content" in cand0 and "parts" in cand0["content"]:
                parts = cand0["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    return parts[0]["text"]

        # Fallback: return full JSON
        return str(data)

    except requests.exceptions.HTTPError as http_err:
        print(f"Generative API HTTP error: {http_err} - response text: {getattr(http_err.response, 'text', '')}")
        return "I'm sorry — the language model could not generate an answer right now (HTTP error)."
    except Exception as e:
        print("Generative API call failed:", e)
        return "I'm sorry — I couldn't contact the language model right now."


# === Wrappers (names kept same as your old code) ===

def get_gemini_response_from_source(question, source_text, language='en'):
    """
    Ask model to answer concisely using source_text.
    """
    lang_instruction = f"Answer in {language}." if language else "Answer in the same language as the question."
    prompt = (
        f"You are an assistant that answers concisely (1-2 short sentences). "
        f"Use ONLY the information in the following source excerpt. "
        f"Do not invent facts. If the answer cannot be found, say "
        f"'I don't see that information in the provided documents.'\n\n"
        f"Source excerpt:\n{source_text}\n\n"
        f"Question: {question}\n\n"
        f"{lang_instruction}\nBe concise and specific."
    )
    return call_generative_api(prompt, max_output_tokens=400)


def get_gemini_response_general(question, language='en'):
    """
    General fallback when no document matches.
    """
    lang_instruction = f"Answer in {language}." if language else ""
    prompt = (
        f"You are an assistant answering questions about universities and college administrative info. "
        f"Answer concisely (1-2 short sentences). {lang_instruction} "
        f"Question: {question}\nBe concise and specific."
    )
    return call_generative_api(prompt, max_output_tokens=400)


def translate_text(text, target_language):
    if not text:
        return text
    t_prompt = f"Translate the following text to {target_language}:\n\n{text}"
    return call_generative_api(t_prompt, max_output_tokens=400)
