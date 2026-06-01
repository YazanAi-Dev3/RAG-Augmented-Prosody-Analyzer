import os
import json
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from app.core.config import settings

class RAGEngine:
    def __init__(self):
        self.collection_name = "arab_poetry_db"
        self.vector_size = 1024  
        self.data_path = "data/poetry_rag_db.json"
        
        print("--- Initializing RAG Engine ---")
        self._initialize_embedder()
        self._initialize_qdrant()

    def _initialize_embedder(self):
        if os.path.exists(settings.EMBEDDING_MODEL_PATH):
            print(f"Loading Embedding Model locally from {settings.EMBEDDING_MODEL_PATH}...")
            self.embedder = SentenceTransformer(settings.EMBEDDING_MODEL_PATH)
        else:
            print("Local Embedding Model not found. Downloading 'BAAI/bge-m3' from HuggingFace...")
            self.embedder = SentenceTransformer('BAAI/bge-m3')
            
            os.makedirs(settings.EMBEDDING_MODEL_PATH, exist_ok=True)
            self.embedder.save(settings.EMBEDDING_MODEL_PATH)
            print(f"Model successfully saved to {settings.EMBEDDING_MODEL_PATH}")

    def _initialize_qdrant(self):
        print(f"Connecting to local Qdrant database at {settings.QDRANT_STORAGE_PATH}...")
        self.qdrant = QdrantClient(path=settings.QDRANT_STORAGE_PATH)
        
        collections_response = self.qdrant.get_collections()
        collections = [col.name for col in collections_response.collections]
        
        if self.collection_name not in collections:
            print(f"Collection '{self.collection_name}' not found. Building database from JSON...")
            self._build_database()
        else:
            count = self.qdrant.count(collection_name=self.collection_name).count
            print(f"Collection '{self.collection_name}' found with {count} vectors. Ready!")

    def _build_database(self):
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Data file {self.data_path} is missing! Cannot build DB.")

        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
        )

        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"Loaded {len(data)} verses from JSON. Starting embedding and injection...")

        points = []
        for i, item in enumerate(data):
            difficult_words_str = " ".join([dw['word'] + " " + dw['meaning'] for dw in item['semantics']['difficult_words']])
            text_to_embed = f"{item['verse_text']} | {difficult_words_str} | {item['semantics']['explanation_simple']}"
            
            vector = self.embedder.encode(text_to_embed).tolist()

            payload = {
                "verse_id": item.get("verse_id"),
                "verse_text": item.get("verse_text"),
                "poet": item["metadata"]["poet"],
                "era": item["metadata"]["era"],
                "meter": item["metadata"]["meter"],
                "rhyme": item["metadata"]["rhyme"],
                "theme": item["metadata"]["theme"],
                "difficult_words": item["semantics"]["difficult_words"],
                "explanation_simple": item["semantics"]["explanation_simple"],
                "explanation_detailed": item["semantics"]["explanation_detailed"]
            }

            point_id = i + 1  
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=points
        )
        print("Database successfully built and vectors injected!")

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        
        query_vector = self.embedder.encode(query).tolist()
        
        search_response = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k
        )
        
        results = []
        for hit in search_response.points:
            results.append({
                "score": hit.score,
                "payload": hit.payload
            })
            
        return results

rag_engine = RAGEngine()