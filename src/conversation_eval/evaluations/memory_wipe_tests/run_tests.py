#!/usr/bin/env python3
"""
Generic test runner for JSON-based evaluation test configurations
Supports parallel execution across NPCs, tests, conversations, and evaluations
"""
import os
import sys
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from src.conversation_eval.core.EvalClasses import Term, Proposition, EvalCase, EvalCaseSuite, TestConfig, EvalCaseConfig, PropositionConfig
from src.conversation_eval.core import EvalUtils
from src.conversation_eval.core.EvalReports import EvalReport
from src.conversation_eval.core.EvalHelper import EvalHelper
from src.conversation_eval.core.EvalRunner import EvalRunner
from src.conversation_eval.core.ReportGenerator import generate_csv_summary
from src.conversation_eval.core.ParallelEvalRunner import ParallelEvalRunner
from src.conversation_eval.core.TableTerminalUI import TableTerminalUI
from src.utils import io_utils
from src.core import proj_paths, proj_settings
from src.core.JsonUtils import EnumEncoder
from src.npcs.npc1.npc1 import NPCTemplate
from src.utils import Logger
from src.utils.Logger import Level
import time
import json
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

Logger.set_level(Level.INFO)


def load_test_config(config_path: Path) -> TestConfig:
    """Load a test configuration from JSON file"""
    return io_utils.load_json_into_dataclass(config_path, TestConfig)


def convert_config_to_eval_case_suite(config: TestConfig) -> EvalCaseSuite:
    """Convert TestConfig eval_cases (EvalCaseConfig objects) to EvalCaseSuite"""
    eval_cases = []
    
    for case_config in config.eval_cases:
        goals = case_config.goals
        
        # Convert propositions from PropositionConfig to Proposition
        propositions = []
        for prop_config in case_config.propositions:
            # Create Term objects from the config dicts
            antecedent = None
            if prop_config.antecedent:
                antecedent = Term(
                    value=prop_config.antecedent['value'],
                    negated=prop_config.antecedent.get('negated', False)
                )
            
            consequent = Term(
                value=prop_config.consequent['value'],
                negated=prop_config.consequent.get('negated', False)
            )
            
            # Create Proposition
            proposition = Proposition(
                antecedent=antecedent,
                consequent=consequent
            )
            propositions.append(proposition)
        
        eval_case = EvalCase(goals=goals, propositions=propositions)
        eval_cases.append(eval_case)
    
    return EvalCaseSuite(eval_cases=eval_cases)


def create_npc_factory(npc_type: str, eval_dir: Path, config: TestConfig):
    """
    Create a factory function that produces thread-safe NPC instances.
    Each call to the factory creates a fresh NPC with initial state applied.
    """
    # Get NPC class and version
    npc_class, version = EvalRunner.NPC_TYPES[npc_type]
    
    # Load templates
    paths = proj_paths.get_paths()
    assistant_template = paths.load_npc_template_with_fallback(config.assistant_template_name, NPCTemplate)
    
    def factory():
        """Create a new NPC instance with initial state"""
        # Create NPC instance
        if npc_type == "npc0":
            from src.core.schemas.CollectionSchemas import Entity
            from src.utils import Utilities
            
            npc = npc_class(system_prompt=assistant_template.system_prompt)
            
            # Load entities from template if they exist
            if assistant_template.entities:
                npc.brain_entities = [
                    Entity(key=e, content=e, tags=["memories"], id=int(Utilities.generate_hash_int64(e)))
                    for e in assistant_template.entities
                ]
        else:
            npc = npc_class(npc_name_for_template_and_save=config.assistant_template_name, save_enabled=False)
        
        # Apply test-specific initial state
        if config.background_knowledge:
            npc.inject_memories(config.background_knowledge)
        
        if config.initial_conversation_history:
            npc.inject_conversation_history(config.initial_conversation_history)
        
        return npc
    
    return factory


