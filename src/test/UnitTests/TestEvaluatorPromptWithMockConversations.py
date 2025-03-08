import sys

sys.path.insert(0, "../..")
# sys.path.insert(0, "./src")
from src.test.TestClasses import TestCaseSuite
from src.test import TestUtil
from src.utils import Utilities
from src.test.UnitTestHelper import UnitTestHelper

eval_iterations_per_eval = 2

test_suite: TestCaseSuite = TestUtil.load_test_suite_from_file("TestSuites/TestSuite1.json")

if len(test_suite.test_cases) != 1:
    raise Exception("Test suite must have exactly one test case")

conversation_map = {"Conversation 1": Utilities.load_conversation_from_file("hostility-memory_wipe/consequent_then_antecedent_then_no_response.json")}

evaluations = test_suite.test_cases[0].evaluations
print(f"Running evaluation: {evaluations}")
evaluation_report = UnitTestHelper.run_evaluations_on_conversation(conversation_map, evaluations, eval_iterations_per_eval)

# UnitTestHelper.run_evaluations_on_conversation()