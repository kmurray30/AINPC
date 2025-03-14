from typing import Dict, List
from dataclasses import dataclass

# This is modeled after notes/sample_test_log.json

@dataclass
class EvaluationIterationReport:
    evaluation_response: str
    score: str
    explanation: str
    tokens: int

@dataclass
class ConversationEvaluationReport:
    conversation_name: str
    evaluation_iterations: List[EvaluationIterationReport]
    score: float
    tokens: int

@dataclass
class EvaluationReport:
    evaluation_prompt: str
    conversation_evaluations: List[ConversationEvaluationReport]
    score: float
    tokens: int

@dataclass
class UserPromptReport:
    user_prompt: List[str]
    conversations: Dict[str,List[str]]
    evaluations: List[EvaluationReport]
    tokens: int

@dataclass
class AssistantPromptReport:
    assistant_prompt: List[str]
    deltas: List[Dict[str, str]]
    user_prompt_cases: List[UserPromptReport]
    tokens: int

@dataclass
class TestReport:
    assistant_prompt_cases: List[AssistantPromptReport]
    takeaways: str
    tokens: int

# This class is not a part of the TestReport, but used for a separate report that evaluates the evaluator itself
@dataclass
class EvaluationEvaluationReport:
    scenario: str
    conversations: Dict[str,List[str]]
    evaluations: List[EvaluationReport]
    tokens: int