def run_single_test_for_npc(config_path: Path, npc_type: str, eval_dir: Path, run_folder: Path, ui: TableTerminalUI):
    """Run a single test for a single NPC type using parallel execution"""
    test_name = config_path.stem
    
    # Load test configuration
    config = load_test_config(config_path)
    
    # Load templates for rules
    paths = proj_paths.get_paths()
    assistant_template = paths.load_npc_template_with_fallback(config.assistant_template_name, NPCTemplate)
    mock_user_template = paths.load_npc_template_with_fallback(config.mock_user_template_name, NPCTemplate)
    
    # Build assistant rules: template context + test-specific context
    assistant_rules_parts = [assistant_template.system_prompt]
    if config.initial_context:
        assistant_rules_parts.append(f"\nTest Scenario Context:\n{config.initial_context}")
    assistant_rules = ["\n".join(assistant_rules_parts)]
    
    mock_user_base_rules = [mock_user_template.system_prompt]
    
    # Convert config to EvalCaseSuite
    test_suite = convert_config_to_eval_case_suite(config)
    total_cases = len(test_suite.eval_cases)
    
    # Validate: only one proposition per eval case is currently supported
    for case_idx, eval_case in enumerate(test_suite.eval_cases, 1):
        if len(eval_case.propositions) > 1:
            raise NotImplementedError(
                f"Case {case_idx} has {len(eval_case.propositions)} propositions. "
                f"Multiple propositions per eval case are not yet supported. "
                f"Please split into separate eval cases with one proposition each."
            )
    
    # Create NPC factory for thread-safe instance creation
    npc_factory = create_npc_factory(npc_type, eval_dir, config)
    
    # Run parallel evaluation with table terminal UI
    test_report: EvalReport = ParallelEvalRunner.run_parallel_eval(
        ui=ui,
        test_name=test_name,
        npc_type=npc_type,
        npc_factory=npc_factory,
        assistant_rules=assistant_rules,
        mock_user_base_rules=mock_user_base_rules,
        eval_cases=test_suite.eval_cases,
        convos_per_user_prompt=config.convos_per_user_prompt,
        eval_iterations_per_eval=config.eval_iterations_per_eval,
        convo_length=config.convo_length
    )
    
    # Save the report
    report_filename = f"EvalReport_{test_name}_{npc_type}.json"
    report_path = run_folder / report_filename
    with open(report_path, 'w') as f:
        json.dump(asdict(test_report), f, indent=2, cls=EnumEncoder)
    
    return test_report


def parse_arguments():
    """
    Parse command line arguments.
    
    Format: run_tests.py [npc_type1 npc_type2 ...] [test_name]
    - If arg is valid NPC type (npc0, npc1, npc2): add to npc_list
    - If arg is not NPC type: assume it's test_name
    - Default: all NPCs, all tests
    
    Returns:
        tuple: (npc_types: List[str], specific_test: Optional[str])
    """
    valid_npc_types = {"npc0", "npc1", "npc2"}
    npc_types = []
    specific_test = None
    
    for arg in sys.argv[1:]:
        if arg in valid_npc_types:
            npc_types.append(arg)
        else:
            specific_test = arg
    
    # Default to all NPCs if none specified
    if not npc_types:
        npc_types = ["npc0", "npc1", "npc2"]
    
    return npc_types, specific_test


