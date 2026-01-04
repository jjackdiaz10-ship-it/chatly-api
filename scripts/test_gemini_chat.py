import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("GOOGLE_API_KEY not found.")
    exit(1)

model = "gemini-2.0-flash"
prompt = "Hola, eres un asistente útil?"
sys_instr_text = "Eres un asistente sarcástico."

configs = [
    {
        "name": "v1 stable + camelCase",
        "url": f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}",
        "payload": {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": sys_instr_text}]}
        }
    },
    {
        "name": "v1 stable + snake_case",
        "url": f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}",
        "payload": {
            "contents": [{"parts": [{"text": prompt}]}],
            "system_instruction": {"parts": [{"text": sys_instr_text}]}
        }
    },
    {
        "name": "v1beta + snake_case",
        "url": f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        "payload": {
            "contents": [{"parts": [{"text": prompt}]}],
            "system_instruction": {"parts": [{"text": sys_instr_text}]}
        }
    },
    {
        "name": "v1beta + camelCase",
        "url": f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        "payload": {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": sys_instr_text}]}
        }
    }
]

print(f"Testing Gemini API configs for model: {model}\n")

for config in configs:
    print(f"--- Testing: {config['name']} ---")
    try:
        response = requests.post(config['url'], json=config['payload'], timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS!")
            try:
                text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                print(f"Response: {text[:50]}...")
            except:
                print("Response JSON OK but parsing failed.")
        else:
            print(f"Error: {response.text[:200]}...")
    except Exception as e:
        print(f"Exception: {e}")
    print("\n")
