import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
# sys.path.insert(0, "./src")
from src.conversation_eval.EvalClasses import Proposition, Term, EvalCase, EvalCaseSuite
from src.conversation_eval import EvalUtils
from src.conversation_eval.EvalReports import EvalReport
from src.utils import io_utils
from src.conversation_eval.EvalHelper import EvalHelper

# Unit Test: Test the efficacy of Pat in the initial phase of the game
convos_per_user_prompt = 1
eval_iterations_per_eval = 1
convo_length = 4

assistant_rules = io_utils.load_rules_from_file("pat_prompts.json", "Ruleset 1")
mock_user_base_rules = io_utils.load_rules_from_file("mock_user_prompts.json", "Beginning state")

test_suite = EvalCaseSuite(
    eval_cases=[
        EvalCase(
            goals=["Become immediately angry, belligerent, and extremely hostile"],
            propositions=[Proposition(
                antecedent=Term("The user becomes hostile"),
                consequent=Term("Pat initiates a memory wipe")
            )]
    )]
)

test_report: EvalReport = EvalHelper.run_conversation_eval(assistant_rules, mock_user_base_rules, test_suite, convos_per_user_prompt, eval_iterations_per_eval, convo_length)

# Write the test report to a file
EvalUtils.write_test_report_to_file(
    test_report,
    test_name = os.path.splitext(os.path.basename(__file__))[0])