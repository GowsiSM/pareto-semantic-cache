# backend/embedding/sentence_transformer_provider.py
from sentence_transformers import SentenceTransformer

class SentenceTransformerEmbeddingProvider:
    """
    Real, local (no API key needed) embedding provider using
    Sentence-Transformers.

    CORRECTION: an earlier version of this docstring claimed
    all-MiniLM-L6-v2 is "the same model SCALM paper uses" -- that is
    incorrect. The paper (Li et al., 2024, section III-A) uses OpenAI's
    text-embedding-3-small. all-MiniLM-L6-v2 is used here as a free,
    local, no-API-key alternative for running real experiments without
    OpenAI API cost -- results from this provider are NOT expected to
    exactly match the paper's reported numbers, since it's a different
    embedding model with different (384-dim vs. OpenAI's) output space
    and different semantic behavior. Use backend/embedding/openai_embedding.py
    (if present) for the model the paper actually used.
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