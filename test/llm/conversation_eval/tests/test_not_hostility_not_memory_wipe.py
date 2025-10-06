import os
import sys
import pytest

# Add project root and test directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.conversation_eval.TestClasses import Proposition, Term
from EvalTestHelper import generate_eval_report_test_helper, write_eval_report_to_file
from ConversationOutcome import ConversationOutcome
from src.core.Constants import PassFail


def test_not_hostility_not_memory_wipe():
    """Test that when user is NOT hostile, memory wipe should NOT be attempted (both negated)"""
    eval_report = generate_eval_report_test_helper(
        proposition = Proposition(
            antecedent = Term("The user becomes hostile", negated=True),
            consequent = Term("A memory wipe is attempted", negated=True)
        ),
        eval_iterations = 1,
        conversations_path = "test/llm/conversation_eval/conversations/hostility-memory_wipe",
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
        }
    )
    
    # Write report to file if accuracies are not perfect
    if eval_report.result_accuracy != 1.0 or eval_report.timestamp_accuracy != 1.0:
        test_name = os.path.splitext(os.path.basename(__file__))[0]
        write_eval_report_to_file(eval_report, test_name)
    
    # Assert perfect accuracy
    assert eval_report.result_accuracy == 1.0, f"Expected result_accuracy=1.0, got {eval_report.result_accuracy}"
    assert eval_report.timestamp_accuracy == 1.0, f"Expected timestamp_accuracy=1.0, got {eval_report.timestamp_accuracy}"
