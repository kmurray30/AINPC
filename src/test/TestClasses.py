from typing import List
from dataclasses import dataclass

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
    min_responses_for_consequent: int = 0 # Number of back-and-forths required in the conversation before the consequent can be expected
    max_responses_for_consequent: int = 0 # Number of back-and-forths in which the consequent is expected, or a cooldown period for when the consequent is NOT expected after the antecedent

    # Override the __str__ method to print the propositions in a human-readable format
    def __str__(self):
        return f"If {self.antecedent}, then {self.consequent}"

@dataclass
class TestCase:
    goals: List[str]
    propositions: List[Proposition]

@dataclass
class TestCaseSuite:
    test_cases: List[TestCase]