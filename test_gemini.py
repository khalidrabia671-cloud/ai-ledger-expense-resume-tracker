import os
from dotenv import load_dotenv
from google import genai

# .env file se key load karo
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ ERROR: .env file mein GEMINI_API_KEY nahi mili. Check karo file sahi jagah hai.")
else:
    print(f"✅ Key mil gayi, shuru hoti hai: {api_key[:6]}...")

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents="Say 'Hello, connection working!' in one short sentence."
        )
        print("✅ SUCCESS! Gemini ka jawab:")
        print(response.text)
    except Exception as e:
        print("❌ ERROR: Gemini se connect nahi ho paya.")
        print(f"Details: {e}")
