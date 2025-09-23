import os
import requests

# Read API key and model from env
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')

# Default model: use Gemini model (not text-bison-001 anymore)
# Options: "models/gemini-1.5-flash", "models/gemini-1.5-pro"
GEMINI_MODEL = os.environ.get('GEMINI_MODEL') or "models/gemini-1.5-flash"

# Base URL for Google Generative Language REST API
BASE_URL = "https://generativelanguage.googleapis.com/v1"

def call_generative_api(prompt, max_output_tokens=512, temperature=0.7, timeout=30):
    """
    Calls the Google Generative Language REST API using Gemini model.
    Endpoint format:
      POST https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")

    url = f"{BASE_URL}/{GEMINI_MODEL}:generateContent"
    params = {"key": GEMINI_API_KEY}

    # Gemini expects "contents" instead of "prompt"
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

        # Gemini response shape:
        # {"candidates":[{"content":{"parts":[{"text":"..."}]}}]}
        if isinstance(data, dict) and "candidates" in data and len(data["candidates"]) > 0:
            cand0 = data["candidates"][0]
            if "content" in cand0 and "parts" in cand0["content"]:
                parts = cand0["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    return parts[0]["text"]

        # fallback: stringify whole response
        return str(data)

    except requests.exceptions.HTTPError as http_err:
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
