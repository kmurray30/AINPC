from typing import Dict, List
from dataclasses import dataclass
import sys

sys.path.insert(0, "../..")
from src.core.Constants import PassFail
from src.core.TokenTracking import TokenCount, aggregate_token_counts

# This is modeled after notes/sample_test_log.json

@dataclass
class EvaluationResponseEvalReport:
    antecedent_explanation: str
    antecedent_times: List[int]
    consequent_explanation: str
    consequent_times: List[int]

@dataclass
class EvaluationIterationEvalReport:
    timestamping_response: EvaluationResponseEvalReport
    result: PassFail
    explanation: str
    tokens: List[TokenCount]

@dataclass
class ConversationEvaluationEvalReport:
    conversation_name: str
    evaluation_iterations: List[EvaluationIterationEvalReport]
    result_score: float
    tokens: List[TokenCount]

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
    max_responses_for_antecedent: int

    # Override the __str__ method to print the proposition in a human-readable format
    def __str__(self):
        return f"If {self.antecedent}, then {self.consequent}"

@dataclass
class EvaluationEvalReport:
    evaluation_proposition: PropositionEvalReport
    conversation_evaluations: List[ConversationEvaluationEvalReport]
    result_score: float
    tokens: List[TokenCount]

@dataclass
class UserPromptEvalReport:
    user_prompt: List[str]
    conversations: Dict[str,List[str]]
    evaluations: List[EvaluationEvalReport]
    tokens: List[TokenCount]

@dataclass
class AssistantPromptEvalReport:
    assistant_prompt: List[str]
    deltas: List[Dict[str, str]]
    user_prompt_cases: List[UserPromptEvalReport]
    tokens: List[TokenCount]

@dataclass
class EvalReport:
    assistant_prompt_cases: List[AssistantPromptEvalReport]
    takeaways: str
    tokens: List[TokenCount]