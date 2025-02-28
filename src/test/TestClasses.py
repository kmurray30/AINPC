from typing import List
from dataclasses import dataclass

@dataclass
class TestCase:
    goals: List[str]
    evaluations: List[str]

@dataclass
class TestCaseSuite:
    test_cases: List[TestCase]