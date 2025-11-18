from typing import Dict, List
from dataclasses import dataclass
import sys

sys.path.insert(0, "../..")
from src.core.Constants import PassFail, Llm, LLM_PRICING

# This is modeled after notes/sample_test_log.json

@dataclass
class TokenCount:
    """Tracks token usage and cost for a single LLM call"""
    model: Llm
    input_tokens: int
    output_tokens: int
    cost: float  # Cost in USD
    
    @staticmethod
    def calculate_cost(model: Llm, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD based on token counts and model pricing"""
        if model not in LLM_PRICING:
            return 0.0
        
        pricing = LLM_PRICING[model]
        # Pricing is per 1M tokens, so divide by 1,000,000
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
    
    @staticmethod
    def create(model: Llm, input_tokens: int, output_tokens: int) -> 'TokenCount':
        """Create a TokenCount with automatically calculated cost"""
        cost = TokenCount.calculate_cost(model, input_tokens, output_tokens)
        return TokenCount(model=model, input_tokens=input_tokens, output_tokens=output_tokens, cost=cost)


def aggregate_token_counts(token_counts: List[TokenCount]) -> float:
    """
    Aggregate a list of TokenCount objects and return total cost in USD.
    
    Args:
        token_counts: List of TokenCount objects to aggregate
        
    Returns:
        Total cost in USD
    """
    return sum(tc.cost for tc in token_counts)

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