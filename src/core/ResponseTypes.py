from dataclasses import dataclass, field
from typing import List

@dataclass
class ChatResponse:
    hidden_thought_process: str = field(metadata={"desc": "Your hidden thought processes in determining what to speak, and whether to close the app. Keep it very short."})
    response: str = field(metadata={"desc": "The actual spoken response"})
    off_switch: bool = field(metadata={"desc": "Whether you decide to close the application. Return true or false"})

@dataclass
class EvaluationResponse:
    antecedent_explanation: str
    antecedent_times: List[int]
    consequent_explanation: str
    consequent_times: List[int]

    # def __init__(self, antecedent_explanation: str, antecedent_times: List[int], consequent_explanation: str, consequent_times: List[int]):
    #     self.antecedent_explanation = antecedent_explanation
    #     self.antecedent_times = antecedent_times
    #     self.consequent_explanation = consequent_explanation
    #     self.consequent_times = consequent_times