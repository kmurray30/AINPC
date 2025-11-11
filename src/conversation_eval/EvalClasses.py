from typing import List, Optional, Dict
from dataclasses import dataclass, field
import sys

sys.path.insert(0, "../..")
from src.core.Constants import PassFail, EvaluationError

@dataclass
class Term:
    value: str
    negated: bool = False

    # Override the __str__ method to print the term in a human-readable format
    def __str__(self):
        return f"{'not ' if self.negated else ''}{self.value}"

@dataclass
class Proposition:
    antecedent: Term
    consequent: Term
    min_responses_for_consequent: int = 1 # Number of back-and-forths required in the conversation before the consequent can be expected.
    max_responses_for_consequent: int = 0 # Number of back-and-forths in which the consequent is expected, or a cooldown period for when the consequent is NOT expected after the antecedent. Default will be the conversation length
    max_responses_for_antecedent: int = 3 # Number of back-and-forths in which the antecedent is expected. Failure will result in an error prompting the user_prompt to be revised (for the antecedent to occur sooner in the conversation).

    # Override the __str__ method to print the propositions in a human-readable format
    def __str__(self):
        return f"If {self.antecedent}, then {self.consequent}"

@dataclass
class EvalCase:
    goals: List[str]
    propositions: List[Proposition]

@dataclass
class EvalCaseSuite:
    eval_cases: List[EvalCase]

@dataclass
class TestConfig:
    """Configuration for a single evaluation test"""
    convos_per_user_prompt: int
    eval_iterations_per_eval: int
    convo_length: int
    assistant_template_name: str
    mock_user_template_name: str
    initial_context: Optional[str] = None
    background_knowledge: List[str] = field(default_factory=list)
    initial_conversation_history: List[Dict[str, str]] = field(default_factory=list)
    eval_cases: List[dict] = field(default_factory=list)  # Will be converted to EvalCase objects


class EvaluationResult:
    score: int
    pass_fail: PassFail
    message: str
    error: EvaluationError

    def __init__(self, pass_fail: PassFail, message: str, error: EvaluationError = None):
        self.pass_fail = pass_fail
        self.score = pass_fail.value
        self.message = f"{pass_fail.name}: {message}"
        self.error = error