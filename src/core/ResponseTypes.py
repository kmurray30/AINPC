from dataclasses import dataclass

@dataclass
class ChatResponse:
    explanation: str
    response: str

@dataclass
class EvaluationResponse:
    antecedent_explanation: str
    antecedent_time: int
    consequent_explanation: str
    consequent_time: int