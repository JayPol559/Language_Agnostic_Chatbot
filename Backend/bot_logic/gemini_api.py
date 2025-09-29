import os
import requests

# --- CONFIG ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")

# Optional base URL (prefer v1)
GEMINI_HOST = os.environ.get('GEMINI_HOST') or "https://generativelanguage.googleapis.com"
GEMINI_BASE_URL = os.environ.get('GEMINI_BASE_URL') or f"{GEMINI_HOST}/v1"

# Language codes mapping
LANG_CODE_TO_NAME = {
    'en': 'English', 'hi': 'Hindi', 'gu': 'Gujarati', 'mr': 'Marathi',
    'bn': 'Bengali', 'ta': 'Tamil', 'te': 'Telugu', 'kn': 'Kannada', 'ml': 'Malayalam',
}

# --- INTERNAL ---
_DISCOVERED = None

def _candidate_bases():
    """Return candidate API bases (deduplicated)."""
    versions = ["v1"]  # force v1 for stability
    bases = [GEMINI_BASE_URL.rstrip('/')]
    for v in versions:
        base = f"{GEMINI_HOST.rstrip('/')}/{v}"
        if base not in bases:
            bases.append(base)
    return bases

def _list_models_at_base(base):
    """Return list of models at a given base."""
    try:
        resp = requests.get(f"{base}/models", params={"key": GEMINI_API_KEY}, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        models = data.get('models') if isinstance(data, dict) else None
        if isinstance(models, list):
            return models
        if isinstance(data, dict) and 'name' in data:
            return [data]
    except Exception:
        pass
    return None

def _discover_model_and_base(preferred_model_hint=None):
    """Automatically discover a working base URL and model name."""
    global _DISCOVERED
    if _DISCOVERED:
        return _DISCOVERED

    hint = preferred_model_hint
    hint_normal = hint.split('/', 1)[-1] if hint and '/' in hint else hint

    for base in _candidate_bases():
        models = _list_models_at_base(base)
        if not models:
            continue

        # exact match
        for m in models:
            name = m.get('name') if isinstance(m, dict) else None
            if not name:
                continue
            short = name.split('/', 1)[-1] if '/' in name else name
            if short == hint_normal or (hint_normal and short.lower() == hint_normal.lower()):
                _DISCOVERED = (base, name)
                return _DISCOVERED

        # any model that supports generateContent
        for m in models:
            name = m.get('name')
            supported = m.get('supportedMethods') or m.get('supported_methods') or []
            if isinstance(supported, list) and 'generateContent' in supported:
                _DISCOVERED = (base, name)
                return _DISCOVERED

        # fallback: first Gemini model
        for m in models:
            name = m.get('name')
            if name and 'gemini' in name.lower():
                _DISCOVERED = (base, name)
                return _DISCOVERED

        # fallback: first available model
        if len(models) > 0:
            first = models[0].get('name')
            if first:
                _DISCOVERED = (base, first)
                return _DISCOVERED

    return None

def _try_post_url(url, payload, timeout):
    try:
        resp = requests.post(url, params={"key": GEMINI_API_KEY}, json=payload,
                             headers={"Content-Type": "application/json"}, timeout=timeout)
        return resp
    except Exception:
        return None

def call_generative_api(prompt, max_output_tokens=512, temperature=0.7, timeout=30):
    """Call Gemini Generative API with automatic discovery."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_output_tokens}
    }

    discovered = _discover_model_and_base()
    if not discovered:
        return "No available model found. Check your API key and network."

    base, model_full_name = discovered
    url = f"{base}/models/{model_full_name}:generateContent"
    resp = _try_post_url(url, payload, timeout)
    if resp is None:
        return "Request failed."
    try:
        resp.raise_for_status()
        data = resp.json()
        if "candidates" in data and len(data["candidates"]) > 0:
            cand0 = data["candidates"][0]
            parts = cand0.get("content", {}).get("parts", [])
            if len(parts) > 0 and "text" in parts[0]:
                return parts[0]["text"]
        return str(data)
    except Exception as e:
        return f"Error parsing response: {e}"

# --- HELPER FUNCTIONS ---
def get_gemini_response_from_source(question, source_text, source_title=None, language_code='en'):
    lang_name = LANG_CODE_TO_NAME.get(language_code, language_code)
    prompt = (
        f"You are an assistant. Use ONLY the following source excerpt to answer the question. "
        f"Do NOT invent facts. If the answer is not present, respond exactly: "
        f'"I don\'t see that information in the provided documents."\n\n'
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
