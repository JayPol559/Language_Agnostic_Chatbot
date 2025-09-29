import os
import requests

# Read API key and model from env
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

# Default Gemini model (can be overridden by env)
GEMINI_MODEL = os.environ.get('GEMINI_MODEL') or "models/gemini-1.5-flash"

# Base URL (can override via GEMINI_BASE_URL env)
BASE_URL = os.environ.get('GEMINI_BASE_URL') or "https://generativelanguage.googleapis.com/v1beta"

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
    Call Gemini API with the correct format.

    Tries a set of candidate base URLs and model names to be robust against model/version mismatches.
    Endpoint pattern:
      POST {BASE_URL}/{MODEL}:generateContent?key={API_KEY}
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")

    # Candidate base URLs to try (order: configured, common alternatives)
    candidate_base_urls = [
        os.environ.get('GEMINI_BASE_URL') or BASE_URL,
        "https://generativelanguage.googleapis.com/v1beta2",
        "https://generativelanguage.googleapis.com/v1",
    ]

    # Candidate models to try (configured first)
    candidate_models = [os.environ.get('GEMINI_MODEL') or GEMINI_MODEL,
                        "models/gemini-1.5",
                        "models/gemini-1.5-pro",
                        "models/gemini-1.5-flash"]

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

    last_error_text = None

    # Try combinations until one works
    for base in candidate_base_urls:
        for model in candidate_models:
            url = f"{base.rstrip('/')}/{model}:generateContent"
            params = {"key": GEMINI_API_KEY}
            try:
                resp = requests.post(url, params=params, json=payload, headers=headers, timeout=timeout)
                # If model/base-url combination not found, try next
                if resp.status_code == 404:
                    # capture for diagnostics and continue
                    last_error_text = resp.text
                    continue
                resp.raise_for_status()
                data = resp.json()

                # Parse Gemini response (compatible with typical generateContent responses)
                if isinstance(data, dict) and "candidates" in data and len(data["candidates"]) > 0:
                    cand0 = data["candidates"][0]
                    if "content" in cand0 and "parts" in cand0["content"]:
                        parts = cand0["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            return parts[0]["text"]

                # Fallback: if response shape different, return stringified JSON
                return str(data)

            except requests.exceptions.HTTPError as http_err:
                # If 404, we already continue above. For other HTTP errors, capture text and try next model/url.
                last_error_text = f"{http_err} - response text: {getattr(http_err.response, 'text', '')}"
                continue
            except Exception as e:
                last_error_text = str(e)
                continue

    # If we get here, all attempts failed — return friendly message and print diagnostics
    print("Generative API: all model/base-url attempts failed. Last error:", last_error_text)
    return "I'm sorry — the configured language model endpoint or model name could not be reached (check GEMINI_MODEL/GEMINI_BASE_URL)."


def get_gemini_response_from_source(question, source_text, source_title=None, language_code='en'):
    """
    Ask model to answer concisely using source_text only.
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
    return call_generative_api(prompt, max_output_tokens=400, temperature=0.05)


def get_gemini_response_general(question, language_code='en'):
    """
    General fallback when no source excerpt is available.
    """
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
    """
    Translate text into target language.
    """
    if not text:
        return text
    lang_name = LANG_CODE_TO_NAME.get(target_language_code, target_language_code)
    prompt = f"Translate the following text into {lang_name} and keep it short:\n\n{text}"
    return call_generative_api(prompt, max_output_tokens=300, temperature=0.1)
