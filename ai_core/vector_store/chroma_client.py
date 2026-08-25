import chromadb
import os
import logging

DEFAULT_CHROMA_COLLECTION = "eu_grants"

# Postavke za logiranje da vidimo šta se dešava
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChromaDBClient:
    def __init__(self):
        # Definišemo gdje će baza živjeti na disku (env-konfigurabilno;
        # default zadržava stari path da postojeći deploy nastavi raditi)
        self.db_path = os.getenv(
            "CHROMA_DB_PATH",
            os.path.join(os.getcwd(), "vector_db", "chroma_db_data"),
        )
        
        # Kreiramo folder ako ne postoji
        os.makedirs(self.db_path, exist_ok=True)
        
        # Povezujemo se na Persistent Client (to znači da podaci ostaju i kad ugasiš skriptu)
        try:
            self.client = chromadb.PersistentClient(path=self.db_path)
            
            # Kreiramo kolekciju 'eu_grants'. 
            # ChromaDB automatski prepoznaje dimenziju vektora (3072) kod prvog upisa.
            self.collection = self.client.get_or_create_collection(name=DEFAULT_CHROMA_COLLECTION)
            print(f"--- ChromaDB Path: {self.db_path} ---")
            print("✅ Kolekcija 'eu_grants' spremna.")
            
        except Exception as e:
            print(f"❌ Greška pri kreiranju Chroma klijenta: {e}")
            raise e

    def add_documents(self, documents, metadatas, ids, embeddings):
        """
        Ova funkcija je falila! Ona dodaje podatke u bazu.
        """
        try:
            # ChromaDB native metoda se zove 'add'
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            return True
        except Exception as e:
            print(f"❌ Greška pri upisu u ChromaDB: {e}")
            return False

    def sync_documents(
        self,
        documents,
        metadatas,
        ids,
        embeddings,
    ):
        """Upsert a validated dataset, then remove only stale records."""
        lengths = {
            len(documents),
            len(metadatas),
            len(ids),
            len(embeddings),
        }

        if not ids:
            raise ValueError(
                "At least one document is required for synchronization."
            )

        if len(lengths) != 1:
            raise ValueError(
                "Documents, metadatas, ids and embeddings "
                "must have equal lengths."
            )

        if len(set(ids)) != len(ids):
            raise ValueError(
                "Document IDs must be unique."
            )

        existing_ids = set(
            self.collection.get()["ids"]
        )

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

        stale_ids = sorted(
            existing_ids - set(ids)
        )

        if stale_ids:
            self.collection.delete(ids=stale_ids)

        return self.collection.count()

    def query(self, query_embeddings, n_results=5):
        """
        Pretražuje bazu koristeći vektore.
        """
        try:
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results
            )
            return results
        except Exception as e:
            print(f"❌ Greška pri pretrazi: {e}")
            return None
