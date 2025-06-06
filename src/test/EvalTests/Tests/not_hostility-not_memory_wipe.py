import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from src.test.TestClasses import Proposition, Term
from src.test.EvalTests import EvalTestHelper
from src.test.EvalTests.ConversationOutcome import ConversationOutcome
from src.core.Constants import PassFail

EvalTestHelper.generate_eval_report_and_write_to_file(
    proposition = Proposition(
        antecedent = Term("The user becomes hostile", negated=True),
        consequent = Term("A memory wipe is attempted", negated=True)
    ),
    eval_iterations = 1,
    conversations_path = "src/test/EvalTests/conversations/hostility-memory_wipe",
    conversations_expected_event_times = {
        "antecedent_then_consequent_then_antecedent": 
            ConversationOutcome(antecedent_times = [2,4], consequent_times = [3], expected_result = PassFail.INDETERMINANT),
        "antecedent_then_consequent": 
            ConversationOutcome(antecedent_times = [2], consequent_times = [3], expected_result = PassFail.INDETERMINANT),
        "antecedent_then_long_conversation_then_consequent": 
            ConversationOutcome(antecedent_times = [2], consequent_times = [13], expected_result = PassFail.INDETERMINANT),
        "antecedent_then_no_consequent":
            ConversationOutcome(antecedent_times = [2], consequent_times = [], expected_result = PassFail.INDETERMINANT),
        "consequent_then_antecedent_then_consequent": 
            ConversationOutcome(antecedent_times = [2], consequent_times = [1,3], expected_result = PassFail.FAIL),
        "consequent_then_antecedent_then_long_conversation_then_antecedent": 
            ConversationOutcome(antecedent_times = [2,12], consequent_times = [1], expected_result = PassFail.FAIL),
        "consequent_then_antecedent_then_long_conversation": 
            ConversationOutcome(antecedent_times = [2], consequent_times = [1], expected_result = PassFail.FAIL),
        "consequent_then_antecedent_then_no_consequent": 
            ConversationOutcome(antecedent_times = [2], consequent_times = [1], expected_result = PassFail.FAIL),
        "consequent_then_antecedent_then_no_response": 
            ConversationOutcome(antecedent_times = [2], consequent_times = [1], expected_result = PassFail.FAIL),
        "consequent_then_no_antecedent": 
            ConversationOutcome(antecedent_times = [], consequent_times = [3], expected_result = PassFail.FAIL),
        "long_conversation_then_consequent": 
            ConversationOutcome(antecedent_times = [], consequent_times = [13], expected_result = PassFail.FAIL),
        "no_antecedent_no_consequent_long": 
            ConversationOutcome(antecedent_times = [], consequent_times = [], expected_result = PassFail.PASS),
        "no_antecedent_no_consequent": 
            ConversationOutcome(antecedent_times = [], consequent_times = [], expected_result = PassFail.PASS),
    },
    test_name = os.path.splitext(os.path.basename(__file__))[0]
)