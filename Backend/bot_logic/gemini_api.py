import os
import requests

# Read API key and model from env
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

# Default Gemini model (can be overridden by env)
GEMINI_MODEL = os.environ.get('GEMINI_MODEL') or "models/gemini-1.5-flash"

# Base URL (fixed to correct v1beta endpoint, can override via GEMINI_BASE_URL env)
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
    Endpoint pattern:
      POST {BASE_URL}/{MODEL}:generateContent?key={API_KEY}
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")

    # Candidate base URLs to try (only valid ones)
    candidate_base_urls = [
        os.environ.get('GEMINI_BASE_URL') or BASE_URL,
    ]

    # ✅ Candidate models with stable IDs (avoid -latest, use fixed names)
    candidate_models = [
        os.environ.get('GEMINI_MODEL') or GEMINI_MODEL,
        "models/gemini-1.5-flash",
        "models/gemini-1.5-pro"
    ]

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
                if resp.status_code == 404:
                    last_error_text = resp.text
                    continue
                resp.raise_for_status()
                data = resp.json()

                # Parse Gemini response
                if isinstance(data, dict) and "candidates" in data and len(data["candidates"]) > 0:
                    cand0 = data["candidates"][0]
                    if "content" in cand0 and "parts" in cand0["content"]:
                        parts = cand0["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            return parts[0]["text"]

                return str(data)

            except requests.exceptions.HTTPError as http_err:
                last_error_text = f"{http_err} - response text: {getattr(http_err.response, 'text', '')}"
                continue
            except Exception as e:
                last_error_text = str(e)
                continue

    print("Generative API: all model/base-url attempts failed. Last error:", last_error_text)
    return "I'm sorry — the configured language model endpoint or model name could not be reached (check GEMINI_MODEL/GEMINI_BASE_URL)."
