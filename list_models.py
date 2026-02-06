import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("\n--- 🤖 DOSTUPNI EMBEDDING MODELI (Fix) ---")
try:
    for m in client.models.list():
        # U novom SDK-u se koristi 'supported_actions'
        if 'embedContent' in m.supported_actions:
            print(f"Model ID: {m.name}")
except Exception as e:
    print(f"Greška: {e}")
    # Plan B: Ispiši sve atribute da vidimo šta Google šalje
    print("Pokušavam alternativnu metodu...")
    for m in client.models.list():
         if "embed" in m.name.lower():
             print(f"Pronađen embedding model: {m.name}")
print("------------------------------------------\n")
