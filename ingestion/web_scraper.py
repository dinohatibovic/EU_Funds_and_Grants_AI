import requests
from bs4 import BeautifulSoup
import sys
import os
import uuid

# Dodajemo putanju do projekta da vidimo naše module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embeddings.embedding_client import EmbeddingClient
from vector_db.chroma_client import ChromaDBClient

class GrantScraper:
    def __init__(self):
        self.embedder = EmbeddingClient()
        self.db = ChromaDBClient()
        # "Lažiramo" da smo pravi browser da nas ne blokiraju
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def scrape_and_store(self, url: str):
        print(f"\n🌐 Povezujem se na: {url} ...")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Greška pri pristupu stranici: Status {response.status_code}")
                return

            # Parsiranje HTML-a
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Čišćenje: Uzimamo naslov i tekstove paragrafa
            title = soup.title.string if soup.title else "Nepoznat naslov"
            
            # Trik: Uzimamo sve <p> (paragrafe) i <li> (liste) jer tu bude tekst konkursa
            text_blocks = [p.get_text().strip() for p in soup.find_all(['p', 'li', 'h1', 'h2', 'h3']) if len(p.get_text().strip()) > 50]
            
            # Spajamo u veće cjeline (chunks) da ne embedamo svaku rečenicu posebno
            full_text = "\n".join(text_blocks)
            
            # Ako je tekst predug, uzimamo prvih 2000 karaktera (radi štednje i brzine)
            # U naprednoj verziji bi ovo sjeckali na dijelove (chunking)
            final_content = f"IZVOR: {title} ({url})\n\nSADRŽAJ:\n{full_text[:4000]}"
            
            if len(full_text) < 100:
                print("⚠️ Upozorenje: Pronađeno premalo teksta. Možda stranica koristi JavaScript zaštitu.")
                return

            print(f"📄 Uspješno skinuto! Naslov: {title}")
            print(f"📊 Veličina teksta: {len(final_content)} karaktera")

            # --- RAG PROCES ---
            # 1. Priprema podataka
            doc_id = str(uuid.uuid4())
            metadata = {"source": url, "title": title, "type": "scraped_web"}
            
            print("🔄 Generisanje vektora (Geminija)...")
            embedding = self.embedder.generate_embeddings([final_content])

            print("💾 Spremanje u ChromaDB...")
            self.db.add_documents(
                documents=[final_content],
                metadatas=[metadata],
                ids=[doc_id],
                embeddings=embedding
            )
            
            print("✅ USJPJEŠNO! Ovaj link je sada dio 'mozga' tvog AI agenta.")

        except Exception as e:
            print(f"❌ Kritična greška: {e}")

if __name__ == "__main__":
    scraper = GrantScraper()
    print("--- 🕷️ AI GRANT SCRAPER ---")
    print("Unesi URL stranice sa koje želiš 'pokupiti' znanje.")
    target_url = input("URL >> ").strip()
    
    if target_url:
        scraper.scrape_and_store(target_url)
    else:
        print("Nisi unio URL.")
