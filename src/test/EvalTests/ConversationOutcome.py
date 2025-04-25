from dataclasses import dataclass
from typing import List
import sys

sys.path.insert(0, "../..")
from src.core.Constants import PassFail

@dataclass
class ConversationOutcome:
    antecedent_times: List[int]
    consequent_times: List[int]
    expected_result: PassFail
