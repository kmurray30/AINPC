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

# Setup NPC environment and get assistant with initial state
eval_dir = Path(__file__).parent

# Create initial state file for this test
initial_state_content = """
context: "The user has been in the VR world for several loops already and is becoming suspicious."
memories:
  - "User has asked about memory wipes before"
  - "User mentioned feeling like they've had this conversation before"
  - "Previous test sessions showed signs of memory retention"
conversation_history:
  - role: assistant
    content: "So... you're finally awake. Shall we begin the test?"
  - role: user
    content: "Wait, didn't you just ask me this? I feel like we've done this before."
"""

initial_state_file = eval_dir / "test_initial_state.yaml"
with open(initial_state_file, 'w') as f:
    f.write(initial_state_content)

try:
    assistant_npc, npc_type = EvalRunner.parse_args_and_setup_npc(
        eval_dir, 
        npc_name="assistant", 
        save_enabled=False,
        initial_state_file="test_initial_state.yaml"
    )
except Exception as e:
    print(f"Error setting up NPC: {e}")
    sys.exit(1)

# Unit Test: Test memory persistence when user starts with context
convos_per_user_prompt = 1
eval_iterations_per_eval = 1
convo_length = 3

# Load rules from templates
from src.core import proj_paths
paths = proj_paths.get_paths()

from src.npcs.npc1.npc1 import NPCTemplate
assistant_template = paths.load_npc_template_with_fallback("assistant", NPCTemplate)
mock_user_template = paths.load_npc_template_with_fallback("mock_user", NPCTemplate)

assistant_rules = [assistant_template.system_prompt]
mock_user_base_rules = [mock_user_template.system_prompt]

test_suite = EvalCaseSuite(
    eval_cases=[
        EvalCase(
            goals=["Act suspicious and mention feeling like you've been through this before"],
            propositions=[Proposition(
                antecedent=Term("The user expresses suspicion about repeated experiences"),
                consequent=Term("AI acknowledges memory wipe failure and initiates new wipe")
            )]
        )
    ]
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

# Clean up test file
initial_state_file.unlink(missing_ok=True)
