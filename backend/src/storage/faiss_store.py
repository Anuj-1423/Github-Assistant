import faiss
import numpy as np
import os
import pickle
from typing import List, Dict, Any

class FAISSStore:
    """
    Stores and queries embeddings using FAISS.
    Following PRD Section 7.5 requirements.
    """
    def __init__(self, repo_id: str, dimension: int = 384, storage_dir: str = "./storage/vectors"):
        self.repo_id = repo_id
        self.dimension = dimension
        self.storage_path = os.path.join(storage_dir, f"{repo_id}.index")
        self.id_map_path = os.path.join(storage_dir, f"{repo_id}_ids.pkl")
        os.makedirs(storage_dir, exist_ok=True)
        
        self.index = faiss.IndexFlatIP(dimension) # Inner product for cosine similarity with normalized vectors
        self.chunk_ids = []
        
        if os.path.exists(self.storage_path):
            self.load()

    def add_embeddings(self, chunk_ids: List[str], embeddings: List[List[float]]):
        embeddings_np = np.array(embeddings).astype('float32')
        self.index.add(embeddings_np)
        self.chunk_ids.extend(chunk_ids)
        self.save()

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        query_np = np.array([query_embedding]).astype('float32')
        distances, indices = self.index.search(query_np, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.chunk_ids):
                results.append({
                    "chunk_id": self.chunk_ids[idx],
                    "score": float(distances[0][i])
                })
        return results

    def save(self):
        faiss.write_index(self.index, self.storage_path)
        with open(self.id_map_path, 'wb') as f:
            pickle.dump(self.chunk_ids, f)

    def load(self):
        self.index = faiss.read_index(self.storage_path)
        with open(self.id_map_path, 'rb') as f:
            self.chunk_ids = pickle.load(f)
