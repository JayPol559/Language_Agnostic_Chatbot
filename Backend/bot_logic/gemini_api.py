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

# Optional base URL (may include version) to prefer
GEMINI_BASE_URL = os.environ.get('GEMINI_BASE_URL')

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

_DISCOVERED = None

def _candidate_bases():
    versions = ["v1beta", "v1beta2", "v1"]
    bases = []
    if GEMINI_BASE_URL:
        bases.append(GEMINI_BASE_URL.rstrip('/'))
    for v in versions:
        bases.append(f"{GEMINI_HOST.rstrip('/')}/{v}")
    # deduplicate preserve order
    seen = set()
    out = []
    for b in bases:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out

def _list_models_at_base(base):
    try:
        url = f"{base}/models"
        resp = requests.get(url, params={"key": GEMINI_API_KEY}, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        # API may return {'models': [...]} or similar
        models = data.get('models') if isinstance(data, dict) else None
        if isinstance(models, list):
            return models
        # Sometimes response is a single model object
        if isinstance(data, dict) and 'name' in data:
            return [data]
    except Exception:
        pass
    return None

def _discover_model_and_base(preferred_model_hint=None):
    """
    Discover a working base URL and model name. Returns (base, model_full_name).
    The model_full_name should be like 'models/gemini-1.5-flash' or 'models/text-bison-001'.
    """
    global _DISCOVERED
    if _DISCOVERED:
        return _DISCOVERED

    hint = preferred_model_hint or GEMINI_MODEL
    # Normalize hint to without models/ prefix
    hint_normal = hint.split('/', 1)[-1] if '/' in hint else hint

    for base in _candidate_bases():
        models = _list_models_at_base(base)
        if not models:
            continue
        # Try to find exact match first
        for m in models:
            name = m.get('name') if isinstance(m, dict) else None
            if not name:
                continue
            short = name.split('/', 1)[-1] if '/' in name else name
            if short == hint_normal or short.lower() == hint_normal.lower():
                _DISCOVERED = (base, name)
                return _DISCOVERED
        # If exact not found, look for models that support generateContent
        for m in models:
            name = m.get('name')
            if not name:
                continue
            supported = m.get('supportedMethods') or m.get('supported_methods') or []
            if isinstance(supported, list) and 'generateContent' in supported:
                _DISCOVERED = (base, name)
                return _DISCOVERED
        # fallback: prefer any gemini model
        for m in models:
            name = m.get('name')
            if not name:
                continue
            if 'gemini' in name.lower():
                _DISCOVERED = (base, name)
                return _DISCOVERED
        # else pick first model
        if len(models) > 0:
            first = models[0].get('name')
            if first:
                _DISCOVERED = (base, first)
                return _DISCOVERED

    # nothing discovered
    return None

def _try_post_url(url, payload, timeout):
    try:
        resp = requests.post(url, params={"key": GEMINI_API_KEY}, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)
        return resp
    except Exception as e:
        return None

def call_generative_api(prompt, max_output_tokens=512, temperature=0.7, timeout=30):
    """
    Call Gemini (Generative Language) API with discovery fallback.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")

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

    # First try using the configured model hint directly across candidate bases
    model_hint = GEMINI_MODEL
    tried = []
    last_error = None

    for base in _candidate_bases():
        # try with both forms: with "models/" and without (some APIs expect full name)
        for model_form in (f"models/{{model_hint}}", model_hint):
            url = f"{{base}}/models/{{model_form}}:generateContent"
            tried.append(url)
            resp = _try_post_url(url, payload, timeout)
            if resp is None:
                last_error = 'request failed'
                continue
            if resp.status_code == 404:
                last_error = resp.text
                continue
            try:
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and "candidates" in data and len(data["candidates"]) > 0:
                    cand0 = data["candidates"][0]
                    if isinstance(cand0, dict) and "content" in cand0 and isinstance(cand0["content"], dict):
                        parts = cand0["content"].get("parts")
                        if isinstance(parts, list) and len(parts) > 0 and isinstance(parts[0], dict) and "text" in parts[0]:
                            return parts[0]["text"]
                return str(data)
            except Exception as e:
                last_error = str(e)
                continue

    # If direct attempts failed, try discovery via ListModels
    discovered = _discover_model_and_base(GEMINI_MODEL)
    if discovered:
        base, full_model_name = discovered
        url = f"{{base}}/models/{{full_model_name}}:generateContent"
        tried.append(url)
        resp = _try_post_url(url, payload, timeout)
        if resp is not None:
            try:
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and "candidates" in data and len(data["candidates"]) > 0:
                    cand0 = data["candidates"][0]
                    if isinstance(cand0, dict) and "content" in cand0 and isinstance(cand0["content"], dict):
                        parts = cand0["content"].get("parts")
                        if isinstance(parts, list) and len(parts) > 0 and isinstance(parts[0], dict) and "text" in parts[0]:
                            return parts[0]["text"]
                return str(data)
            except Exception as e:
                last_error = str(e)

    diagnostic = {
        "message": "All model/base-url attempts failed.",
        "tried": tried,
        "last_error": last_error,
    }
    print("Generative API diagnostic:", diagnostic)
    return ("I'm sorry — the language model endpoint could not be reached or the model is not available. "
            "Check GEMINI_API_KEY, GEMINI_MODEL and GEMINI_HOST/GEMINI_BASE_URL. "
            f"Details: {{last_error}}")

def get_gemini_response_from_source(question, source_text, source_title=None, language_code='en'):
    """
    Ask model to answer concisely using source_text only.
    """
    lang_name = LANG_CODE_TO_NAME.get(language_code, language_code)
    prompt = (
        f"You are an assistant. Use ONLY the following source excerpt to answer the question. "
        f"Do NOT invent facts. If the answer is not present, respond exactly: "
        f'"I don't see that information in the provided documents.'\n\n"
        f"Source title: {{source_title or 'Source'}}\n\n"
        f"Source excerpt:\n{{source_text}}\n\n"
        f"Question: {{question}}\n"
        f"Answer in {{lang_name}}. Be concise — ONE short sentence. "
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
        f"Answer concisely (ONE short sentence) in {{lang_name}}. "
        f"Question: {{question}}\n"
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
    prompt = f"Translate the following text into {{lang_name}} and keep it short:\n\n{{text}}"
    return call_generative_api(prompt, max_output_tokens=300, temperature=0.1)