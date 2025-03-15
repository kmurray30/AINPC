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
    score: str
    explanation: str
    tokens: int

@dataclass
class ConversationEvaluationTestReport:
    conversation_name: str
    evaluation_iterations: List[EvaluationIterationTestReport]
    score: float
    tokens: int

@dataclass
class ConditionTestReport:
    antecedent: str
    consequent: str

@dataclass
class EvaluationTestReport:
    evaluation_condition: ConditionTestReport
    conversation_evaluations: List[ConversationEvaluationTestReport]
    score: float
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