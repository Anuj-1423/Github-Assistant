from typing import List, Dict, Any
from src.storage.storage_factory import get_storage
from src.storage.faiss_store import FAISSStore
from src.embeddings.embedding_model import EmbeddingModel

class HybridRetriever:
    """
    Combines semantic and keyword search.
    Following PRD Section 7.8 requirements.
    """
    def __init__(self, repo_id: str):
        self.repo_id = repo_id
        self.store = get_storage()
        self.faiss = FAISSStore(repo_id)
        self.embedder = EmbeddingModel()

    def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # 1. Semantic Search
        query_embedding = self.embedder.generate_embeddings([query])[0]
        semantic_results = self.faiss.search(query_embedding, top_k=limit)
        
        # 2. Keyword Search
        keyword_results = self.store.keyword_search(self.repo_id, query, top_k=limit)
        
        # 3. Merge Results (Simple Reciprocal Rank Fusion or just combining)
        merged_scores = {}
        
        # Normalize semantic scores (cosine similarity is usually 0-1)
        for res in semantic_results:
            merged_scores[res['chunk_id']] = res['score'] * 0.7 # Weight semantic higher
            
        # Add keyword results
        for res in keyword_results:
            if res['chunk_id'] in merged_scores:
                merged_scores[res['chunk_id']] += 0.3 # Boost if found by both
            else:
                merged_scores[res['chunk_id']] = 0.5
                
        # 4. Sort and Fetch Full Content
        sorted_ids = sorted(merged_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        final_results = []
        for chunk_id, score in sorted_ids:
            chunk_data = self.store.get_chunk_by_id(chunk_id)
            if chunk_data:
                chunk_data['score'] = score
                final_results.append(chunk_data)
                
        return final_results
