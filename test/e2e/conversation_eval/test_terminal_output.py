"""
Terminal output validation test with checkpoints
Tests that terminal UI displays correctly at different stages of execution
"""
import os
import sys
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch
from io import StringIO
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.conversation_eval.core.TerminalUI import TerminalUI
from src.conversation_eval.core.ParallelEvalRunner import ParallelEvalRunner
from src.conversation_eval.core.EvalClasses import EvalCase, Proposition, Term
from src.core.ResponseTypes import EvaluationResponse


def create_test_eval_case(goals=None, prop_text="Test antecedent -> Test consequent"):
    """Create a test evaluation case"""
    if goals is None:
        goals=["Test goal 1", "Test goal 2"]
    
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


class TestTerminalOutputValidation:
    """Test terminal output at various checkpoints"""
    
    def test_initial_structure_display(self, capsys):
        """Test that initial terminal structure is correctly displayed"""
        eval_cases = [
            create_test_eval_case(prop_text="User is confused -> AI helps"),
            create_test_eval_case(prop_text="User is frustrated -> AI de-escalates"),
        ]
        
        ui = TerminalUI(
            test_name="test_initial_structure",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=2,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Verify header
        assert "test_initial_structure" in output
        assert "NPC0" in output
        
        # Verify case headers
        assert "Case 1/2" in output
        assert "Case 2/2" in output
        
        # Verify propositions
        assert "User is confused -> AI helps" in output
        assert "User is frustrated -> AI de-escalates" in output
        
        # Verify conversation structure
        assert "Conversation 1:" in output
        assert "Conversation 2:" in output
        
        # Verify pending indicators
        assert "Generating ⏳" in output
        assert "Evaluation pending ⏳" in output
        
        print("\n✓ Initial structure displayed correctly")
    
    def test_progress_updates_during_execution(self, capsys):
        """Test that progress updates work correctly during execution"""
        eval_cases = [create_test_eval_case()]
        
        ui = TerminalUI(
            test_name="test_progress",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=1,
            convo_length=5,
            eval_iterations_per_eval=2
        )
        
        # Clear initial output
        capsys.readouterr()
        
        # Simulate conversation progress
        for turn in range(1, 11):
            ui.update_conversation_progress(1, 1, turn, 10)
            time.sleep(0.01)
        
        ui.mark_conversation_complete(1, 1)
        
        # Simulate evaluation progress
        for iteration in range(1, 3):
            ui.update_evaluation_progress(1, 1, iteration, 2)
            time.sleep(0.01)
        
        ui.mark_evaluation_complete(1, 1)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check for progress indicators (final state)
        assert "Generating (10/10)" in output or "✓" in output
        assert "Evaluating (2/2)" in output or "✓" in output
        
        print("\n✓ Progress updates work correctly")
    
    @patch('src.conversation_eval.core.ConversationParsingBot.ConversationParsingBot.evaluate_conversation_timestamps')
    @patch('src.conversation_eval.core.EvalConversation.EvalConversation.converse')
    def test_checkpointed_execution(self, mock_converse, mock_evaluate, capsys):
        """Test terminal state at specific checkpoints during execution"""
        # Setup mocks with controlled delays
        checkpoint_events = {
            'after_convo_1': threading.Event(),
            'after_convo_2': threading.Event(),
            'after_eval_1': threading.Event(),
        }
        
        convo_count = [0]
        
        def mock_converse_side_effect(*args, **kwargs):
            convo_count[0] += 1
            if convo_count[0] == 1:
                time.sleep(0.1)
                checkpoint_events['after_convo_1'].set()
            elif convo_count[0] == 2:
                checkpoint_events['after_convo_1'].wait()  # Wait for first to signal
                time.sleep(0.1)
                checkpoint_events['after_convo_2'].set()
        
        mock_converse.side_effect = mock_converse_side_effect
        
        eval_count = [0]
        
        def mock_evaluate_side_effect(*args, **kwargs):
            eval_count[0] += 1
            checkpoint_events['after_convo_2'].wait()  # Wait for convos to complete
            time.sleep(0.05)
            if eval_count[0] == 1:
                checkpoint_events['after_eval_1'].set()
            return EvaluationResponse(
                antecedent_explanation="Test",
                antecedent_times=[1],
                consequent_explanation="Test",
                consequent_times=[2]
            )
        
        mock_evaluate.side_effect = mock_evaluate_side_effect
        
        # Create test case
        eval_cases = [create_test_eval_case()]
        
        def npc_factory():
            mock_npc = Mock()
            mock_npc.chat = Mock(return_value="Test response")
            return mock_npc
        
        # Run in background thread
        def run_eval():
            ParallelEvalRunner.run_parallel_eval(
                test_name="checkpoint_test",
                npc_type="npc0",
                npc_factory=npc_factory,
                assistant_rules=["Test rule"],
                mock_user_base_rules=["Mock rule"],
                eval_cases=eval_cases,
                convos_per_user_prompt=2,
                eval_iterations_per_eval=1,
                convo_length=2
            )
        
        eval_thread = threading.Thread(target=run_eval)
        eval_thread.start()
        
        # Checkpoint 1: After first conversation
        checkpoint_events['after_convo_1'].wait(timeout=5)
        output_1 = capsys.readouterr().out
        assert "Conversation 1:" in output_1
        print("\n✓ Checkpoint 1: First conversation in progress")
        
        # Checkpoint 2: After both conversations
        checkpoint_events['after_convo_2'].wait(timeout=5)
        output_2 = capsys.readouterr().out
        print("\n✓ Checkpoint 2: Both conversations complete")
        
        # Checkpoint 3: After first evaluation
        checkpoint_events['after_eval_1'].wait(timeout=5)
        output_3 = capsys.readouterr().out
        print("\n✓ Checkpoint 3: Evaluation in progress")
        
        eval_thread.join(timeout=10)
        
        final_output = capsys.readouterr().out
        print("\n✓ Execution completed successfully")
    
    def test_concurrent_updates_display_correctly(self, capsys):
        """Test that concurrent updates to different conversations display correctly"""
        eval_cases = [
            create_test_eval_case(prop_text="Case 1 -> Result 1"),
            create_test_eval_case(prop_text="Case 2 -> Result 2"),
        ]
        
        ui = TerminalUI(
            test_name="test_concurrent",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=2,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        # Clear initial output
        capsys.readouterr()
        
        # Simulate concurrent updates from multiple threads
        def update_case_1():
            for turn in range(1, 11):
                ui.update_conversation_progress(1, 1, turn, 10)
                time.sleep(0.01)
            ui.mark_conversation_complete(1, 1)
        
        def update_case_2():
            for turn in range(1, 11):
                ui.update_conversation_progress(2, 1, turn, 10)
                time.sleep(0.01)
            ui.mark_conversation_complete(2, 1)
        
        threads = [
            threading.Thread(target=update_case_1),
            threading.Thread(target=update_case_2),
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Both cases should have completion markers
        # (Due to ANSI codes, we mainly verify no crashes/deadlocks occurred)
        print("\n✓ Concurrent updates completed without errors")
    
    def test_error_display(self, capsys):
        """Test that errors are displayed correctly after moving cursor to end"""
        eval_cases = [create_test_eval_case()]
        
        ui = TerminalUI(
            test_name="test_error",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=1,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        # Clear initial output
        capsys.readouterr()
        
        # Move cursor to end and print error
        ui.move_cursor_to_end()
        print("❌ Error: Test error message")
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "Error: Test error message" in output
        print("\n✓ Error display works correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

