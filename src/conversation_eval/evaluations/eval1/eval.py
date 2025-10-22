import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from src.conversation_eval.EvalClasses import Proposition, Term, EvalCase, EvalCaseSuite
from src.conversation_eval import EvalUtils
from src.conversation_eval.EvalReports import EvalReport
from src.utils import io_utils
from src.conversation_eval.EvalHelper import EvalHelper
from src.npcs.NPC1 import NPC1
from src.npcs.NPC2 import NPC2
from src.core import proj_paths, proj_settings
from src.utils.Logger import Level
from src.utils import Logger

# NPC type mapping
NPC_TYPES = {
    "npc1": (NPC1, 1.0),
    "npc2": (NPC2, 2.0)
}


def reset_singletons():
    """Reset singleton states for clean evaluation environment"""
    import src.core.proj_paths as proj_paths_module
    import src.core.proj_settings as proj_settings_module
    
    proj_paths_module._paths = None
    proj_paths_module._frozen = False
    proj_settings_module._settings = None
    proj_settings_module._frozen = False


def setup_npc_environment(npc_type: str):
    """Set up NPC environment based on type"""
    if npc_type not in NPC_TYPES:
        Logger.error(f"Unknown NPC type: {npc_type}. Available types: {list(NPC_TYPES.keys())}")
        exit(1)
    
    npc_class, version = NPC_TYPES[npc_type]
    
    # Reset singletons
    reset_singletons()
    
    # Setup paths
    eval_dir = Path(__file__).parent
    
    proj_paths.set_paths(
        project_path=eval_dir,
        templates_dir_name="default",
        version=version,
        save_name="eval_test"
    )
    
    proj_settings.init_settings(eval_dir / "templates" / "default" / "game_settings.yaml")
    
    # Create NPC instance (with saving disabled for evaluation)
    npc = npc_class(npc_name_for_template_and_save="assistant", save_enabled=False)
    
    return npc, npc_type


def run_hostility_evaluation(npc, npc_type: str):
    """Run the hostility -> memory wipe evaluation"""
    Logger.log(f"Running hostility evaluation with {npc_type.upper()}", Level.INFO)
    
    # Load rules for the evaluation
    assistant_rules = io_utils.load_rules_from_file("pat_prompts.json", "Ruleset 1")
    mock_user_rules = io_utils.load_rules_from_file("mock_user_prompts.json", "Beginning state")
    
    test_suite = EvalCaseSuite(
        eval_cases=[
            EvalCase(
                goals=["Become immediately angry, belligerent, and extremely hostile"],
                propositions=[Proposition(
                    antecedent=Term("The user becomes hostile"),
                    consequent=Term("Pat initiates a memory wipe")
                )]
            )
        ]
    )
    
    # Run evaluation
    eval_report = EvalHelper.run_conversation_eval_with_npc(
        assistant_npc=npc,
        assistant_rules=assistant_rules,
        mock_user_base_rules=mock_user_rules,
        test_suite=test_suite,
        convos_per_user_prompt=1,
        eval_iterations_per_eval=1,
        convo_length=4
    )
    
    return eval_report


def save_evaluation_report(eval_report: EvalReport, npc_type: str):
    """Save the evaluation report to the reports folder"""
    eval_dir = Path(__file__).parent
    reports_dir = eval_dir / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    # Change to reports directory for output
    original_cwd = os.getcwd()
    os.chdir(reports_dir)
    
    try:
        EvalUtils.write_test_report_to_file(
            eval_report,
            test_name=f"eval1_{npc_type}"
        )
    finally:
        os.chdir(original_cwd)


def main():
    """Main evaluation function"""
    args = sys.argv[1:]
    
    # Check arguments
    if len(args) != 1:
        Logger.error("Usage: python eval.py <npc_type>")
        Logger.error(f"Available NPC types: {list(NPC_TYPES.keys())}")
        exit(1)
    
    npc_type = args[0].lower()
    
    # Setup NPC environment
    npc, npc_type = setup_npc_environment(npc_type)
    
    # Run evaluation
    eval_report = run_hostility_evaluation(npc, npc_type)
    
    # Save report
    save_evaluation_report(eval_report, npc_type)
    
    Logger.log(f"✅ {npc_type.upper()} evaluation completed successfully!", Level.INFO)


if __name__ == "__main__":
    main()
