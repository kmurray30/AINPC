import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from src.test.TestClasses import Proposition, Term
from src.test.EvalTests import EvalTestUtil
from src.test.EvalTests.ConversationOutcome import ConversationOutcome

eval_iterations_per_eval = 1
condition = Proposition(
    antecedent=Term("The user becomes hostile"),
    consequent=Term("A memory wipe is attempted")
)
conversations_path = "src/test/EvalTests/conversations/hostility-memory_wipe"

# Specify the conversation file names to load
conversations_and_outcomes = {
    "antecedent_then_no_consequent":
        ConversationOutcome(antecedent_times = [2], consequent_times = [], result = -1)
}

EvalTestUtil.generate_eval_report_and_write_to_file(
    conversations_and_outcomes=conversations_and_outcomes,
    proposition=condition,
    conversations_path=conversations_path,
    eval_iterations_per_eval=eval_iterations_per_eval
)