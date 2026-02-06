import sys
import os
import uuid
from dotenv import load_dotenv

load_dotenv()  # <-- OVO JE KLJUČNO

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embeddings.embedding_client import EmbeddingClient
from vector_db.chroma_client import ChromaDBClient

