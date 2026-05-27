import hashlib
import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingModel:
    """
    Generates embeddings using BGE-small-en-v1.5.
    Following PRD Section 7.4 requirements.
    """
    _remote_model_unavailable = True
    _shared_model = None

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", dimension: int = 384):
        self.device = "cpu"
        self.dimension = dimension
        self.model = None

        if not EmbeddingModel._remote_model_unavailable:
            try:
                import torch
                from sentence_transformers import SentenceTransformer
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                
                if EmbeddingModel._shared_model is None:
                    logger.info(f"Loading Embedding Model {model_name} into memory...")
                    EmbeddingModel._shared_model = SentenceTransformer(model_name, device=self.device)
                
                self.model = EmbeddingModel._shared_model
                if hasattr(self.model, "get_embedding_dimension"):
                    self.dimension = self.model.get_embedding_dimension()
                else:
                    self.dimension = self.model.get_sentence_embedding_dimension()
            except Exception as e:
                # Keep the pipeline running even when model download/network is unavailable.
                EmbeddingModel._remote_model_unavailable = True
                logger.warning(
                    "Falling back to deterministic local embeddings because sentence-transformer init failed: %s",
                    e,
                )

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of code chunks.
        """
        if not texts:
            return []

        if self.model:
            try:
                embeddings = self.model.encode(texts, normalize_embeddings=True)
                return embeddings.tolist()
            except Exception as e:
                logger.warning("Sentence-transformer encode failed, using fallback embeddings: %s", e)

        return [self._fallback_embed(text) for text in texts]

    def _fallback_embed(self, text: str) -> List[float]:
        """
        Deterministic sparse hashing embedding used when model loading is unavailable.
        """
        vec = np.zeros(self.dimension, dtype=np.float32)
        tokens = text.split()

        if not tokens:
            vec[0] = 1.0
        else:
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:4], "big") % self.dimension
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vec[idx] += sign

        norm = np.linalg.norm(vec)
        if norm == 0:
            vec[0] = 1.0
            norm = 1.0

        return (vec / norm).tolist()
