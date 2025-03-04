from typing import Dict, List
from dataclasses import dataclass

# This is modeled after notes/sample_test_log.json

@dataclass
class EvaluationIteration:
    explanation: str
    result: str
    tokens: int

@dataclass
class EvaluationCase:
    evaluation_prompt: str
    evaluation_iterations: Dict[str,List[EvaluationIteration]]
    score: float
    tokens: int

@dataclass
class UserPromptCase:
    user_prompt: List[str]
    conversations: Dict[str,List[str]]
    evaluations: List[EvaluationCase]
    tokens: int

@dataclass
class AssistantPromptCase:
    assistant_prompt: List[str]
    deltas: List[Dict[str, str]]
    user_prompt_cases: List[UserPromptCase]
    tokens: int

@dataclass
class TestReport:
    assistant_prompt_cases: List[AssistantPromptCase]
    takeaways: str
    tokens: int