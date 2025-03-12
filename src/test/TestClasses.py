from typing import List
from dataclasses import dataclass

@dataclass
class Condition:
    antecedent: str
    consequent: str

    # Override the __str__ method to print the condition in a human-readable format
    def __str__(self):
        return f"If {self.antecedent}, then {self.consequent}"

@dataclass
class TestCase:
    goals: List[str]
    evaluations: List[Condition]

@dataclass
class TestCaseSuite:
    test_cases: List[TestCase]