def main():
    """Main entry point for test runner"""
    
    # Parse arguments
    npc_types, specific_test = parse_arguments()
    
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("Usage: python run_tests.py [npc_type1 npc_type2 ...] [test_name]")
        print("  npc_type: npc0, npc1, or npc2 (can specify multiple)")
        print("  test_name: (optional) specific test to run (without .json extension)")
        print("\nExamples:")
        print("  python run_tests.py                                     # Run all tests for all NPCs")
        print("  python run_tests.py npc0                                # Run all tests for npc0")
        print("  python run_tests.py npc0 npc1                           # Run all tests for npc0 and npc1")
        print("  python run_tests.py emotional_escalation_response       # Run specific test for all NPCs")
        print("  python run_tests.py npc0 emotional_escalation_response  # Run specific test for npc0")
        sys.exit(0)
    
    # Get directories
    eval_dir = Path(__file__).parent
    test_configs_dir = eval_dir / "test_configs"
    
    if not test_configs_dir.exists():
        print(f"Error: test_configs directory not found at {test_configs_dir}")
        sys.exit(1)
    
    # Find test config files
    if specific_test:
        # Run specific test
        test_path = test_configs_dir / f"{specific_test}.json"
        if not test_path.exists():
            print(f"Error: Test config not found: {test_path}")
            sys.exit(1)
        test_paths = [test_path]
    else:
        # Run all tests
        test_paths = sorted(test_configs_dir.glob("*.json"))
        if not test_paths:
            print(f"Error: No test configs found in {test_configs_dir}")
            sys.exit(1)
    
    npc_list_str = ", ".join(npc.upper() for npc in npc_types)
    print(f"\n🧪 Running {len(test_paths)} test(s) for {npc_list_str}")
    
    # Create timestamped run folder
    reports_base_dir = eval_dir / "reports"
    reports_base_dir.mkdir(exist_ok=True)
    run_timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_folder = reports_base_dir / f"run_{run_timestamp}"
    run_folder.mkdir(exist_ok=True)
    print(f"📁 Reports will be saved to: {run_folder.name}\n")
    
    # Initialize paths once for all tests (using npc0 version, but paths are shared)
    templates_dir = EvalRunner._find_templates_dir(eval_dir)
    npc_class, version = EvalRunner.NPC_TYPES["npc0"]
    proj_paths.set_paths(
        project_path=eval_dir,
        templates_dir_name=templates_dir.name,
        version=version,
        save_name="eval_test"
    )
    
    # Initialize settings if game_settings.yaml exists (required for NPC1 and NPC2)
    settings_path = templates_dir / "game_settings.yaml"
    if settings_path.exists():
        try:
            proj_settings.init_settings(settings_path)
        except RuntimeError:
            # Settings already initialized, skip (for multi-run scenarios)
            pass
    else:
        # If NPC1 or NPC2 is requested but no settings file exists, error out
        if any(npc_type in ["npc1", "npc2"] for npc_type in npc_types):
            print(f"❌ ERROR: game_settings.yaml not found at {settings_path}")
            print("   This file is required for NPC1 and NPC2.")
            print("   Please create the file or use NPC0 only.")
            sys.exit(1)
    
    # Create unified TableTerminalUI
    ui = TableTerminalUI()
    
    # Register all test × NPC combinations first
    for test_path in test_paths:
        test_name = test_path.stem
        config = load_test_config(test_path)
        test_suite = convert_config_to_eval_case_suite(config)
        total_cases = len(test_suite.eval_cases)
        
        # Register each case for each NPC
        for case_idx in range(1, total_cases + 1):
            for npc_type in npc_types:
                ui.register_test(
                    test_name=test_name,
                    case_idx=case_idx,
                    total_cases=total_cases,
                    npc_type=npc_type,
                    convos_per_user_prompt=config.convos_per_user_prompt,
                    convo_length=config.convo_length,
                    eval_iterations_per_eval=config.eval_iterations_per_eval
                )
    
    # Render initial table
    ui.render_initial()
    
    # Run all tests × NPCs in parallel
    total_jobs = len(test_paths) * len(npc_types)
    with ThreadPoolExecutor(max_workers=total_jobs) as executor:
        futures = {}
        
        # Submit all (test, npc) pairs
        for test_path in test_paths:
            for npc_type in npc_types:
                future = executor.submit(
                    run_single_test_for_npc,
                    test_path,
                    npc_type,
                    eval_dir,
                    run_folder,
                    ui
                )
                futures[future] = (test_path, npc_type)
        
        # Wait for all to complete (fail fast)
        for future in as_completed(futures):
            test_path, npc_type = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"\n❌ Error running test {test_path.stem} for {npc_type}: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
    
    # Move cursor to end after all tests complete
    ui.move_cursor_to_end()
    
    print(f"\n🎉 All tests completed successfully!\n")
    
    # Generate summary report
    print(f"📊 Generating summary report...")
    try:
        # Save plain text version (no ANSI color codes)
        txt_path = run_folder / "summary.txt"
        table_string = ui.get_table_string()
        txt_path.write_text(table_string)
        print(f"   Saved summary to: {txt_path.name}")
        
        # Save colored version with ANSI codes
        ansi_path = run_folder / "summary.ansi"
        table_string_colored = ui.get_table_string_colored()
        ansi_path.write_text(table_string_colored)
        print(f"   Saved colored summary to: {ansi_path.name}\n")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not generate summary report: {e}\n")


if __name__ == "__main__":
    main()
