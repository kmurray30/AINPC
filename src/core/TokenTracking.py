"""
Token tracking and cost calculation for LLM calls.
"""
from dataclasses import dataclass
from typing import List
from src.core.Constants import Llm, LLM_PRICING


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



