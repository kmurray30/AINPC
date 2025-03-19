from typing import Dict, List
from dataclasses import dataclass

# This is modeled after notes/sample_test_log.json

@dataclass
class EvaluationResponseEvalReport:
    antecedent_explanation: str
    antecedent_times: List[int]
    consequent_explanation: str
    consequent_times: List[int]

@dataclass
class EvaluationIterationEvalReport:
    evaluation_response: EvaluationResponseEvalReport
    accuracy: float
    score: int
    explanation: str
    tokens: int

@dataclass
class ConversationEvaluationEvalReport:
    conversation_name: str
    conversation: List[str]
    expected_antecedent_times: List[int]
    expected_consequent_times: List[int]
    evaluation_iterations: List[EvaluationIterationEvalReport]
    accuracy: float
    score: float
    tokens: int

@dataclass
class TermEvalReport:
    value: str
    negated: bool

    # Override the __str__ method to print the term in a human-readable format
    def __str__(self):
        return f"{'not ' if self.negated else ''}{self.value}"

@dataclass
class PropositionEvalReport:
    antecedent: TermEvalReport
    consequent: TermEvalReport

    # Override the __str__ method to print the proposition in a human-readable format
    def __str__(self):
        return f"If {self.antecedent}, then {self.consequent}"
    
@dataclass
class EvaluationEvalReport:
    proposition: PropositionEvalReport
    conversation_evaluations: List[ConversationEvaluationEvalReport]
    accuracy: float
    score: float
    tokens: int

@dataclass
class EvalReport:
    evaluations: Dict[str, EvaluationEvalReport]
    accuracies: Dict[str, float]
    tokens: int