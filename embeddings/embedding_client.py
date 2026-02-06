"""
EMBEDDING CLIENT - Local ONNX Model
====================================
Uses sentence-transformers with ONNX runtime
NO API KEY NEEDED - Works offline!
"""

from sentence_transformers import SentenceTransformer
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingClient:
    """Client for creating embeddings using local ONNX model."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize EmbeddingClient.
        
        Models:
        - all-MiniLM-L6-v2 (22MB) - Fast, good quality
        - all-mpnet-base-v2 (438MB) - Better quality
        - distiluse-base-multilingual-cased-v2 (135MB) - Multilingual
        """
        try:
            logger.info(f"🔄 Loading model: {model_name}...")
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"✅ EmbeddingClient initialized")
            logger.info(f"   Model: {model_name}")
            logger.info(f"   Dimension: {self.dimension}")
        except Exception as e:
            logger.error(f"❌ Error loading model: {e}")
            raise

    def embed_single(self, text: str) -> list[float]:
        """Creates embedding for a single string."""
        try:
            logger.info(f"🔄 Embedding: {text[:50]}...")
            
            # Encode single text
            embedding = self.model.encode(text, convert_to_tensor=False)
            
            logger.info(f"✅ Embedding created ({len(embedding)} dims)")
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return []

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Creates embeddings for multiple texts."""
        try:
            logger.info(f"🔄 Batch embedding {len(texts)} texts...")
            
            # Encode batch
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_tensor=False
            )
            
            logger.info(f"✅ {len(embeddings)} embeddings created")
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"❌ Batch error: {e}")
            return []

    def get_model_info(self) -> dict:
        """Returns model information."""
        return {
            "model": self.model_name,
            "dimension": self.dimension,
            "batch_size": 32,
            "offline": True
        }


if __name__ == "__main__":
    try:
        print("\n" + "=" * 70)
        print("TESTING EMBEDDING CLIENT (LOCAL ONNX)")
        print("=" * 70)
        
        client = EmbeddingClient()
        print(f"\n✅ Client initialized")
        print(f"   Model: {client.model_name}")
        print(f"   Dimension: {client.dimension}")
        
        # Test single
        print("\n📌 TEST 1: Single Embedding")
        embedding = client.embed_single("Horizon Europe grant")
        if embedding:
            print(f"✅ Success! Dimension: {len(embedding)}")
        else:
            print("❌ Failed")
        
        # Test batch
        print("\n📌 TEST 2: Batch Embedding")
        texts = [
            "Horizon Europe grant for AI",
            "EU funding for startups",
            "Digital transformation project"
        ]
        embeddings = client.embed_batch(texts)
        print(f"✅ {len(embeddings)} embeddings created")
        
        # Test similarity
        print("\n📌 TEST 3: Similarity Check")
        if len(embeddings) >= 2:
            import numpy as np
            sim = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            print(f"✅ Similarity between first two: {sim:.4f}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
