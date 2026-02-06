import os
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

class EmbeddingClient:
    """
    Klijent za generisanje vektorskih reprezentacija teksta (Embeddings)
    koristeći Google Gemini API.
    
    Model: models/gemini-embedding-001 (Verifikovan za tvoj API ključ)
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("⚠️ UPOZORENJE: GEMINI_API_KEY nije pronađen u .env fajlu. Embedding će neuspjeti.")
            self.client = None
            return

        # Inicijalizacija Gemini klijenta verzije 1.0+
        try:
            self.client = genai.Client(api_key=self.api_key)
            print("✅ Gemini Klijent uspješno inicijalizovan.")
        except Exception as e:
            print(f"❌ Greška pri inicijalizaciji Gemini klijenta: {e}")
            self.client = None

    def generate_embeddings(self, texts):
        """
        Šalje tekst na Google servere i vraća listu vektora (brojeva).
        Uključuje Retry logiku u slučaju mrežnih grešaka.
        """
        if not self.client:
            print("❌ Klijent nije inicijalizovan. Prekidam.")
            return []

        if isinstance(texts, str):
            texts = [texts]

        # Čišćenje teksta: Gemini ne voli nove redove u embedding zahtjevima
        # Ovo osigurava bolju kvalitetu vektora.
        cleaned_texts = [t.replace("\n", " ").strip() for t in texts]
        
        # Filtriranje praznih stringova da ne trošimo API pozive uzalud
        cleaned_texts = [t for t in cleaned_texts if t]
        
        if not cleaned_texts:
            print("⚠️ Upozorenje: Prazan tekst poslan na embedding.")
            return []

        # Pokušaj slanja zahtjeva sa jednostavnom 'retry' logikom
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # KLJUČNA IZMJENA: Koristimo tačan naziv modela koji smo otkrili
                result = self.client.models.embed_content(
                    model="models/gemini-embedding-001",
                    contents=cleaned_texts
                )
                
                # Ekstrakcija vektora iz odgovora
                # Google vraća objekat koji sadrži listu embeddinga
                embeddings = [e.values for e in result.embeddings]
                
                # Verifikacija dimenzija (Trebalo bi biti 768 za ovaj model)
                if embeddings:
                    print(f"✨ Uspjeh! Generisano {len(embeddings)} vektora (Dimenzija: {len(embeddings[0])})")
                
                return embeddings

            except Exception as e:
                print(f"⚠️ Greška pri embeddingu (Pokušaj {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2) # Sačekaj 2 sekunde prije novog pokušaja
                else:
                    print("❌ Svi pokušaji neuspješni.")
                    return []
