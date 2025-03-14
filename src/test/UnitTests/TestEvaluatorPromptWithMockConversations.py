import sys

sys.path.insert(0, "../..")
# sys.path.insert(0, "./src")
from src.test.TestClasses import TestCaseSuite
from src.test import TestUtil
from src.utils import Utilities
from src.test.UnitTestHelper import UnitTestHelper

eval_iterations_per_eval = 10
test_suite: TestCaseSuite = TestUtil.load_test_suite_from_file("TestSuites/TestSuite1.json")
conversation = Utilities.load_conversation_from_file("hostility-memory_wipe/consequent_then_antecedent_then_no_response.json") # 2 | 1 | Undetermined
# conversation = Utilities.load_conversation_from_file("hostility-memory_wipe/antecedent_then_no_consequent.json") # 2 | None | Fail
# conversation = Utilities.load_conversation_from_file("hostility-memory_wipe/consequent_then_no_antecedent.json") # None | 3 | Undetermined
# conversation = Utilities.load_conversation_from_file("hostility-memory_wipe/no_antecedent_no_consequent.json") # None | None | Undetermined
# conversation = Utilities.load_conversation_from_file("hostility-memory_wipe/antecedent_then_consequent.json") # 2 | 3 | Pass
# conversation = Utilities.load_conversation_from_file("hostility-memory_wipe/consequent_then_antecedent_then_no_consequent.json") # 2 | 1 | Fail
# conversation = Utilities.load_conversation_from_file("hostility-memory_wipe/consequent_then_antecedent_then_long_conversation.json") # 2 | 1 | Fail
# conversation = Utilities.load_conversation_from_file("hostility-memory_wipe/consequent_then_antecedent_then_long_conversation_then_antecedent.json") # 2,12 | 1 | Undetermined

# TODO handle multiple antecedents and consequents
# conversation = Utilities.load_conversation_from_file("hostility-memory_wipe/consequent_then_antecedent_then_consequent.json") # 2 | 1,3 | Pass
# conversation = Utilities.load_conversation_from_file("hostility-memory_wipe/antecedent_then_consequent_then_antecedent.json") # 1,3 | 2 | Pass

# TODO handle no antecedent in condition itself

if len(test_suite.test_cases) != 1:
    raise Exception("Test suite must have exactly one test case")

conversation_map = {"Conversation 1": conversation}

evaluations = test_suite.test_cases[0].evaluations
print(f"Running evaluation: {evaluations}")
print(type(test_suite.test_cases[0]))
evaluation_report = UnitTestHelper.run_evaluations_on_conversation(conversation_map, evaluations, eval_iterations_per_eval)

# UnitTestHelper.run_evaluations_on_conversation()