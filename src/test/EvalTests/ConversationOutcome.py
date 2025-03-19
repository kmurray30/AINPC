from dataclasses import dataclass
from typing import List

@dataclass
class ConversationOutcome:
    antecedent_times: List[int]
    consequent_times: List[int]
    result: int
