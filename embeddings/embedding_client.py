import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

class EmbeddingClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("⚠️ WARNING: GEMINI_API_KEY not found. Embeddings will fail.")
        
        # Inicijalizacija Gemini klijenta
        self.client = genai.Client(api_key=self.api_key)

    def generate_embeddings(self, texts):
        if isinstance(texts, str):
            texts = [texts]
            
        # Čišćenje teksta (novi redovi znaju praviti problem)
        texts = [t.replace("\n", " ") for t in texts]
        
        try:
            # Pozivamo Gemini text-embedding-004 model
            result = self.client.models.embed_content(
                model="text-embedding-004",
                contents=texts
            )
            # Vraćamo listu vektora
            return [e.values for e in result.embeddings]
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return []
