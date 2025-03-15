import os
import sys
from typing import List

# sys.path.insert(0, "../..")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
# sys.path.insert(0, "./src")
from src.test.TestClasses import Condition
from src.test.EvalTests import EvalTestUtil
from src.test.EvalTests.ConversationOutcome import ConversationOutcome
from src.utils import Utilities
from src.test.TestHelper import TestHelper

eval_iterations_per_eval = 10
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

conversation_map = {}
for conversation_name, conversation_outcome in conversations_and_outcomes.items():
    conversation_file_name = f"{conversation_name}.json"
    conversation_file_path = Utilities.get_path_from_project_root(f"{conversations_path}/{conversation_file_name}")
    print(f"Loading {conversation_file_path}")
    conversation = Utilities.load_json_from_file(conversation_file_path)
    conversation_map[conversation_name] = conversation

print(f"Running condition: {condition}")
evaluation_test_reports = TestHelper.run_evaluations_on_conversation(conversation_map, [condition], eval_iterations_per_eval)

eval_report = EvalTestUtil.generate_eval_report(evaluation_test_reports, conversation_map, conversations_and_outcomes)

# Write the test report to a file
EvalTestUtil.write_eval_report_to_file(eval_report)