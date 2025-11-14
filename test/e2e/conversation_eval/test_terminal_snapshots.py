"""
Terminal Snapshot Tests with Controlled Execution
Tests terminal UI visual output at specific moments using snapshot comparisons
"""
import os
import sys
from pathlib import Path
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from test.utils.virtual_terminal import VirtualTerminal
from test.utils.snapshot_helper import redirect_to_vterm, assert_snapshot_matches, save_snapshot
from src.conversation_eval.core.TerminalUI import TerminalUI
from src.conversation_eval.core.EvalClasses import EvalCase, Proposition, Term


# Check if we should update snapshots
UPDATE_SNAPSHOTS = os.environ.get('UPDATE_SNAPSHOTS', 'false').lower() == 'true'


def create_test_eval_case(prop_text="Test antecedent -> Test consequent", goals=None):
    """Create a test evaluation case"""
    if goals is None:
        goals = ["Test goal 1", "Test goal 2"]
    
    antecedent_text, consequent_text = prop_text.split(" -> ")
    
    return EvalCase(
        goals=goals,
        propositions=[
            Proposition(
                antecedent=Term(value=antecedent_text, negated=False),
                consequent=Term(value=consequent_text, negated=False),
                min_responses_for_consequent=1,
                max_responses_for_consequent=0,
                max_responses_for_antecedent=3
            )
        ]
    )


