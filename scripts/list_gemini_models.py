import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    # Fallback to verify if the placeholder is still there or if user didn't set it
    print("GOOGLE_API_KEY not found in env.")
    exit(1)

endpoints = [
    "https://generativelanguage.googleapis.com/v1/models",
    "https://generativelanguage.googleapis.com/v1beta/models"
]

for base_url in endpoints:
    url = f"{base_url}?key={api_key}"
    print(f"\nQuerying: {base_url}")

    try:
        response = requests.get(url)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"Found {len(models)} models:")
            for m in models:
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    # Filter for flash models to be concise
                    if "flash" in m['name']:
                        print(f" - {m['name']} (Display: {m.get('displayName')})")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
