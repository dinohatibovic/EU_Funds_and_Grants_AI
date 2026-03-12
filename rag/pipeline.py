"""
RAG PIPELINE - Retrieval Augmented Generation
==============================================
"""

from embeddings.embedding_client import EmbeddingClient
from vector_db.chroma_client import ChromaDBClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGPipeline:
    """Complete RAG pipeline for grant search."""
    
    def __init__(self):
        """Initialize RAG pipeline."""
        try:
            self.embedding_client = EmbeddingClient()
            self.db_client = ChromaDBClient()
            self.collection = self.db_client.client.get_or_create_collection("grants")
            logger.info("✅ RAG Pipeline initialized")
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            raise
    
    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """Search for relevant grants."""
        try:
            logger.info(f"🔍 Searching: {query}")
            
            # Generate query embedding
            query_embedding = self.embedding_client.generate_embeddings([query])[0]
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            for i, (doc_id, doc_text, metadata) in enumerate(zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0]
            )):
                formatted_results.append({
                    "rank": i + 1,
                    "id": doc_id,
                    "title": metadata.get("title", "N/A"),
                    "category": metadata.get("category", "N/A"),
                    "text": doc_text,
                    "relevance": "High" if i < 3 else "Medium"
                })
            
            logger.info(f"✅ Found {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return []
    
    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return {
            "total_documents": self.collection.count(),
            "embedding_dimension": self.embedding_client.dimension,
            "model": self.embedding_client.model_name
        }


if __name__ == "__main__":
    try:
        print("\n" + "=" * 70)
        print("RAG PIPELINE TEST")
        print("=" * 70)
        
        pipeline = RAGPipeline()
        
        # Test queries
        queries = [
            "EU funding for AI projects",
            "Grants for startups in Bosnia",
            "Digital transformation support"
        ]
        
        for query in queries:
            print(f"\n📌 Query: {query}")
            print("-" * 70)
            results = pipeline.search(query, n_results=3)
            for result in results:
                print(f"\n   {result['rank']}. {result['title']}")
                print(f"      Category: {result['category']}")
                print(f"      Text: {result['text'][:60]}...")
        
        # Stats
        print("\n" + "=" * 70)
        print("PIPELINE STATISTICS")
        print("=" * 70)
        stats = pipeline.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
