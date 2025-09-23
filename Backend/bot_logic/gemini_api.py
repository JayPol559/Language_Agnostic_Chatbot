import os
import requests

# Use GOOGLE Generative Language REST endpoint (text-bison-like).
# The API key you provided will be used here. Please DO NOT commit this file with a real API key to a public repo.
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or "AIzaSyBmc1MD1m4bQqXwWUyNRQCNIucaTqLi2hoQ"

# Example model endpoint (text-bison). Ensure this endpoint matches current Google Generative API.
BASE_URL = "https://generativelanguage.googleapis.com/v1"

# Model name: adjust if required by the API. This is an example; if your account uses another model name, change it.
# New line:
MODEL = "models/gemini-pro"


def call_generative_api(prompt, max_output_tokens=512, temperature=0.2):
    """
    Calls Google Generative Language API using the provided API key and returns the generated text.
    """
    url = f"{BASE_URL}/{MODEL}:generate?key={GEMINI_API_KEY}"
    payload = {
        "prompt": {
            "text": prompt
        },
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Typical response contains 'candidates' list with 'output' or 'content'
        if 'candidates' in data and len(data['candidates']) > 0:
            return data['candidates'][0].get('output') or data['candidates'][0].get('content') or str(data['candidates'][0])
        # Fallback to possible alternative keys
        if 'output' in data:
            return data['output']
        return str(data)
    except Exception as e:
        # Log and return fallback
        print("Generative API call failed:", e, getattr(e, 'response', None))
        return "I'm sorry — I couldn't fetch an answer right now."


def get_gemini_response(prompt):
    """
    Get a conversational/QA response for the given prompt.
    """
    return call_generative_api(prompt, max_output_tokens=400)


def translate_text(text, target_language):
    """
    Translate `text` to `target_language`. Uses the generative model to translate if a dedicated translation API is not available.
    Example: prompt for translation.
    """
    if not text:
        return text
    prompt = f"Translate the following text to {target_language}:\n\n{text}"
    return call_generative_api(prompt, max_output_tokens=400)
