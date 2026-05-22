import os
from dotenv import load_dotenv
from groq import Groq
import requests

load_dotenv()

def test_groq():
    print("Testing Groq...")
    key = os.getenv("GROQ_API_KEY")
    if not key:
        print("GROQ_API_KEY not found")
        return
    try:
        client = Groq(api_key=key)
        # Using the model from the code: llama-3.3-70b-versatile
        # Note: the 'groq/' prefix is for litellm, for groq python client we use the model id
        client.chat.completions.create(
            messages=[{"role": "user", "content": "Hi"}],
            model="llama-3.3-70b-versatile",
        )
        print("✅ Groq API Key is WORKING")
    except Exception as e:
        print(f"❌ Groq API Key FAILED: {e}")

def test_openrouter():
    print("Testing OpenRouter...")
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        print("OPENROUTER_API_KEY not found")
        return
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "meta-llama/llama-3.3-70b-instruct",
                "messages": [{"role": "user", "content": "Hi"}]
            }
        )
        if response.status_code == 200:
            print("✅ OpenRouter API Key is WORKING")
        else:
            print(f"❌ OpenRouter API Key FAILED: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ OpenRouter API Key FAILED: {e}")

if __name__ == "__main__":
    test_groq()
    test_openrouter()
