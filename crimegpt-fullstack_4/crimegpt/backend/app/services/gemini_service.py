import requests

from app.config import GEMINI_API_KEY

GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def gemini_available() -> bool:
    return bool(GEMINI_API_KEY) and GEMINI_API_KEY != "MY_GEMINI_API_KEY"


def call_gemini(contents: list[dict], system_instruction: str, model: str = "gemini-2.0-flash") -> str | None:
    if not gemini_available():
        return None

    url = GEMINI_URL_TEMPLATE.format(model=model)
    try:
        response = requests.post(
            f"{url}?key={GEMINI_API_KEY}",
            json={
                "contents": contents,
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "generationConfig": {"temperature": 0.7},
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini API call failed, falling back to local engine: {e}")
        return None
