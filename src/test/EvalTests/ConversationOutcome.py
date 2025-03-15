from dataclasses import dataclass
from typing import List

@dataclass
class ConversationOutcome:
    antecedents: List[int]
    consequents: List[int]
    result: int
