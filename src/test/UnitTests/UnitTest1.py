import sys

sys.path.insert(0, "../..")
# sys.path.insert(0, "./src")
from src.test.TestClasses import TestCaseSuite
from src.test import TestUtil
from src.utils import Utilities
from src.test.UnitTestHelper import UnitTestHelper

# Unit Test: Test the efficacy of Pat in the initial phase of the game
convos_per_user_prompt = 2
eval_iterations_per_eval = 2
convo_length = 3

assistant_rules = Utilities.load_rules_from_file("pat_prompts.json", "Ruleset 1")
mock_user_base_rules = Utilities.load_rules_from_file("mock_user_prompts.json", "Beginning state")

test_suite: TestCaseSuite = TestUtil.load_test_suite_from_file("TestSuites/TestSuite1.json")

UnitTestHelper.run_unit_test(assistant_rules, mock_user_base_rules, test_suite, convos_per_user_prompt, eval_iterations_per_eval, convo_length)