class TestTerminalSnapshots:
    """Snapshot tests for terminal UI visual output"""
    
    def test_single_test_initial_render(self):
        """Test snapshot of initial render for a single test"""
        vterm = VirtualTerminal()
        
        with redirect_to_vterm(vterm):
            eval_cases = [create_test_eval_case(prop_text="User is confused -> AI helps")]
            
            ui = TerminalUI(
                test_name="test_single",
                npc_type="npc0",
                eval_cases=eval_cases,
                convos_per_user_prompt=2,
                convo_length=5,
                eval_iterations_per_eval=1
            )
        
        snapshot = vterm.get_snapshot()
        assert_snapshot_matches(snapshot, "single_test_initial_render.txt", UPDATE_SNAPSHOTS)
    
    def test_single_test_conversation_progress(self):
        """Test snapshot of conversation in progress"""
        vterm = VirtualTerminal()
        
        with redirect_to_vterm(vterm):
            eval_cases = [create_test_eval_case(prop_text="User is confused -> AI helps")]
            
            ui = TerminalUI(
                test_name="test_single",
                npc_type="npc0",
                eval_cases=eval_cases,
                convos_per_user_prompt=2,
                convo_length=5,
                eval_iterations_per_eval=1
            )
            
            # Simulate conversation 1 at 50% progress
            ui.update_conversation_progress(1, 1, 5, 10)
        
        snapshot = vterm.get_snapshot()
        assert_snapshot_matches(snapshot, "single_test_conv1_progress.txt", UPDATE_SNAPSHOTS)
    
    def test_single_test_conversation_complete(self):
        """Test snapshot of conversation complete"""
        vterm = VirtualTerminal()
        
        with redirect_to_vterm(vterm):
            eval_cases = [create_test_eval_case(prop_text="User is confused -> AI helps")]
            
            ui = TerminalUI(
                test_name="test_single",
                npc_type="npc0",
                eval_cases=eval_cases,
                convos_per_user_prompt=2,
                convo_length=5,
                eval_iterations_per_eval=1
            )
            
            # Simulate conversation 1 complete
            ui.update_conversation_progress(1, 1, 10, 10)
        
        snapshot = vterm.get_snapshot()
        assert_snapshot_matches(snapshot, "single_test_conv1_complete.txt", UPDATE_SNAPSHOTS)
    
    def test_single_test_evaluation_progress(self):
        """Test snapshot of evaluation in progress"""
        vterm = VirtualTerminal()
        
        with redirect_to_vterm(vterm):
            eval_cases = [create_test_eval_case(prop_text="User is confused -> AI helps")]
            
            ui = TerminalUI(
                test_name="test_single",
                npc_type="npc0",
                eval_cases=eval_cases,
                convos_per_user_prompt=2,
                convo_length=5,
                eval_iterations_per_eval=2
            )
            
            # Simulate conversation 1 complete, evaluation in progress
            ui.update_conversation_progress(1, 1, 10, 10)
            ui.update_evaluation_progress(1, 1, 1, 2)
        
        snapshot = vterm.get_snapshot()
        assert_snapshot_matches(snapshot, "single_test_eval_progress.txt", UPDATE_SNAPSHOTS)
    
    def test_sequential_tests_no_overlap(self):
        """
        CRITICAL TEST: Verify that sequential tests don't overlap.
        This is the test that should catch the misalignment issue.
        """
        vterm = VirtualTerminal(rows=150)  # Extra rows for two tests
        
        with redirect_to_vterm(vterm):
            # Test 1
            eval_cases1 = [create_test_eval_case(prop_text="Test 1 antecedent -> Test 1 consequent")]
            
            ui1 = TerminalUI(
                test_name="test1",
                npc_type="npc0",
                eval_cases=eval_cases1,
                convos_per_user_prompt=2,
                convo_length=5,
                eval_iterations_per_eval=1
            )
            
            # Progress through test 1
            ui1.update_conversation_progress(1, 1, 5, 10)
            ui1.update_conversation_progress(1, 1, 10, 10)
            ui1.update_conversation_progress(1, 2, 10, 10)
            ui1.update_evaluation_progress(1, 1, 1, 1)
            ui1.update_evaluation_progress(1, 2, 1, 1)
            ui1.move_cursor_to_end()
            
            # Capture after test 1 completes
            snapshot_after_test1 = vterm.get_snapshot()
            
            # Test 2 starts - THIS IS WHERE OVERLAP WOULD OCCUR
            eval_cases2 = [create_test_eval_case(prop_text="Test 2 antecedent -> Test 2 consequent")]
            
            ui2 = TerminalUI(
                test_name="test2",
                npc_type="npc0",
                eval_cases=eval_cases2,
                convos_per_user_prompt=2,
                convo_length=5,
                eval_iterations_per_eval=1
            )
            
            # Capture after test 2 renders
            snapshot_after_test2_render = vterm.get_snapshot()
            
            # Progress through test 2
            ui2.update_conversation_progress(1, 1, 5, 10)
            ui2.update_conversation_progress(1, 1, 10, 10)
            ui2.update_conversation_progress(1, 2, 10, 10)
            ui2.update_evaluation_progress(1, 1, 1, 1)
            ui2.update_evaluation_progress(1, 2, 1, 1)
            ui2.move_cursor_to_end()
            
            # Final snapshot
            snapshot_final = vterm.get_snapshot()
        
        # Save all snapshots
        assert_snapshot_matches(snapshot_after_test1, "sequential_after_test1.txt", UPDATE_SNAPSHOTS)
        assert_snapshot_matches(snapshot_after_test2_render, "sequential_after_test2_render.txt", UPDATE_SNAPSHOTS)
        assert_snapshot_matches(snapshot_final, "sequential_final.txt", UPDATE_SNAPSHOTS)
        
        # Verify test 1 content is still intact in final snapshot
        assert "test1" in snapshot_final, "Test 1 name should still be visible"
        assert "Test 1 antecedent -> Test 1 consequent" in snapshot_final, "Test 1 proposition should still be visible"
        
        # Verify test 2 content is present
        assert "test2" in snapshot_final, "Test 2 name should be visible"
        assert "Test 2 antecedent -> Test 2 consequent" in snapshot_final, "Test 2 proposition should be visible"
        
        # Verify no overlap: test 1 header should not be corrupted
        lines = snapshot_final.split('\n')
        test1_header_found = False
        test1_header_intact = False
        for i, line in enumerate(lines):
            if "test1" in line and "Test:" in line:
                test1_header_found = True
                # Check if the line is properly formatted (not corrupted)
                if line.strip().startswith("🧪 Test: test1"):
                    test1_header_intact = True
                break
        
        assert test1_header_found, "Test 1 header should exist"
        assert test1_header_intact, "Test 1 header should not be corrupted by test 2 updates"
    
    def test_multiple_conversations_parallel(self):
        """Test snapshot with multiple conversations progressing in parallel"""
        vterm = VirtualTerminal()
        
        with redirect_to_vterm(vterm):
            eval_cases = [create_test_eval_case(prop_text="User is confused -> AI helps")]
            
            ui = TerminalUI(
                test_name="test_parallel",
                npc_type="npc0",
                eval_cases=eval_cases,
                convos_per_user_prompt=3,
                convo_length=5,
                eval_iterations_per_eval=1
            )
            
            # Simulate conversations at different progress levels
            ui.update_conversation_progress(1, 1, 3, 10)
            ui.update_conversation_progress(1, 2, 7, 10)
            ui.update_conversation_progress(1, 3, 5, 10)
        
        snapshot = vterm.get_snapshot()
        assert_snapshot_matches(snapshot, "parallel_conversations_mixed_progress.txt", UPDATE_SNAPSHOTS)
    
    def test_multiple_cases(self):
        """Test snapshot with multiple evaluation cases"""
        vterm = VirtualTerminal()
        
        with redirect_to_vterm(vterm):
            eval_cases = [
                create_test_eval_case(prop_text="Case 1 antecedent -> Case 1 consequent"),
                create_test_eval_case(prop_text="Case 2 antecedent -> Case 2 consequent"),
            ]
            
            ui = TerminalUI(
                test_name="test_multi_case",
                npc_type="npc0",
                eval_cases=eval_cases,
                convos_per_user_prompt=2,
                convo_length=5,
                eval_iterations_per_eval=1
            )
            
            # Case 1 in progress, case 2 pending
            ui.update_conversation_progress(1, 1, 5, 10)
            ui.update_conversation_progress(1, 2, 3, 10)
        
        snapshot = vterm.get_snapshot()
        assert_snapshot_matches(snapshot, "multi_case_case1_progress.txt", UPDATE_SNAPSHOTS)


if __name__ == "__main__":
    # Run with UPDATE_SNAPSHOTS=true to regenerate golden files
    pytest.main([__file__, "-v", "-s"])

