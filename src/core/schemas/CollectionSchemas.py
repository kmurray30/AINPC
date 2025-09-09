from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Entity:
    key: str
    content: str
    tags: List[str]
    id: Optional[int] = None
    # embedding: Optional[List[float]] = None


