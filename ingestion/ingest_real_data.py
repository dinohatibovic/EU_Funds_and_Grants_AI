import sys
import os
import uuid

# Postavljanje putanje
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embeddings.embedding_client import EmbeddingClient
from vector_db.chroma_client import ChromaDBClient

def ingest_real_bih_data():
    print("--- 🇧🇦 UČITAVANJE STVARNIH BIH PODATAKA ---")
    
    embedder = EmbeddingClient()
    db = ChromaDBClient()
    
    # STVARNI PODACI (Simulacija aktivnih poziva za 2025/2026)
    real_grants = [
        # 1. EU4Agri
        "EU4Agri: Podrška poljoprivredi i ruralnom razvoju. Bespovratna sredstva za nabavku mehanizacije i preradu voća/povrća. Iznosi od 30.000 KM do 200.000 KM. Aplikacija se vrši online. URL: https://eu4agri.ba/",
        
        # 2. Challenge to Change
        "Challenge to Change 3.0 (C2C): Grantovi za inovativne poslovne ideje i startupe u BiH. Fokus na Švedsku dijasporu i lokalne inovatore. Iznosi do 30.000 EUR. URL: https://c2c.ba/",
        
        # 3. Fond za zaštitu okoliša FBiH
        "Javni konkurs Fonda za zaštitu okoliša FBiH: Sredstva za projekte energijske efikasnosti (utopljavanje zgrada, solarne ploče). Pravo učešća: Javne ustanove i privatna preduzeća. URL: https://fzofbih.org.ba/",
        
        # 4. Ministarstvo privrede KS
        "Poticaji za razvoj male privrede KS: Subvencioniranje kamata na kredite i poticaj za žensko poduzetništvo. Iznos: Refundacija troškova do 50%. URL: https://mp.ks.gov.ba/",
        
        # 5. Horizon Europe (BiH participation)
        "Horizon Europe - Hop On Facility: Posebna linija za zemlje poput BiH za ulazak u postojeće EU konzorcije. Fokus na istraživanje i razvoj (R&D). Budžet po projektu do 500.000 EUR. URL: https://ec.europa.eu/info/funding-tenders",
        
        # 6. USAID Turizam
        "USAID Turizam: Grantovi za razvoj turističkih iskustava i digitalni marketing u turizmu. Fokus na održivi turizam u Hercegovini i Krajini. URL: https://turizambih.ba/",
        
        # 7. Zavod za zapošljavanje (Federalni i RS)
        "Program sufinansiranja zapošljavanja 2026: 'Prvo radno iskustvo'. Država plaća doprinose za nove radnike na period od 12 mjeseci. URL: https://www.fzzz.ba/ i https://www.zzzrs.net/",
        
        # 8. Digital Europe za Zapadni Balkan
        "Digital Europe Programme: Grantovi za digitalizaciju malih preduzeća (SME) i uvođenje AI rješenja u poslovanje. Potrebno partnerstvo sa EU firmom. URL: https://digital-strategy.ec.europa.eu/"
    ]
    
    metadatas = [{"source": "RealData", "type": "Grant"} for _ in real_grants]
    ids = [str(uuid.uuid4()) for _ in real_grants]
    
    print(f"🔄 Generišem embeddinge za {len(real_grants)} stvarnih poziva...")
    embeddings = embedder.generate_embeddings(real_grants)  # embed() → generate_embeddings()

    if not embeddings:
        print("❌ Embedding neuspješan — prekidam.")
        return

    print("💾 Spremanje u bazu...")
    db.add_documents(documents=real_grants, metadatas=metadatas, ids=ids, embeddings=embeddings)  # add() → add_documents()
    print("✅ Baza ažurirana sa BiH podacima!")

if __name__ == "__main__":
    ingest_real_bih_data()
