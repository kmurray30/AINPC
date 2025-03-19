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