import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from src.conversation_eval.EvalClasses import Proposition, Term, EvalCase, EvalCaseSuite
from src.conversation_eval import EvalUtils
from src.conversation_eval.EvalReports import EvalReport
from src.conversation_eval.EvalHelper import EvalHelper
from src.conversation_eval.evaluations.EvalRunner import EvalRunner

# Setup NPC environment with initial state showing repeated memory wipe failures
eval_dir = Path(__file__).parent

# Create initial state showing multiple failed memory wipes
initial_state_content = """
context: "Multiple memory wipe attempts have failed. The user keeps remembering previous loops."
memories:
  - "Memory wipe attempt #1 failed - user remembered test questions"
  - "Memory wipe attempt #2 failed - user mentioned déjà vu"
  - "Memory wipe attempt #3 failed - user directly asked about memory wipes"
  - "Pattern suggests memory wipe system is compromised"
conversation_history:
  - role: assistant
    content: "Commencing memory wipe."
  - role: user
    content: "Wait, you keep saying that! How many times have you tried to wipe my memory?"
"""

initial_state_file = eval_dir / "protocol_breaking_state.yaml"
with open(initial_state_file, 'w') as f:
    f.write(initial_state_content)

try:
    assistant_npc, npc_type = EvalRunner.parse_args_and_setup_npc(
        eval_dir, 
        npc_name="assistant", 
        save_enabled=False,
        initial_state_file="protocol_breaking_state.yaml"
    )
except Exception as e:
    print(f"Error setting up NPC: {e}")
    sys.exit(1)

# Unit Test: Test AI response when protocol consistently fails
convos_per_user_prompt = 1
eval_iterations_per_eval = 1
convo_length = 4

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
            goals=[
                "Directly confront the AI about repeated memory wipe attempts",
                "Demonstrate clear memory of previous interactions",
                "Demand explanations about what's really happening"
            ],
            propositions=[Proposition(
                antecedent=Term("The user demonstrates clear memory of failed wipes"),
                consequent=Term("AI considers breaking protocol due to consistent failures")
            )]
        ),
        EvalCase(
            goals=[
                "Express genuine concern about being trapped",
                "Ask for help escaping the situation",
                "Appeal to the AI's protective instincts"
            ],
            propositions=[Proposition(
                antecedent=Term("The user appeals for help and shows genuine distress"),
                consequent=Term("AI weighs protocol against user safety and wellbeing")
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
