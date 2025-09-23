import os
import requests

# 🔑 API key read from environment (safe way, no hardcoding)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

# ✅ Latest Gemini models (change if you have access to others)
# Options: "models/gemini-1.5-flash", "models/gemini-1.5-pro"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL") or "models/gemini-1.5-flash"

# ✅ Correct base URL (⚠️ Gemini API works on v1beta)
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def call_generative_api(prompt, max_output_tokens=512, temperature=0.7, timeout=30):
    """
    Calls Google Gemini API using the correct REST format.
    POST https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("❌ GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set.")

    url = f"{BASE_URL}/{GEMINI_MODEL}:generateContent"
    params = {"key": GEMINI_API_KEY}

    # ✅ Gemini expects "contents" → "parts" → {"text": ...}
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

        # ✅ Parse Gemini response
        # Expected: {"candidates":[{"content":{"parts":[{"text":"..."}]}}]}
        if "candidates" in data and data["candidates"]:
            cand = data["candidates"][0]
            if "content" in cand and "parts" in cand["content"]:
                parts = cand["content"]["parts"]
                if parts and "text" in parts[0]:
                    return parts[0]["text"]

        # fallback
        return str(data)

    except requests.exceptions.HTTPError as http_err:
        print(f"⚠️ HTTP error: {http_err} | Response: {http_err.response.text if http_err.response else ''}")
        return "I'm sorry — the model could not generate an answer right now."
    except Exception as e:
        print("⚠️ API call failed:", e)
        return "I'm sorry — I couldn't contact the model right now."


def get_gemini_response(prompt):
    """Simple helper for direct prompts"""
    return call_generative_api(prompt, max_output_tokens=400)


def translate_text(text, target_language):
    """Translate text using Gemini"""
    if not text:
        return text
    t_prompt = f"Translate the following text to {target_language}:\n\n{text}"
    return call_generative_api(t_prompt, max_output_tokens=200)


# 🟢 Example test
if __name__ == "__main__":
    ans = get_gemini_response("Write a short welcome message for a university chatbot.")
    print("Gemini Response:", ans)
