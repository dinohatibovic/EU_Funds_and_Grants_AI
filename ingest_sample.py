import os
import sys
import uuid
from dotenv import load_dotenv

# --- DIO 1: DIJAGNOSTIKA OKRUŽENJA ---
# Odmah ispisujemo poruku da znamo da je Python pokrenuo skriptu.
# Ovo sprečava "tihu smrt" programa.
print("--- 🚀 POKRETANJE SKRIPTE ZA INGESTIJU (v2.0 Diagnostic) ---")

# Učitavanje varijabli iz .env fajla
# Ovo je ključno jer se tu nalazi tvoj GEMINI_API_KEY
load_dotenv()

# Provjera API ključa ODMAH na početku
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ GREŠKA: GEMINI_API_KEY nije pronađen u .env fajlu!")
    print("   Mogući razlozi:")
    print("   1. Nemaš .env fajl.")
    print("   2. Fajl se zove .env.txt (pogrešno).")
    print("   3. Nisi ga exportovao u terminalu.")
    print("   Skripta se gasi radi sigurnosti.")
    sys.exit(1) # Izlazimo sa kodom greške
else:
    # Prikazujemo samo prva 4 slova ključa radi sigurnosti.
    # Ako ovo vidiš, znači da Python "vidi" tvoj ključ.
    print(f"✅ API Ključ detektovan: {api_key[:4]}********")

# Dodavanje putanje za importe
# Ovo govori Pythonu: "Traži fajlove i u trenutnom folderu".
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Pokušaj importa naših modula
# Ovdje provjeravamo da li postoje fajlovi embedding_client.py i chroma_client.py
try:
    print("--- Učitavanje AI modula... ---")
    from embeddings.embedding_client import EmbeddingClient
    from vector_db.chroma_client import ChromaDBClient
    print("✅ Moduli (Embedding i Chroma) uspješno učitani.")
except ImportError as e:
    print(f"❌ GREŠKA PRI IMPORTU: {e}")
    print("   Provjeri da li folderi 'embeddings' i 'vector_db' postoje i imaju __init__.py")
    sys.exit(1)
except Exception as e:
    print(f"❌ NEOČEKIVANA GREŠKA PRI IMPORTU: {e}")
    sys.exit(1)

# --- DIO 2: DEFINICIJA PODATAKA ---
# Ovo su testni podaci specifični za BiH i EU fondove.
# Oni će biti pretvoreni u vektore i poslani na server.
SAMPLE_DOCUMENTS = [
    {
        "text": "EU4Business is an EU project that supports startups in Bosnia and Herzegovina. Total budget is 16 million EUR. Grants are available for tourism and agriculture.",
        "metadata": {"source": "EU4Business", "category": "Startups", "year": "2024", "country": "BiH"}
    },
    {
        "text": "Horizon Europe offers funding for research and innovation. Universities in Sarajevo and Banja Luka are eligible. Focus on Green Deal and Digital Transformation.",
        "metadata": {"source": "Horizon Europe", "category": "Research", "year": "2025", "country": "EU/BiH"}
    },
    {
        "text": "Challenge to Change (C2C) provides grants up to 30,000 EUR for SMEs in BiH. The focus is on innovative products and services.",
        "metadata": {"source": "C2C", "category": "SME", "year": "2024", "country": "BiH"}
    },
    {
        "text": "IPARD funds are not yet fully available in BiH, but pre-accession assistance helps farmers improve machinery and production standards.",
        "metadata": {"source": "IPARD", "category": "Agriculture", "year": "2024", "country": "BiH"}
    },
    {
        "text": "Creative Europe supports cultural sectors in BiH. Museums, theaters, and artists can apply for cooperation projects.",
        "metadata": {"source": "Creative Europe", "category": "Culture", "year": "2024", "country": "BiH"}
    }
]

# --- DIO 3: GLAVNI PROCES ---
def main():
    print("\n--- 🏁 POČETAK GLAVNOG PROCESA ---")
    
    # 1. Inicijalizacija Klijenata
    try:
        print("1. Inicijalizacija Embedding Klijenta (Gemini)...")
        embed_client = EmbeddingClient()
        
        print("2. Inicijalizacija ChromaDB Klijenta (Lokalna Baza)...")
        chroma_client = ChromaDBClient()
        print("✅ Klijenti spremni.")
    except Exception as e:
        print(f"❌ GREŠKA KOD INICIJALIZACIJE: {e}")
        return

    # 2. Priprema podataka za slanje
    print(f"\n3. Priprema {len(SAMPLE_DOCUMENTS)} dokumenata za obradu...")
    texts = [doc["text"] for doc in SAMPLE_DOCUMENTS]
    metadatas = [doc["metadata"] for doc in SAMPLE_DOCUMENTS]
    ids = [str(uuid.uuid4()) for doc in SAMPLE_DOCUMENTS]

    # 3. Generisanje Embeddinga (Slanje na Google servere)
    print("4. Slanje teksta na Gemini API za vektorizaciju...")
    print("   (Ovo može potrajati 2-5 sekundi, ovisno o internetu...)")
    try:
        embeddings = embed_client.generate_embeddings(texts)
        if not embeddings:
            print("❌ GREŠKA: Gemini je vratio praznu listu! Provjeri kvotu ili ključ.")
            return
        print(f"✅ Uspjeh! Generisano {len(embeddings)} vektora.")
        # Provjera dimenzija (Mora biti 768 za Gemini Flash/Pro embeddinge)
        if len(embeddings) > 0:
            print(f"   Dimenzija prvog vektora: {len(embeddings[0])} (Očekivano 768)")
    except Exception as e:
        print(f"❌ KATASTROFALNA GREŠKA KOD GEMINI API-ja: {e}")
        return

    # 4. Pohrana u Bazu (ChromaDB)
    print("\n5. Pohrana vektora u lokalnu ChromaDB bazu...")
    try:
        success = chroma_client.add_documents(texts, metadatas, ids, embeddings)
        if success:
            print("✅ Podaci uspješno upisani u fajl 'chroma.sqlite3'!")
        else:
            print("⚠️ Upozorenje: Funkcija add_documents je vratila False. Nešto nije u redu sa bazom.")
    except Exception as e:
        print(f"❌ GREŠKA KOD UPISA U BAZU: {e}")
        return

    # 5. Testna Pretraga (Verifikacija)
    print("\n6. Testna pretraga: 'grants for startups in BiH'...")
    try:
        query_text = "grants for startups in BiH"
        # I upit moramo pretvoriti u vektor da bi ga uporedili
        query_embedding = embed_client.generate_embeddings([query_text])[0]
        results = chroma_client.query(query_embedding, n_results=2)
        
        print("\n--- 🔍 REZULTATI PRETRAGE (DOKAZ DA RADI) ---")
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                print(f"Rezultat {i+1}: {doc}")
        else:
            print("⚠️ Nema rezultata. Baza je možda prazna.")
            
    except Exception as e:
        print(f"❌ GREŠKA KOD TESTNE PRETRAGE: {e}")

    print("\n==================================================")
    print("🎉 INGESTIJA ZAVRŠENA USPJEŠNO! SPREMNO ZA GIT PUSH.")
    print("==================================================")

# Ova linija osigurava da se kod pokrene samo kad ga ti pozoveš direktno
if __name__ == "__main__":
    main()
