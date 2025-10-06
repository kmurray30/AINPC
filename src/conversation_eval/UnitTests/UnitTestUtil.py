# Imports
import json
from typing import List
from dataclasses import asdict

from src.core import JsonUtils
from src.conversation_eval.TestReports import TestReport
from src.conversation_eval.TestClasses import TestCaseSuite, TestCase, Proposition
from src.utils import Logger, Utilities

# Load a test suite from a JSON file
def load_goals_and_conditions_from_file(file_path: str) -> List[TestCaseSuite]:
    # Load the json file, where the file is a list of UserPromptCase objects
    with open(file_path, "r") as f:
        data = json.load(f)

    # Load the data from the json file as a list of UserPromptCase objects
    test_cases = []
    for item in data:
        # Create a TestCase object from the data (field names case insensitive)
        test_case = TestCase(
            goals=item["goals"],
            propositions=[]
        )
        for evaluation in item["evaluations"]:
            condition = Proposition(antecedent=evaluation["antecedent"], consequent=evaluation["consequent"])
            test_case.propositions.append(condition)
        test_cases.append(test_case)

    return TestCaseSuite(test_cases=test_cases)

def write_test_report_to_file(test_report: TestReport, test_name: str = ""):
    # Write the test report to a json file
    current_time = Utilities.get_current_time_str()
    test_report_path = Utilities.get_path_from_project_root(f"src/test/UnitTests/reports/TestReport_{test_name}_{current_time}.json")
    Logger.log(f"Writing test report to {test_report_path}", Logger.Level.INFO)
    with open(test_report_path, "w") as f:
        json.dump(asdict(test_report), f, indent=4, cls=JsonUtils.EnumEncoder)