"""
INGESTION PROCESS - Local ONNX Embeddings
==========================================
"""

import logging
from embeddings.embedding_client import EmbeddingClient
from vector_db.chroma_client import ChromaDBClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("\n" + "=" * 70)
    print("🚀 START OF PRODUCTION INGESTION PROCESS")
    print("=" * 70)
    
    # STEP 1: Initialize Clients
    print("\n📌 STEP 1: Initialize Clients")
    print("-" * 70)
    try:
        embedding_client = EmbeddingClient()
        logger.info("✅ EmbeddingClient initialized")
        
        db_client = ChromaDBClient()
        logger.info("✅ ChromaDBClient initialized")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False
    
    # STEP 2: Define Sample Documents
    print("\n📌 STEP 2: Define Sample Documents")
    print("-" * 70)
    
    documents = [
        # EU Grants
        {
            "id": "eu_001",
            "title": "Horizon Europe Call 2026: AI for Healthcare",
            "text": "Funding for AI projects in healthcare sector. Budget: €50M. Deadline: 2026-06-30",
            "category": "EU Grant"
        },
        {
            "id": "eu_002",
            "title": "Digital Europe Programme: SME Digitalization",
            "text": "Support for SME digital transformation. Budget: €100M. Focus: Cloud, AI, Cybersecurity",
            "category": "EU Grant"
        },
        {
            "id": "eu_003",
            "title": "Erasmus+ 2026: Tech Education",
            "text": "Funding for universities and tech education. Budget: €75M",
            "category": "EU Grant"
        },
        # National Grants
        {
            "id": "nat_001",
            "title": "Innovate Bosnia: Local grant for startups",
            "text": "Maximum funding: 50,000 KM. For tech startups in BiH",
            "category": "National Grant"
        },
        {
            "id": "nat_002",
            "title": "Ministry of Development FBiH: SME Incentives",
            "text": "Up to 100,000 KM for SME development. Focus: Export, Innovation",
            "category": "National Grant"
        },
        {
            "id": "nat_003",
            "title": "FIPA Incentives: Investments in IT sector",
            "text": "Up to 150,000 KM for IT sector investments",
            "category": "National Grant"
        },
        # Specialized
        {
            "id": "spec_001",
            "title": "IPA Education Digitalization",
            "text": "Grants for kindergarten and school digitalization",
            "category": "Specialized"
        },
        {
            "id": "spec_002",
            "title": "Environmental Protection Fund",
            "text": "Energy efficiency and renewable energy projects",
            "category": "Specialized"
        },
        {
            "id": "spec_003",
            "title": "Sarajevo Canton: Local grants for startups",
            "text": "Up to 50,000 KM for local startups",
            "category": "Specialized"
        },
        # Additional
        {
            "id": "add_001",
            "title": "EU4Digital: Public administration digitalization",
            "text": "Support for government digital transformation",
            "category": "Additional"
        },
        {
            "id": "add_002",
            "title": "Competitiveness and Innovation Framework",
            "text": "Support for innovation and competitiveness",
            "category": "Additional"
        },
        {
            "id": "add_003",
            "title": "Regional Development Fund",
            "text": "Infrastructure projects in regional development",
            "category": "Additional"
        },
    ]
    
    logger.info(f"✅ {len(documents)} documents defined")
    
    # STEP 3: Generate Embeddings
    print("\n📌 STEP 3: Generate Embeddings (BATCH MODE)")
    print("-" * 70)
    
    try:
        texts = [doc["text"] for doc in documents]
        embeddings = embedding_client.embed_batch(texts)
        
        if not embeddings:
            logger.error("❌ Embeddings not generated")
            return False
        
        logger.info(f"✅ {len(embeddings)} embeddings generated")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False
    
    # STEP 4: Store in ChromaDB
    print("\n📌 STEP 4: Store in ChromaDB")
    print("-" * 70)
    
    try:
        collection = db_client.client.get_or_create_collection("grants")
        
        # Add documents with embeddings
        ids = [doc["id"] for doc in documents]
        metadatas = [{"category": doc["category"], "title": doc["title"]} for doc in documents]
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        
        count = collection.count()
        logger.info(f"✅ {count} documents stored in ChromaDB")
        
    except Exception as e:
        logger.error(f"❌ Error storing in ChromaDB: {e}")
        return False
    
    # STEP 5: Test Search
    print("\n📌 STEP 5: Test Search")
    print("-" * 70)
    
    try:
        query = "EU funding for AI projects"
        query_embedding = embedding_client.embed_single(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )
        
        logger.info(f"✅ Search results for: '{query}'")
        for i, doc in enumerate(results["documents"][0], 1):
            logger.info(f"   {i}. {doc[:60]}...")
        
    except Exception as e:
        logger.error(f"❌ Search error: {e}")
    
    print("\n" + "=" * 70)
    print("✅ INGESTION COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
