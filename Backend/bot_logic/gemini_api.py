import os
import requests

# Read API key and model from env (do NOT commit real keys to repo)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
# Default model: use text-bison-001 (stable text model). Change this to the exact model name if you have access to Gemini model names.
GEMINI_MODEL = os.environ.get('GEMINI_MODEL') or "models/text-bison-001"

# Base URL for Google Generative Language REST API
BASE_URL = "https://generativelanguage.googleapis.com/v1"

def call_generative_api(prompt, max_output_tokens=512, temperature=0.2, timeout=30):
    """
    Calls the Google Generative Language REST API using the API key.
    Endpoint format:
      POST https://generativelanguage.googleapis.com/v1/models/{MODEL}:generate?key={API_KEY}
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")

    url = f"{BASE_URL}/{GEMINI_MODEL}:generate"
    params = {"key": GEMINI_API_KEY}
    payload = {
        "prompt": {"text": prompt},
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens
    }

    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, params=params, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        # Try common response shapes:
        # 1) {'candidates': [{'output': '...'}]} or {'candidates':[{'output':'...'}]}
        if isinstance(data, dict):
            if 'candidates' in data and len(data['candidates']) > 0:
                cand0 = data['candidates'][0]
                # different keys used historically: 'output', 'content'
                return cand0.get('output') or cand0.get('content') or str(cand0)

            # 2) {'output': '...'} simple key
            if 'output' in data and isinstance(data['output'], str):
                return data['output']

            # 3) some responses may include 'result' or 'text' keys
            if 'result' in data:
                r = data['result']
                if isinstance(r, dict):
                    # nested textual content
                    for k in ('output', 'content', 'text'):
                        if k in r:
                            return r[k]
                    # sometimes result.candidates
                    if 'candidates' in r and len(r['candidates']) > 0:
                        return r['candidates'][0].get('output') or r['candidates'][0].get('content')

            # 4) fallback: stringify whole response
            return str(data)

        return str(data)

    except requests.exceptions.HTTPError as http_err:
        # Return a helpful message and also log details
        print(f"Generative API HTTP error: {http_err} - response text: {getattr(http_err.response, 'text', '')}")
        return "I'm sorry — the language model could not generate an answer right now (HTTP error)."
    except Exception as e:
        print("Generative API call failed:", e)
        return "I'm sorry — I couldn't contact the language model right now."

def get_gemini_response(prompt):
    return call_generative_api(prompt, max_output_tokens=400)

def translate_text(text, target_language):
    if not text:
        return text
    t_prompt = f"Translate the following text to {target_language}:\n\n{text}"
    return call_generative_api(t_prompt, max_output_tokens=400)
