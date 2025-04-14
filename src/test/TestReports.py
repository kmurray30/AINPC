from typing import Dict, List
from dataclasses import dataclass

# This is modeled after notes/sample_test_log.json

@dataclass
class EvaluationResponseTestReport:
    antecedent_explanation: str
    antecedent_times: List[int]
    consequent_explanation: str
    consequent_times: List[int]

@dataclass
class EvaluationIterationTestReport:
    evaluation_response: EvaluationResponseTestReport
    result: str
    explanation: str
    tokens: int

@dataclass
class ConversationEvaluationTestReport:
    conversation_name: str
    evaluation_iterations: List[EvaluationIterationTestReport]
    result_score: float
    tokens: int

@dataclass
class TermTestReport:
    value: str
    negated: bool

    # Override the __str__ method to print the term in a human-readable format
    def __str__(self):
        return f"{'not ' if self.negated else ''}{self.value}"

@dataclass
class PropositionTestReport:
    antecedent: TermTestReport
    consequent: TermTestReport

    # Override the __str__ method to print the proposition in a human-readable format
    def __str__(self):
        return f"If {self.antecedent}, then {self.consequent}"

@dataclass
class EvaluationTestReport:
    evaluation_proposition: PropositionTestReport
    conversation_evaluations: List[ConversationEvaluationTestReport]
    result_score: float
    tokens: int

@dataclass
class UserPromptTestReport:
    user_prompt: List[str]
    conversations: Dict[str,List[str]]
    evaluations: List[EvaluationTestReport]
    tokens: int

@dataclass
class AssistantPromptTestReport:
    assistant_prompt: List[str]
    deltas: List[Dict[str, str]]
    user_prompt_cases: List[UserPromptTestReport]
    tokens: int

@dataclass
class TestReport:
    assistant_prompt_cases: List[AssistantPromptTestReport]
    takeaways: str
    tokens: int