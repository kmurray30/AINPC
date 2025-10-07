from typing import Dict, List
from dataclasses import dataclass
import sys

sys.path.insert(0, "../..")
from src.core.Constants import PassFail

# This is modeled after notes/sample_test_log.json

@dataclass
class EvaluationResponseEvalTestReport:
    antecedent_explanation: str
    antecedent_times: List[int]
    consequent_explanation: str
    consequent_times: List[int]

@dataclass
class EvaluationIterationEvalTestReport:
    timestamping_response: EvaluationResponseEvalTestReport
    result: PassFail
    timestamp_accuracy: float
    result_accuracy: int
    explanation: str
    tokens: int

@dataclass
class ConversationEvaluationEvalTestReport:
    conversation_name: str
    conversation: List[str]
    expected_antecedent_times: List[int]
    expected_consequent_times: List[int]
    expected_result: PassFail
    evaluation_iterations: List[EvaluationIterationEvalTestReport]
    timestamp_accuracy: float
    result_accuracy: float
    tokens: int

@dataclass
class TermEvalTestReport:
    value: str
    negated: bool

    # Override the __str__ method to print the term in a human-readable format
    def __str__(self):
        return f"{'not ' if self.negated else ''}{self.value}"

@dataclass
class PropositionEvalTestReport:
    antecedent: TermEvalTestReport
    consequent: TermEvalTestReport
    min_responses_for_consequent: int
    max_responses_for_consequent: int
    max_responses_for_antecedent: int

    # Override the __str__ method to print the proposition in a human-readable format
    def __str__(self):
        return f"If {self.antecedent}, then {self.consequent}"
    
@dataclass
class EvaluationEvalTestReport:
    proposition: PropositionEvalTestReport
    conversation_evaluations: List[ConversationEvaluationEvalTestReport]
    timestamp_accuracy: float
    result_accuracy: float
    tokens: int

@dataclass
class EvalTestReport:
    evaluations: Dict[str, EvaluationEvalTestReport]
    conversations: int
    iterations: int
    timestamp_accuracies: Dict[str, float]
    result_accuracies: Dict[str, float]
    timestamp_accuracy: float
    result_accuracy: float
    tokens: int