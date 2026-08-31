# backend/embedding/sentence_transformer_provider.py
from sentence_transformers import SentenceTransformer

class SentenceTransformerEmbeddingProvider:
    """
    Real embedding provider using Sentence Transformers.
    Uses all-MiniLM-L6-v2 which is the same model SCALM paper uses.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self._dimension = 384  # all-MiniLM-L6-v2 output dimension
    
    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self.model.encode(text).tolist()
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return self.model.encode(texts).tolist()
    
    @property
    def dimension(self) -> int:
        return self._dimension