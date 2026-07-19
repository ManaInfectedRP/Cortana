"""Long-term vector memory backed by ChromaDB.

Uses Chroma's built-in ONNX MiniLM embedding function, so no torch or
separate embedding model is required for memory.
"""

import time
import uuid
from pathlib import Path

import chromadb


class VectorMemory:
    def __init__(self, persist_dir: str | Path):
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection("conversations")

    def add_exchange(self, user_text: str, assistant_text: str) -> None:
        doc = f"User: {user_text}\nCortana: {assistant_text}"
        self._collection.add(
            ids=[str(uuid.uuid4())],
            documents=[doc],
            metadatas=[{"timestamp": time.time()}],
        )

    def search(self, query: str, top_k: int = 4) -> list[str]:
        if self._collection.count() == 0:
            return []
        res = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, self._collection.count()),
        )
        docs = res.get("documents") or [[]]
        distances = res.get("distances") or [[]]
        out = []
        for doc, dist in zip(docs[0], distances[0]):
            # skip results that are barely related
            if dist is None or dist < 1.4:
                out.append(doc)
        return out
