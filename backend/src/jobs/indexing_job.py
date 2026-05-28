import uuid
import logging
import os
from typing import Dict, Any
from src.ingestion.clone_repo import RepoIngestor
from src.parsing.tree_sitter_parser import get_parser
from src.chunking.code_chunker import CodeChunker
from src.embeddings.embedding_model import EmbeddingModel
from src.storage.storage_factory import get_storage
from src.storage.faiss_store import FAISSStore
from src.graph.graph_builder import CodeGraph

logger = logging.getLogger(__name__)

class IndexingJob:
    """
    Orchestrates the entire indexing process.
    Milestones 1-5.
    """
    def __init__(self, repo_url: str, branch: str = "main", repo_id: str = None):
        self.repo_url = repo_url
        self.branch = branch
        self.repo_id = repo_id or str(uuid.uuid4())[:8]
        
        # Always use absolute paths from root for storage
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        repo_storage = os.path.join(root_dir, "storage", "repos")
        graph_storage = os.path.join(root_dir, "storage", "graphs")
        
        self.store = get_storage()
        
        # Fetch system settings for indexing parameters
        settings = {}
        try:
            if hasattr(self.store, "get_system_settings"):
                settings = self.store.get_system_settings()
        except Exception as e:
            logger.warning(f"Failed to fetch system settings for indexing: {e}")

        chunk_size = settings.get("chunk_size", 2000)
        chunk_overlap = settings.get("chunk_overlap", 200)

        self.ingestor = RepoIngestor(base_storage_path=repo_storage)
        self.embedder = EmbeddingModel()
        self.chunker = CodeChunker(self.repo_id, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.graph = CodeGraph(self.repo_id, storage_dir=graph_storage)

    async def run(self):
        logger.info(f"Starting indexing job for {self.repo_url}")
        
        # 1. Clone Repo
        repo_path = self.ingestor.clone_repo(self.repo_url, self.repo_id)
        if not repo_path:
            return {"status": "FAILED", "error": "Clone failed"}

        # 2. Walk & Parse
        all_chunks = []
        all_parse_results = []
        
        for file_path in self.ingestor.walk_repo(repo_path):
            rel_path = file_path.replace(repo_path, "").lstrip("\\/")
            # Normalize path for all OS
            rel_path = rel_path.replace("\\", "/")
            
            file_extension = f".{rel_path.split('.')[-1]}" if '.' in rel_path else ""
            parser = get_parser(file_extension)
            
            try:
                # Attempt to read as text; will raise error for binaries
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if parser:
                    parse_result = parser.parse_file(content)
                    parse_result['file_path'] = rel_path
                    all_parse_results.append(parse_result)
                    
                    chunks = self.chunker.chunk_file(rel_path, parse_result, content)
                    all_chunks.extend(chunks)
                else:
                    # Add to parse results so it appears in the architecture map
                    all_parse_results.append({
                        "file_path": rel_path,
                        "functions": [],
                        "classes": [],
                        "imports": []
                    })
                    
                    # Fallback text indexing for .md, .csv, Dockerfile, .txt, etc.
                    # Exclude huge files if necessary, but we'll chunk it as a whole file for now.
                    chunk_id = str(uuid.uuid4())[:8]
                    import hashlib
                    all_chunks.append({
                        "chunk_id": chunk_id,
                        "file_path": rel_path,
                        "chunk_type": "file",
                        "symbol_name": rel_path.split("/")[-1],
                        "start_line": 1,
                        "end_line": len(content.splitlines()),
                        "content": content,
                        "content_hash": hashlib.md5(content.encode('utf-8')).hexdigest()
                    })
            except UnicodeDecodeError:
                # Safely ignore binary files like .pkl, .png
                continue
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")

        # 3. Store Metadata & Keyword Index
        self.store.add_chunks(self.repo_id, all_chunks)
        self.store.upsert_repo(self.repo_id, self.repo_url.split('/')[-1], self.repo_url, self.branch)

        # 4. Generate & Store Embeddings
        if all_chunks:
            chunk_contents = [c['content'] for c in all_chunks]
            chunk_ids = [c['chunk_id'] for c in all_chunks]
            embeddings = self.embedder.generate_embeddings(chunk_contents)
            
            faiss_store = FAISSStore(self.repo_id)
            faiss_store.add_embeddings(chunk_ids, embeddings)

        # 5. Build Relationship Graph
        self.graph.build_from_parse_results(all_parse_results)
        self.graph.save()

        logger.info(f"Indexing complete for {self.repo_id}")
        return {
            "status": "READY",
            "repo_id": self.repo_id,
            "repo_path": repo_path,
            "files_indexed": len(all_parse_results),
            "chunks_created": len(all_chunks),
            "graph_nodes": len(self.graph.graph.nodes),
            "graph_edges": len(self.graph.graph.edges)
        }
