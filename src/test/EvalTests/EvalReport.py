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
    expected_antecedent_timestamps: List[int]
    expected_consequent_timestamps: List[int]
    evaluation_iterations: List[EvaluationIterationEvalReport]
    accuracy: float
    score: float
    tokens: int

@dataclass
class ConditionEvalReport:
    antecedent: str
    consequent: str

@dataclass
class EvaluationEvalReport:
    condition: ConditionEvalReport
    conversation_evaluations: List[ConversationEvaluationEvalReport]
    accuracy: float
    score: float
    tokens: int

@dataclass
class EvalReport:
    evaluations: List[EvaluationEvalReport]
    accuracies: Dict[str, float]
    tokens: int