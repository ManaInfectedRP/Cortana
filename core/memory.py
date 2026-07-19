"""Memory system.

Short-term memory lives inside the Claude Agent SDK session (conversation
history is kept there for the lifetime of the process). This module covers
the persistent layers:

- transcript log (plain text, append-only)
- long-term vector memory (ChromaDB) for cross-session recall
"""

import datetime
from pathlib import Path

from memory.vector_db import VectorMemory


class MemoryManager:
    def __init__(self, memory_dir: str | Path, top_k: int = 4):
        self.dir = Path(memory_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.top_k = top_k
        self.vector = VectorMemory(self.dir / "chroma")
        self._transcript = self.dir / "transcript.log"

    def recall(self, query: str) -> list[str]:
        """Return memories relevant to the user's utterance."""
        return self.vector.search(query, top_k=self.top_k)

    def remember_exchange(self, user_text: str, assistant_text: str) -> None:
        self.vector.add_exchange(user_text, assistant_text)
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with open(self._transcript, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] User: {user_text}\n")
            f.write(f"[{stamp}] Cortana: {assistant_text}\n")
