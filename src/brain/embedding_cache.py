import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from threading import RLock


class EmbeddingCache:
    """
    Simple JSON-backed cache mapping raw text -> embedding list[float].

    - Loads existing cache file on initialization if present.
    - In-memory updates via add/check methods.
    - Persist to disk explicitly by calling save() (e.g., from NPC.maintain()).
    - Creates the file and parent directory automatically if missing on save().
    - File format: JSON object { text: embedding_list }.
      For backward-compatibility, will accept a JSON list of {"text", "embedding"} and convert in-memory to a dict.
    """

    def __init__(self, cache_file: Optional[Path] = None) -> None:
        self._lock = RLock()
        self._cache: Dict[str, List[float]] = {}
        # Default location inside the brain module directory
        default_path = Path(__file__).resolve().parent / "embedding_cache.json"
        self._cache_file = cache_file or default_path
        self._load_if_exists()

    def _load_if_exists(self) -> None:
        with self._lock:
            if not self._cache_file.exists():
                self._cache = {}
                return
            try:
                text = self._cache_file.read_text(encoding="utf-8")
                data = json.loads(text) if text else {}
                if isinstance(data, dict):
                    # Expected format
                    self._cache = {str(k): list(v) for k, v in data.items()}
                elif isinstance(data, list):
                    # Legacy/alternate format
                    converted: Dict[str, List[float]] = {}
                    for item in data:
                        if isinstance(item, dict) and "text" in item and "embedding" in item:
                            converted[str(item["text"])] = list(item["embedding"])  # type: ignore[arg-type]
                    self._cache = converted
                else:
                    # Unknown format, start fresh
                    self._cache = {}
            except Exception:
                # On any read/parse error, start with an empty cache
                self._cache = {}

    def get(self, text: str) -> Optional[List[float]]:
        with self._lock:
            return self._cache.get(text)

    def contains(self, text: str) -> bool:
        with self._lock:
            return text in self._cache

    def add(self, text: str, embedding: List[float]) -> None:
        with self._lock:
            self._cache[text] = list(embedding)

    def save(self) -> None:
        with self._lock:
            # Ensure directory exists
            os.makedirs(self._cache_file.parent, exist_ok=True)
            # Write atomically using a temp file and replace
            temp_path = self._cache_file.with_suffix(self._cache_file.suffix + ".tmp")
            data = json.dumps(self._cache, ensure_ascii=False)
            temp_path.write_text(data, encoding="utf-8")
            os.replace(temp_path, self._cache_file)


