"""
ingest_local_grants.py
======================
Učitava lokalne i federalne grantove iz data/grants.json u ChromaDB
kolekciju 'eu_grants'. Preskače ID-eve koji već postoje (upsert logika).

Pokretanje:
    cd EU_Funds_and_Grants_AI
    source venv/bin/activate
    python3 ingestion/ingest_local_grants.py
"""

import json
import logging
import sys
from pathlib import Path

# Dodaj root projekta u Python path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from embeddings.embedding_client import EmbeddingClient
from vector_db.chroma_client import ChromaDBClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Kategorije koje se tretiraju kao lokalni/federalni grantovi
LOCAL_CATEGORIES = {
    "Federalni",
    "Kantonalni (ZDK)",
    "EU/GIZ",
    "EU/UNDP",
    "Specijalni (FBiH)",
    "Nacionalni",
    # Uključi i generičke kategorije iz starih ID-eva
    "National Grant",
    "Specialized",
}

COLLECTION_NAME = "eu_grants"
DATA_FILE = ROOT / "data" / "grants.json"


def build_embed_text(grant: dict) -> str:
    """Gradi tekst koji se embeduje — kombinuje sva relevantna polja."""
    parts = [
        grant.get("title", ""),
        f"Kategorija: {grant.get('category', '')}",
        grant.get("description", ""),
        f"Rok: {grant.get('deadline', 'nije naveden')}",
        f"Budžet: {grant.get('budget', 'nije naveden')}",
    ]
    note = grant.get("note", "")
    if note:
        parts.append(f"Napomena: {note}")
    url = grant.get("url", "")
    if url:
        parts.append(f"Izvor: {url}")
    return ". ".join(p for p in parts if p.strip())


def load_grants(path: Path) -> list[dict]:
    """Čita grants.json i vraća sve grantove."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> bool:
    print("\n" + "=" * 65)
    print("  INGESTION — Lokalni i federalni grantovi → ChromaDB")
    print("=" * 65)

    # 1. Učitaj JSON
    print(f"\n[1/4] Učitavam {DATA_FILE.name}...")
    try:
        all_grants = load_grants(DATA_FILE)
        logger.info(f"Ukupno grantova u fajlu: {len(all_grants)}")
    except FileNotFoundError:
        logger.error(f"Fajl nije pronađen: {DATA_FILE}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Greška pri parsiranju JSON-a: {e}")
        return False

    # Filtriranje nije potrebno — ingestujemo SVE grantove
    # (baza treba biti kompletna za RAG pretragu)
    grants_to_ingest = all_grants
    logger.info(f"Grantova za ingestion: {len(grants_to_ingest)}")

    # 2. Inicijalizuj klijente
    print("\n[2/4] Inicijalizujem klijente...")
    try:
        emb_client = EmbeddingClient()
        db_client  = ChromaDBClient()
        collection = db_client.client.get_or_create_collection(COLLECTION_NAME)
        existing   = set(collection.get()["ids"])
        logger.info(f"Kolekcija '{COLLECTION_NAME}' ima {len(existing)} postojecih dokumenata")
    except Exception as e:
        logger.error(f"Greška pri inicijalizaciji: {e}")
        return False

    # 3. Pripremi dokumente (preskoči postojeće)
    print("\n[3/4] Priprema dokumenata...")
    new_docs   = []
    new_ids    = []
    new_meta   = []
    new_texts  = []

    for g in grants_to_ingest:
        gid = g.get("id", "")
        if not gid:
            logger.warning(f"Grant bez ID-a, preskačem: {g.get('title','?')}")
            continue
        if gid in existing:
            logger.info(f"  Preskačem (već postoji): {gid}")
            continue

        text = build_embed_text(g)
        new_texts.append(text)
        new_ids.append(gid)
        new_docs.append(text)
        new_meta.append({
            "title":    g.get("title", ""),
            "category": g.get("category", ""),
            "budget":   g.get("budget", ""),
            "deadline": g.get("deadline", ""),
            "url":      g.get("url", ""),
            "relevance":g.get("relevance", ""),
        })

    if not new_texts:
        print("\n✅ Svi grantovi su već upisani u bazu — nema novih.")
        return True

    logger.info(f"Novih grantova za upis: {len(new_texts)}")

    # 4. Generiši embeddings i upisi u ChromaDB
    print(f"\n[4/4] Generisanje embeddinga i upis {len(new_texts)} dokumenata...")
    try:
        embeddings = emb_client.embed_batch(new_texts)
        if not embeddings or len(embeddings) != len(new_texts):
            logger.error("Broj embeddinga ne odgovara broju tekstova!")
            return False

        collection.add(
            ids=new_ids,
            embeddings=embeddings,
            documents=new_docs,
            metadatas=new_meta,
        )

        final_count = collection.count()
        print(f"\n{'=' * 65}")
        print(f"  ✅ Upisano {len(new_texts)} novih grantova u ChromaDB")
        print(f"  📦 Ukupno u kolekciji '{COLLECTION_NAME}': {final_count}")
        print(f"{'=' * 65}\n")

    except Exception as e:
        logger.error(f"Greška pri upisu u ChromaDB: {e}")
        return False

    # 5. Brzi test pretrage
    print("Brzi test pretrage...")
    try:
        test_query  = "FMRPO grant poduzetništvo ZDK"
        test_embed  = emb_client.embed_batch([test_query])
        test_result = collection.query(query_embeddings=test_embed, n_results=2)
        docs = test_result.get("documents", [[]])[0]
        print(f"  Upit: '{test_query}'")
        for i, doc in enumerate(docs, 1):
            print(f"  {i}. {doc[:80]}...")
    except Exception as e:
        logger.warning(f"Test pretrage neuspješan (nije kritično): {e}")

    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
