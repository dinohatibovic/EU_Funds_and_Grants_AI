import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_API_KEY")

print("\n--- 🔍 DIJAGNOSTIKA KLJUČA ---")
if not key:
    print("❌ STATUS: Ključ NIJE pronađen u sistemu!")
else:
    print(f"✅ STATUS: Ključ je uspješno učitan.")
    print(f"📏 DUŽINA: {len(key)} karaktera")
    print(f"🔑 POČETAK: {key[:8]}...")
    print(f"📂 IZVOR: {'Preuzet iz terminala (Export)' if 'GEMINI_API_KEY' in os.environ else 'Preuzet iz .env fajla'}")
print("------------------------------\n")
