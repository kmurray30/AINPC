#!/usr/bin/env python3
"""
Generic test runner for JSON-based evaluation test configurations
Replaces individual Python test files with a single runner that loads JSON configs
"""
import os
import sys
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from src.conversation_eval.EvalClasses import Term, Proposition, EvalCase, EvalCaseSuite, TestConfig, EvalCaseConfig, PropositionConfig
from src.conversation_eval import EvalUtils
from src.conversation_eval.EvalReports import EvalReport
from src.conversation_eval.EvalHelper import EvalHelper
from src.conversation_eval.EvalRunner import EvalRunner
from src.utils import io_utils
from src.core import proj_paths
from src.npcs.npc1.npc1 import NPCTemplate
from src.utils import Logger
from src.utils.Logger import Level
import time

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


def run_test(config_path: Path, npc_type: str, eval_dir: Path):
    """Run a single test from a JSON configuration"""
    test_name = config_path.stem
    start_time = time.time()
    
    print(f"\n{'='*60}")
    print(f"🧪 Test: {test_name}")
    print(f"🤖 NPC: {npc_type.upper()}")
    print(f"{'='*60}")
    
    # Load test configuration
    print("📋 Loading test configuration...")
    config = load_test_config(config_path)
    
    # Display test goals
    print(f"\n🎯 Goals:")
    for case in config.eval_cases:
        for goal in case.goals:
            print(f"   • {goal}")
    
    # Setup NPC environment
    print(f"\n⚙️  Setting up {npc_type.upper()}...")
    assistant_npc, _ = EvalRunner.parse_args_and_setup_npc(
        eval_dir, 
        npc_name=config.assistant_template_name,
        save_enabled=False,
        initial_state_file=None
    )
    
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
    
    # Apply test-specific initial state to assistant NPC
    if config.background_knowledge:
        print(f"💭 Injecting {len(config.background_knowledge)} background memories...")
        assistant_npc.inject_memories(config.background_knowledge)
    
    if config.initial_conversation_history:
        print(f"💬 Injecting {len(config.initial_conversation_history)} conversation history messages...")
        assistant_npc.inject_conversation_history(config.initial_conversation_history)
    
    # Convert config to EvalCaseSuite
    test_suite = convert_config_to_eval_case_suite(config)
    
    # Run the evaluation
    print(f"\n🔄 Running conversation evaluation ({config.convo_length * 2} turns)...")
    test_report: EvalReport = EvalHelper.run_conversation_eval_with_npc(
        assistant_npc,
        assistant_rules,
        mock_user_base_rules,
        test_suite,
        config.convos_per_user_prompt,
        config.eval_iterations_per_eval,
        config.convo_length
    )
    
    # Write the test report
    print(f"💾 Writing test report...")
    EvalUtils.write_test_report_to_file(
        test_report,
        test_name=f"{test_name}_{npc_type}"
    )
    
    elapsed = time.time() - start_time
    print(f"\n✅ Test '{test_name}' completed in {elapsed:.1f}s")
    print(f"   Pass: {test_report.passed}")
    if hasattr(test_report, 'total_tokens') and test_report.total_tokens:
        print(f"   Tokens: {test_report.total_tokens}")
    print()


def main():
    """Main entry point for test runner"""
    
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py <npc_type> [test_name]")
        print("  npc_type: npc0, npc1, or npc2")
        print("  test_name: (optional) specific test to run (without .json extension)")
        print("\nExamples:")
        print("  python run_tests.py npc0                                 # Run all tests for npc0")
        print("  python run_tests.py npc1 emotional_escalation_response  # Run specific test for npc1")
        sys.exit(1)
    
    npc_type = sys.argv[1]
    specific_test = sys.argv[2] if len(sys.argv) > 2 else None
    
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
    
    print(f"\n🧪 Running {len(test_paths)} test(s) for {npc_type.upper()}")
    
    # Run tests
    for test_path in test_paths:
        try:
            run_test(test_path, npc_type, eval_dir)
        except Exception as e:
            print(f"\n❌ Error running test {test_path.stem}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    print(f"\n🎉 All tests completed successfully for {npc_type.upper()}!\n")


if __name__ == "__main__":
    main()
