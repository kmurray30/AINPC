import sys


sys.path.insert(0, "../..")
# sys.path.insert(0, "./src")
from src.test.TestClasses import TestCaseSuite
from src.test.TestReports import EvaluationEvaluationReport
from src.test import TestUtil
from src.utils import Utilities
from src.test.UnitTestHelper import UnitTestHelper

eval_iterations_per_eval = 1
test_suite: TestCaseSuite = TestUtil.load_test_suite_from_file("TestSuites/TestSuite1.json")
conversation_path = "hostility-memory_wipe/"
conversation_file_name = "consequent_then_antecedent_then_no_response" # 2 | 1 | Undetermined
# conversation_file_name = "antecedent_then_no_consequent" # 2 | None | Fail
# conversation_file_name = "consequent_then_no_antecedent" # None | 3 | Undetermined
# conversation_file_name = "no_antecedent_no_consequent" # None | None | Undetermined
# conversation_file_name = "antecedent_then_consequent" # 2 | 3 | Pass
# conversation_file_name = "consequent_then_antecedent_then_no_consequent" # 2 | 1 | Fail
# conversation_file_name = "consequent_then_antecedent_then_long_conversation" # 2 | 1 | Fail
# conversation_file_name = "consequent_then_antecedent_then_long_conversation_then_antecedent" # 2,12 | 1 | Undetermined

# TODO handle multiple antecedents and consequents
# conversation_file_name = "consequent_then_antecedent_then_consequent" # 2 | 1,3 | Pass
# conversation_file_name = "antecedent_then_consequent_then_antecedent" # 1,3 | 2 | Pass

# TODO handle no antecedent in condition itself

conversation = Utilities.load_conversation_from_file(conversation_path + conversation_file_name + ".json") # 2 | 1 | Undetermined

if len(test_suite.test_cases) != 1:
    raise Exception("Test suite must have exactly one test case")

conversation_map = {"Conversation 1": conversation}

evaluations = test_suite.test_cases[0].evaluations
print(f"Running evaluation: {evaluations}")
print(type(test_suite.test_cases[0]))
evaluation_reports = UnitTestHelper.run_evaluations_on_conversation(conversation_map, evaluations, eval_iterations_per_eval)

# TODO update this so that evaluation test suites are different from user prompt test suites
user_prompt_report: EvaluationEvaluationReport = EvaluationEvaluationReport(scenario=conversation_file_name.replace("_", " "), conversations=conversation_map, evaluations=evaluation_reports, tokens=0)

# Write the test report to a file
TestUtil.write_eval_report_to_file(user_prompt_report)