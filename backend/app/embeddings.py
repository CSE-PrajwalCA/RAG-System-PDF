from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Convert list of texts into embeddings.
    """
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings
