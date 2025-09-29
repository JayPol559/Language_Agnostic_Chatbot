import os
import requests

# Read API key and model from env
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

# Raw model value (may be provided as 'models/gemini-1.5-flash' or 'gemini-1.5-flash')
_raw_model = os.environ.get('GEMINI_MODEL') or "models/gemini-1.5-flash"
# Normalize to model name without the 'models/' prefix
GEMINI_MODEL = _raw_model.split('/', 1)[-1] if '/' in _raw_model else _raw_model

# Host override (optional). If a user sets GEMINI_HOST it should be the host only (no version),
# e.g. 'https://generativelanguage.googleapis.com'
GEMINI_HOST = os.environ.get('GEMINI_HOST') or "https://generativelanguage.googleapis.com"

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

def _build_candidate_urls(model_name):
    """Return a list of candidate full endpoint URLs to try (host/version/models/{model}:generateContent)."""
    versions = ["v1beta", "v1beta2", "v1"]
    # Allow an optional GEMINI_BASE_URL env that may include a version; if present, try it first
    base_env = os.environ.get('GEMINI_BASE_URL')
    candidates = []
    if base_env:
        # If base_env already contains /v1 or /v1beta, use it as-is
        candidates.append(base_env.rstrip('/'))
    # Add host+version combinations (prefer v1beta)
    for v in versions:
        candidates.append(f"{GEMINI_HOST.rstrip('/')}/{v}")
    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    # Build full endpoint URLs
    return [f"{base}/models/{model_name}:generateContent" for base in uniq]

def call_generative_api(prompt, max_output_tokens=512, temperature=0.7, timeout=30):
    """
    Call Gemini (Generative Language) API using a set of candidate endpoints.
    Returns model text on success, or a friendly error string on failure.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")

    model_name = GEMINI_MODEL

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

    last_error = None
    tried_urls = []

    for url in _build_candidate_urls(model_name):
        tried_urls.append(url)
        try:
            resp = requests.post(url, params={"key": GEMINI_API_KEY}, json=payload, headers=headers, timeout=timeout)
            # If 404, likely model/version mismatch; capture and continue
            if resp.status_code == 404:
                last_error = resp.text
                continue
            resp.raise_for_status()
            data = resp.json()

            # Parse typical generateContent response
            if isinstance(data, dict) and "candidates" in data and len(data["candidates"]) > 0:
                cand0 = data["candidates"][0]
                if isinstance(cand0, dict) and "content" in cand0 and isinstance(cand0["content"], dict):
                    parts = cand0["content"].get("parts")
                    if isinstance(parts, list) and len(parts) > 0 and isinstance(parts[0], dict) and "text" in parts[0]:
                        return parts[0]["text"]

            # If response shape differs, return the JSON as string for diagnostics
            return str(data)

        except requests.exceptions.HTTPError as http_err:
            last_error = f"HTTPError {http_err} - resp_text={getattr(http_err.response, 'text', '')}"
            continue
        except Exception as e:
            last_error = str(e)
            continue

    # All attempts failed
    diagnostic = {
        "message": "All model/base-url attempts failed.",
        "model": model_name,
        "tried_urls": tried_urls,
        "last_error": last_error,
    }
    print("Generative API diagnostic:", diagnostic)
    return ("I'm sorry — the language model endpoint could not be reached or the model is not available. "
            "Check GEMINI_API_KEY, GEMINI_MODEL (use model name without the 'models/' prefix), and GEMINI_HOST/GEMINI_BASE_URL. "
            f"Details: {last_error}")

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
