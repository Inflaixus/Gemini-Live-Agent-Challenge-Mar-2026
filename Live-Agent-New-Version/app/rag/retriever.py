import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

def chunk_text(c: dict) -> str:
    return c.get("content", "") or ""

class Retriever:
    """
    Cosine similarity via normalized embeddings + FAISS inner product.
    """
    def __init__(self, chunks: list[dict], embed_model: str = "BAAI/bge-m3"):
        self.chunks = chunks
        self.model = SentenceTransformer(embed_model)

        texts = [chunk_text(c) for c in chunks]
        emb = self.model.encode(texts, normalize_embeddings=True).astype("float32")

        self.index = faiss.IndexFlatIP(emb.shape[1])
        self.index.add(emb)
        self.emb = emb

    def search(self, query: str, top_k: int = 6) -> list[tuple[float, dict]]:
        q = self.model.encode([query], normalize_embeddings=True).astype("float32")
        scores, idx = self.index.search(q, top_k)
        out: list[tuple[float, dict]] = []
        for s, i in zip(scores[0], idx[0]):
            if i == -1:
                continue
            out.append((float(s), self.chunks[i]))
        return out