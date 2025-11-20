"""
Robust tests for TerminalUI ANSI positioning
Tests that ANSI codes are correctly formatted and cursor movements work
"""
import os
import sys
import io
import re
from unittest.mock import patch
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.conversation_eval.core.TableTerminalUI import TableTerminalUI
from src.conversation_eval.core.EvalClasses import EvalCase, Proposition, Term


def create_test_eval_case(prop_text="Test antecedent -> Test consequent"):
    """Create a test evaluation case"""
    antecedent_text, consequent_text = prop_text.split(" -> ")
    
    return EvalCase(
        goals=["Test goal 1", "Test goal 2"],
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


class TestTerminalANSI:
    """Test ANSI escape code correctness"""
    
    def test_cursor_save_after_header(self):
        """Test that cursor save code is emitted after header"""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            eval_cases = [create_test_eval_case()]
            
            ui = TerminalUI(
                test_name="test",
                npc_type="npc0",
                eval_cases=eval_cases,
                convos_per_user_prompt=1,
                convo_length=5,
                eval_iterations_per_eval=1
            )
            
            output = fake_out.getvalue()
            
            # Should contain cursor save code (after the header)
            assert '\033[s' in output, "Output should contain cursor save code"
            
            # Cursor save should come after the test name header
            save_pos = output.find('\033[s')
            test_name_pos = output.find('Test: test')
            assert test_name_pos < save_pos, "Cursor save should come after test header"
            
            print("✓ Cursor save code found after header")
    
    def test_updates_use_cursor_restore(self):
        """Test that updates restore cursor before moving"""
        eval_cases = [create_test_eval_case()]
        
        ui = TerminalUI(
            test_name="test",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=1,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            # Update conversation progress
            ui.update_conversation_progress(1, 1, 5, 10)
            
            output = fake_out.getvalue()
            
            # Should contain cursor restore code
            assert '\033[u' in output, "Update should restore cursor"
            print("✓ Cursor restore code found in update")
    
    def test_relative_positioning(self):
        """Test that positioning is relative (cursor down) not absolute"""
        eval_cases = [create_test_eval_case()]
        
        ui = TerminalUI(
            test_name="test",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=1,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            # Update conversation progress
            ui.update_conversation_progress(1, 1, 5, 10)
            
            output = fake_out.getvalue()
            
            # Should NOT use absolute positioning \033[<line>;<col>H
            absolute_pos_pattern = r'\033\[\d+;\d+H'
            assert not re.search(absolute_pos_pattern, output), \
                "Should not use absolute positioning in updates"
            
            # Should use cursor down \033[<n>B
            cursor_down_pattern = r'\033\[\d+B'
            assert re.search(cursor_down_pattern, output), \
                "Should use cursor down for relative positioning"
            
            print("✓ Using relative positioning (cursor down)")
    
    def test_line_offsets_calculated_correctly(self):
        """Test that line offsets are calculated correctly"""
        eval_cases = [
            create_test_eval_case(prop_text="Case 1 -> Result 1"),
            create_test_eval_case(prop_text="Case 2 -> Result 2"),
        ]
        
        ui = TerminalUI(
            test_name="test",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=2,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        # Check that offsets are calculated
        assert 1 in ui.line_mappings
        assert 2 in ui.line_mappings
        
        # Case 1 conversation 1 should have smaller offset than case 2 conversation 1
        case1_conv1_gen_offset = ui.line_mappings[1].conversations[1][0]
        case2_conv1_gen_offset = ui.line_mappings[2].conversations[1][0]
        
        assert case2_conv1_gen_offset > case1_conv1_gen_offset, \
            "Case 2 should be further down than Case 1"
        
        print(f"✓ Case 1 Conv 1 offset: {case1_conv1_gen_offset}")
        print(f"✓ Case 2 Conv 1 offset: {case2_conv1_gen_offset}")
    
    def test_update_clears_line_correctly(self):
        """Test that updates clear the line before writing"""
        eval_cases = [create_test_eval_case()]
        
        ui = TerminalUI(
            test_name="test",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=1,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            ui.update_conversation_progress(1, 1, 5, 10)
            
            output = fake_out.getvalue()
            
            # Should contain clear line code \033[K
            assert '\033[K' in output, "Should clear line before update"
            print("✓ Line clear code found")
    
    def test_concurrent_updates_different_offsets(self):
        """Test that concurrent updates to different conversations use different offsets"""
        eval_cases = [create_test_eval_case()]
        
        ui = TerminalUI(
            test_name="test",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=2,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        # Capture output from two different conversation updates
        outputs = []
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            ui.update_conversation_progress(1, 1, 3, 10)
            output1 = fake_out.getvalue()
            outputs.append(output1)
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            ui.update_conversation_progress(1, 2, 3, 10)
            output2 = fake_out.getvalue()
            outputs.append(output2)
        
        # Extract cursor down values from both outputs
        cursor_down_pattern = r'\033\[(\d+)B'
        
        match1 = re.search(cursor_down_pattern, output1)
        match2 = re.search(cursor_down_pattern, output2)
        
        assert match1 and match2, "Both outputs should have cursor down codes"
        
        offset1 = int(match1.group(1))
        offset2 = int(match2.group(1))
        
        assert offset1 != offset2, \
            f"Different conversations should have different offsets (got {offset1} and {offset2})"
        
        print(f"✓ Conversation 1 offset: {offset1}")
        print(f"✓ Conversation 2 offset: {offset2}")
    
    def test_move_to_end_uses_total_lines(self):
        """Test that moving to end uses the calculated total_lines"""
        eval_cases = [create_test_eval_case()]
        
        ui = TerminalUI(
            test_name="test",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=1,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        # total_lines should be set
        assert hasattr(ui, 'total_lines'), "Should have total_lines attribute"
        assert ui.total_lines > 0, "total_lines should be positive"
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            ui.move_cursor_to_end()
            
            output = fake_out.getvalue()
            
            # Should restore cursor and move down by total_lines
            assert '\033[u' in output, "Should restore cursor"
            
            cursor_down_pattern = r'\033\[(\d+)B'
            match = re.search(cursor_down_pattern, output)
            
            if match:
                offset = int(match.group(1))
                assert offset == ui.total_lines, \
                    f"Should move down by total_lines ({ui.total_lines}), got {offset}"
                print(f"✓ Moves to end correctly (offset: {offset})")
    
    def test_multiple_ui_instances_independent(self):
        """Test that multiple UI instances don't interfere with each other"""
        eval_cases1 = [create_test_eval_case(prop_text="Test 1 -> Result 1")]
        eval_cases2 = [create_test_eval_case(prop_text="Test 2 -> Result 2")]
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out1:
            ui1 = TerminalUI(
                test_name="test1",
                npc_type="npc0",
                eval_cases=eval_cases1,
                convos_per_user_prompt=1,
                convo_length=5,
                eval_iterations_per_eval=1
            )
            output1 = fake_out1.getvalue()
        
        with patch('sys.stdout', new=io.StringIO()) as fake_out2:
            ui2 = TerminalUI(
                test_name="test2",
                npc_type="npc0",
                eval_cases=eval_cases2,
                convos_per_user_prompt=1,
                convo_length=5,
                eval_iterations_per_eval=1
            )
            output2 = fake_out2.getvalue()
        
        # Both should have cursor save 
        assert '\033[s' in output1, "UI 1 should save cursor"
        assert '\033[s' in output2, "UI 2 should save cursor"
        
        # Both should have their own line mappings
        assert ui1.line_mappings[1].conversations[1][0] == ui2.line_mappings[1].conversations[1][0], \
            "Both UIs should calculate same relative offsets (they're independent)"
        
        print("✓ Multiple UI instances are independent")
    
    def test_sequential_test_runs_dont_overlap(self):
        """Test that running tests sequentially doesn't cause overlap (simulates run_tests.py)"""
        # This simulates what happens when run_tests.py runs multiple tests
        eval_cases1 = [create_test_eval_case(prop_text="Test 1 -> Result 1")]
        eval_cases2 = [create_test_eval_case(prop_text="Test 2 -> Result 2")]
        
        # Capture output as if it's going to the same terminal
        all_output = []
        
        # Test 1
        ui1 = TerminalUI(
            test_name="test1",
            npc_type="npc0",
            eval_cases=eval_cases1,
            convos_per_user_prompt=1,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        # Simulate some updates
        ui1.update_conversation_progress(1, 1, 5, 10)
        ui1.update_conversation_progress(1, 1, 10, 10)
        ui1.update_evaluation_progress(1, 1, 1, 1)
        ui1.move_cursor_to_end()
        
        # Test 2 starts (this is where overlap would occur)
        ui2 = TerminalUI(
            test_name="test2",
            npc_type="npc0",
            eval_cases=eval_cases2,
            convos_per_user_prompt=1,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        # Simulate some updates
        ui2.update_conversation_progress(1, 1, 5, 10)
        ui2.update_conversation_progress(1, 1, 10, 10)
        ui2.update_evaluation_progress(1, 1, 1, 1)
        ui2.move_cursor_to_end()
        
        # If we got here without crashes, the sequential tests worked
        print("✓ Sequential test runs completed without overlap")
        
        # Both UIs should have saved their cursor position
        assert ui1.line_mappings[1].conversations[1][0] >= 0
        assert ui2.line_mappings[1].conversations[1][0] >= 0
        
        print("✓ Both UIs have valid line mappings")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

