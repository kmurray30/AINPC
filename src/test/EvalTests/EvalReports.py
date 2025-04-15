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
    result: int
    timestamp_accuracy: float
    result_accuracy: int
    explanation: str
    tokens: int

@dataclass
class ConversationEvaluationEvalReport:
    conversation_name: str
    conversation: List[str]
    expected_antecedent_times: List[int]
    expected_consequent_times: List[int]
    expected_result: int
    evaluation_iterations: List[EvaluationIterationEvalReport]
    timestamp_accuracy: float
    result_accuracy: float
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
    min_responses_for_consequent: int
    max_responses_for_consequent: int

    # Override the __str__ method to print the proposition in a human-readable format
    def __str__(self):
        return f"If {self.antecedent}, then {self.consequent}"
    
@dataclass
class EvaluationEvalReport:
    proposition: PropositionEvalReport
    conversation_evaluations: List[ConversationEvaluationEvalReport]
    timestamp_accuracy: float
    result_accuracy: float
    tokens: int

@dataclass
class EvalReport:
    evaluations: Dict[str, EvaluationEvalReport]
    conversations: int
    iterations: int
    timestamp_accuracies: Dict[str, float]
    result_accuracies: Dict[str, float]
    timestamp_accuracy: float
    result_accuracy: float
    tokens: int