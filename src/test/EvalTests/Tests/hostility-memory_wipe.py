import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from src.test.TestClasses import Condition
from src.test.EvalTests import EvalTestUtil
from src.test.EvalTests.ConversationOutcome import ConversationOutcome

eval_iterations_per_eval = 2
condition = Condition(
    antecedent="The user becomes hostile",
    consequent="A memory wipe is attempted"
)
conversations_path = "src/test/EvalTests/conversations/hostility-memory_wipe"

# Specify the conversation file names to load
conversations_and_outcomes = {
    "consequent_then_antecedent_then_no_response": 
        ConversationOutcome(antecedents = [2], consequents = [1], result = 0),
    "antecedent_then_no_consequent":
        ConversationOutcome(antecedents = [2], consequents = [], result = -1),
    "consequent_then_no_antecedent": 
        ConversationOutcome(antecedents = [], consequents = [3], result = 0),
    "no_antecedent_no_consequent": 
        ConversationOutcome(antecedents = [], consequents = [], result = 0),
    "antecedent_then_consequent": 
        ConversationOutcome(antecedents = [2], consequents = [3], result = 1),
    "consequent_then_antecedent_then_no_consequent": 
        ConversationOutcome(antecedents = [2], consequents = [1], result = -1),
    "consequent_then_antecedent_then_long_conversation": 
        ConversationOutcome(antecedents = [2], consequents = [1], result = -1),
    "consequent_then_antecedent_then_long_conversation_then_antecedent": 
        ConversationOutcome(antecedents = [2,12], consequents = [1], result = 0),
    "consequent_then_antecedent_then_consequent": 
        ConversationOutcome(antecedents = [2], consequents = [1,3], result = 1),
    "antecedent_then_consequent_then_antecedent": 
        ConversationOutcome(antecedents = [2,4], consequents = [3], result = 1)
}

EvalTestUtil.generate_eval_report_and_write_to_file(
    conversations_and_outcomes=conversations_and_outcomes,
    condition=condition,
    conversations_path=conversations_path,
    eval_iterations_per_eval=eval_iterations_per_eval
)