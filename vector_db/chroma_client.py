import chromadb
import os

class ChromaDBClient:
    """Wrapper for ChromaDB using modern PersistentClient."""

    def __init__(self, collection_name="eu_funds"):
        # Putanja do foldera UNUTAR projekta
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, "chroma_db_data")

        # Kreiramo folder ako ne postoji
        os.makedirs(db_path, exist_ok=True)

        print(f"--- ChromaDB Path: {db_path} ---")

        # Inicijalizacija PersistentClient-a
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def query(self, query_embeddings, top_k=5):
        return self.collection.query(
            query_embeddings=query_embeddings,
            n_results=top_k
        )

    def add(self, documents, metadatas, ids, embeddings):
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )
