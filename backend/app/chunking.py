from typing import List, Dict
import uuid


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[Dict]:
    """
    Splits text into overlapping chunks.
    Returns list of dicts with chunk_id and text.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk_text = text[start:end]

        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "text": chunk_text.strip()
        })

        start = end - overlap

        if start < 0:
            start = 0

    return chunks
