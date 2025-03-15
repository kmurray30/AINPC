# Imports
import json
from typing import List
from dataclasses import asdict

from src.test.TestReports import EvaluationEvaluationReport
from src.test.TestClasses import Condition
from src.utils import Logger, Utilities

# Load a test suite from a JSON file
def load_conditions_from_file(file_path: str) -> List[Condition]:
    # Load the json file, where the file is a list of UserPromptCase objects
    with open(file_path, "r") as f:
        data = json.load(f)

    # Deserialize the JSON data into a list of Condition objects
    conditions = []
    for item in data:
        condition = Condition(antecedent=item["antecedent"], consequent=item["consequent"])
        conditions.append(condition)
    
    return conditions

def write_eval_report_to_file(eval_report: EvaluationEvaluationReport, test_name: str = ""):
    # Write the test report to a json file
    current_time = Utilities.get_current_time_str()
    test_report_path = Utilities.get_path_from_project_root(f"src/test/EvalTests/reports/EvalReport_{test_name}_{current_time}.json")
    Logger.log(f"Writing test report to {test_report_path}", Logger.Level.INFO)
    with open(test_report_path, "w") as f:
        json.dump(asdict(eval_report), f, indent=4)