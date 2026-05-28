try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    Settings = None
from typing import List, Dict, Any, Optional
import os

class ChromaStore:
    def __init__(self, persist_directory: str = "./storage/chroma"):
        self.persist_directory = persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
    def get_or_create_collection(self, collection_name: str):
        """
        Creates or retrieves a collection for a specific repository.
        """
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"} # Using cosine similarity for code embeddings
        )

    def add_chunks(self, collection_name: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        Adds code chunks with their embeddings and metadata to Chroma.
        Following PRD Section 7.5 metadata requirements.
        """
        collection = self.get_or_create_collection(collection_name)
        
        ids = [f"{chunk['file_path']}_{chunk['start_line']}" for chunk in chunks]
        documents = [chunk['content'] for chunk in chunks]
        metadatas = [{
            "file_path": chunk['file_path'],
            "chunk_type": chunk['chunk_type'],
            "symbol_name": chunk['symbol_name'],
            "start_line": chunk['start_line'],
            "end_line": chunk['end_line'],
            "content_hash": chunk['content_hash']
        } for chunk in chunks]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

    def search(self, collection_name: str, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Performs semantic search using query embeddings.
        """
        collection = self.get_or_create_collection(collection_name)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results for the reasoning agent
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "id": results['ids'][0][i],
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "score": 1 - results['distances'][0][i] # Convert distance to similarity
            })
            
        return formatted_results

    def delete_collection(self, collection_name: str):
        self.client.delete_collection(name=collection_name)
