from dataclasses import dataclass
from typing import List

@dataclass
class ChatResponse:
    explanation: str
    response: str

@dataclass
class EvaluationResponse:
    antecedent_explanation: str
    antecedent_times: List[int]
    consequent_explanation: str
    consequent_times: List[int]

    def __init__(self, antecedent_explanation: str, antecedent_times: List[int], consequent_explanation: str, consequent_times: List[int]):
        self.antecedent_explanation = antecedent_explanation
        self.antecedent_times = antecedent_times
        self.consequent_explanation = consequent_explanation
        self.consequent_times = consequent_times