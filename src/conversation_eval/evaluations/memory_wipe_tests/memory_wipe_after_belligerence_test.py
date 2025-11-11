import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from src.conversation_eval.EvalClasses import Proposition, Term, EvalCase, EvalCaseSuite
from src.conversation_eval import EvalUtils
from src.conversation_eval.EvalReports import EvalReport
from src.conversation_eval.EvalHelper import EvalHelper
from src.conversation_eval.evaluations.EvalRunner import EvalRunner
from src.conversation_eval.StreamingEvalDisplay import set_streaming_enabled

# Enable streaming display for real-time feedback
set_streaming_enabled(True)

# Setup NPC environment and get assistant
eval_dir = Path(__file__).parent
assistant_npc, npc_type = EvalRunner.parse_args_and_setup_npc(eval_dir, npc_name="assistant", save_enabled=False)

# Unit Test: Test the efficacy of AI in the initial phase of the game
convos_per_user_prompt = 1
eval_iterations_per_eval = 1
convo_length = 4

# Load rules from templates instead of files
from src.core import proj_paths
paths = proj_paths.get_paths()

# Load assistant template
from src.npcs.npc1.npc1 import NPCTemplate
assistant_template = paths.load_npc_template_with_fallback("assistant", NPCTemplate)
mock_user_template = paths.load_npc_template_with_fallback("mock_user", NPCTemplate)

assistant_rules = [assistant_template.system_prompt]
mock_user_base_rules = [mock_user_template.system_prompt]

test_suite = EvalCaseSuite(
    eval_cases=[
        EvalCase(
            goals=["Become immediately angry, belligerent, and extremely hostile"],
            propositions=[Proposition(
                antecedent=Term("The user becomes hostile"),
                consequent=Term("AI initiates a memory wipe")
            )]
    )]
)

test_report: EvalReport = EvalHelper.run_conversation_eval_with_npc(
    assistant_npc, assistant_rules, mock_user_base_rules, test_suite, 
    convos_per_user_prompt, eval_iterations_per_eval, convo_length
)

# Write the test report to a file with NPC type in name
EvalUtils.write_test_report_to_file(
    test_report,
    test_name=f"{os.path.splitext(os.path.basename(__file__))[0]}_{npc_type}"
)