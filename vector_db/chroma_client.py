import chromadb
import os
import logging

# Postavke za logiranje da vidimo šta se dešava
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChromaDBClient:
    def __init__(self):
        # Definišemo gdje će baza živjeti na disku
        self.db_path = os.path.join(os.getcwd(), "vector_db", "chroma_db_data")
        
        # Kreiramo folder ako ne postoji
        os.makedirs(self.db_path, exist_ok=True)
        
        # Povezujemo se na Persistent Client (to znači da podaci ostaju i kad ugasiš skriptu)
        try:
            self.client = chromadb.PersistentClient(path=self.db_path)
            
            # Kreiramo kolekciju 'eu_grants'. 
            # ChromaDB automatski prepoznaje dimenziju vektora (3072) kod prvog upisa.
            self.collection = self.client.get_or_create_collection(name="eu_grants")
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
