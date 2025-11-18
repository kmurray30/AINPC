"""
Unit tests for TableTerminalUI with comprehensive mocked threading control
"""
import pytest
import threading
import time
from io import StringIO
from contextlib import redirect_stdout
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / "../../../.."))

from src.conversation_eval.core.TableTerminalUI import TableTerminalUI, CellProgress


class TestProgressBarCalculation:
    """Test unicode progress bar generation"""
    
    def test_empty_bar(self):
        """Test 0% progress"""
        ui = TableTerminalUI()
        bar = ui._calculate_progress_bar(0, 26)
        assert bar == "[   ]", f"Expected '[   ]' but got '{bar}'"
    
    def test_half_bar(self):
        """Test 50% progress (12/24 positions)"""
        ui = TableTerminalUI()
        bar = ui._calculate_progress_bar(13, 26)  # 50%
        assert bar == "[█▌ ]", f"Expected '[█▌ ]' but got '{bar}'"
    
    def test_quarter_bar(self):
        """Test 25% progress (6/24 positions)"""
        ui = TableTerminalUI()
        bar = ui._calculate_progress_bar(7, 26)  # ~27% -> rounds to 6/24
        assert bar == "[▊  ]", f"Expected '[▊  ]' but got '{bar}'"
    
    def test_seven_twentyfourths_bar(self):
        """Test 7/24 progress"""
        ui = TableTerminalUI()
        bar = ui._calculate_progress_bar(7, 24)
        assert bar == "[▉  ]", f"Expected '[▉  ]' but got '{bar}'"
    
    def test_full_bar(self):
        """Test 100% progress"""
        ui = TableTerminalUI()
        bar = ui._calculate_progress_bar(26, 26)
        assert bar == "[███]", f"Expected '[███]' but got '{bar}'"
    
    def test_three_quarters_bar(self):
        """Test 75% progress (18/24 positions)"""
        ui = TableTerminalUI()
        bar = ui._calculate_progress_bar(20, 26)  # ~77% -> rounds to 18/24
        assert bar == "[██▎]", f"Expected '[██▎]' but got '{bar}'"


class TestRowNameFormatting:
    """Test row name truncation logic"""
    
    def test_single_case_short_name(self):
        """Test single case with short name"""
        ui = TableTerminalUI()
        name = ui._format_test_case_name("test_name")
        assert "test_name" in name
        assert name.strip() == "test_name"
    
    def test_single_case_long_name(self):
        """Test single case with very long name"""
        ui = TableTerminalUI()
        long_name = "this_is_a_very_long_test_name_that_exceeds_limit"
        name = ui._format_test_case_name(long_name)
        assert len(name) == ui.row_name_width
        # Should truncate beginning and add ellipsis
        assert "..." in name
        assert "exceeds_limit" in name  # Should keep the end
    
    def test_multi_case_format(self):
        """Test multiple case format"""
        ui = TableTerminalUI()
        name = ui._format_test_case_name("test_name_case_2")
        assert " case 2" in name  # case number at end
        assert "test_name" in name
    
    def test_multi_case_long_name_truncation(self):
        """Test multi-case with long name truncates test name"""
        ui = TableTerminalUI()
        long_name = "very_long_test_name_here_case_3"
        name = ui._format_test_case_name(long_name)
        assert " case 3" in name  # case number at end
        # Verify it doesn't exceed max width when padded
        assert len(name) <= ui.row_name_width
        # Should have ellipsis at beginning if truncated
        if len("very_long_test_name_here case 3") > ui.row_name_width:
            assert "..." in name


class TestCellFormatting:
    """Test cell content formatting"""
    
    def test_pending_cell(self):
        """Test pending status"""
        ui = TableTerminalUI()
        cell = CellProgress(status="pending")
        formatted = ui._format_cell(cell)
        assert formatted == "pending"
    
    def test_convo_in_progress(self):
        """Test conversation in progress"""
        ui = TableTerminalUI()
        cell = CellProgress(completed_units=7, total_units=26, status="convo")
        formatted = ui._format_cell(cell)
        assert "convo" in formatted
        assert "[" in formatted and "]" in formatted
    
    def test_eval_in_progress(self):
        """Test evaluation in progress"""
        ui = TableTerminalUI()
        cell = CellProgress(completed_units=22, total_units=26, status="eval")
        formatted = ui._format_cell(cell)
        assert "eval" in formatted
        assert "[" in formatted and "]" in formatted
    
    def test_saving_status(self):
        """Test saving status (should show full bar)"""
        ui = TableTerminalUI()
        cell = CellProgress(completed_units=26, total_units=26, status="saving")
        formatted = ui._format_cell(cell)
        assert "saving" in formatted
        assert "[███]" in formatted
    
    def test_done_with_results(self):
        """Test done status shows results"""
        ui = TableTerminalUI()
        cell = CellProgress(status="done", passes=5, total_evals=9)
        formatted = ui._format_cell(cell)
        assert formatted == "5/9"
    
    def test_none_cell(self):
        """Test formatting None cell"""
        ui = TableTerminalUI()
        formatted = ui._format_cell(None)
        assert formatted == "pending"


class TestSingleTestSingleNPC:
    """Test single test with single NPC"""
    
    def test_register_and_initial_render(self):
        """Test registration and initial table render"""
        ui = TableTerminalUI()
        
        # Capture output
        output = StringIO()
        with redirect_stdout(output):
            ui.register_test(
                test_name="test1",
                case_idx=1,
                total_cases=1,
                npc_type="npc0",
                convos_per_user_prompt=2,
                convo_length=5,
                eval_iterations_per_eval=3
            )
            ui.render_initial()
        
        result = output.getvalue()
        
        # Verify table structure
        assert "npc0" in result
        assert "test1" in result
        assert "pending" in result
        assert "total" in result
    
    def test_progress_updates(self):
        """Test progress updates through conversation and evaluation"""
        ui = TableTerminalUI()
        
        # Register
        ui.register_test(
            test_name="test1",
            case_idx=1,
            total_cases=1,
            npc_type="npc0",
            convos_per_user_prompt=2,
            convo_length=5,
            eval_iterations_per_eval=3
        )
        
        # Update progress to mid-conversation
        output = StringIO()
        with redirect_stdout(output):
            ui.update_progress("test1", 1, 1, "npc0", 10, "convo")
        
        result = output.getvalue()
        assert "convo" in result
        assert "[" in result
        
        # Update to evaluation
        output = StringIO()
        with redirect_stdout(output):
            ui.update_progress("test1", 1, 1, "npc0", 22, "eval")
        
        result = output.getvalue()
        assert "eval" in result
        
        # Set final results
        output = StringIO()
        with redirect_stdout(output):
            ui.set_results("test1", 1, 1, "npc0", 5, 6)
        
        result = output.getvalue()
        assert "5/6" in result


class TestMultipleTestsMultipleNPCs:
    """Test multiple tests with multiple NPCs"""
    
    def test_grid_layout(self):
        """Test that multiple tests and NPCs create proper grid"""
        ui = TableTerminalUI()
        
        # Register 2 tests × 2 NPCs
        for test_name in ["test1", "test2"]:
            for npc_type in ["npc0", "npc1"]:
                ui.register_test(
                    test_name=test_name,
                    case_idx=1,
                    total_cases=1,
                    npc_type=npc_type,
                    convos_per_user_prompt=2,
                    convo_length=5,
                    eval_iterations_per_eval=3
                )
        
        output = StringIO()
        with redirect_stdout(output):
            ui.render_initial()
        
        result = output.getvalue()
        
        # Verify all elements present
        assert "npc0" in result
        assert "npc1" in result
        assert "test1" in result
        assert "test2" in result
        assert "total" in result
        
        # Count pending states
        assert result.count("pending") >= 4  # At least 4 cells pending


class TestTotalRowCalculation:
    """Test total row aggregation"""
    
    def test_total_pending_when_incomplete(self):
        """Test total shows pending when any test incomplete"""
        ui = TableTerminalUI()
        
        ui.register_test("test1", 1, 1, "npc0", 2, 5, 3)
        ui.register_test("test2", 1, 1, "npc0", 2, 5, 3)
        
        # Complete only test1
        ui.set_results("test1", 1, 1, "npc0", 5, 6)
        
        output = StringIO()
        with redirect_stdout(output):
            ui._render()
        
        result = output.getvalue()
        lines = result.strip().split("\n")
        # Find the total line (now starts with "| total")
        total_line = [l for l in lines if "total" in l and l.startswith("|")][0]
        
        # Should still show pending since test2 not done
        assert "pending" in total_line
    
    def test_total_aggregates_when_all_complete(self):
        """Test total aggregates results when all complete"""
        ui = TableTerminalUI()
        
        ui.register_test("test1", 1, 1, "npc0", 2, 5, 3)
        ui.register_test("test2", 1, 1, "npc0", 2, 5, 3)
        
        # Complete both tests
        ui.set_results("test1", 1, 1, "npc0", 5, 6)
        ui.set_results("test2", 1, 1, "npc0", 3, 6)
        
        output = StringIO()
        with redirect_stdout(output):
            ui._render()
        
        result = output.getvalue()
        lines = result.strip().split("\n")
        # Find the total line (now starts with "| total")
        total_line = [l for l in lines if "total" in l and l.startswith("|")][0]
        
        # Should show 8/12 (5+3 / 6+6)
        assert "8/12" in total_line


class TestConcurrentUpdates:
    """Test thread-safe concurrent updates"""
    
    def test_concurrent_updates_no_corruption(self):
        """Test that concurrent updates don't corrupt state"""
        ui = TableTerminalUI()
        
        # Register multiple tests
        for test_idx in range(1, 4):
            for npc_type in ["npc0", "npc1"]:
                ui.register_test(
                    test_name=f"test{test_idx}",
                    case_idx=1,
                    total_cases=1,
                    npc_type=npc_type,
                    convos_per_user_prompt=2,
                    convo_length=5,
                    eval_iterations_per_eval=3
                )
        
        # Simulate concurrent updates
        errors = []
        
        def update_progress(test_name, npc_type):
            try:
                for i in range(1, 27):
                    ui.update_progress(test_name, 1, 1, npc_type, i, "convo" if i < 20 else "eval")
                    time.sleep(0.001)  # Small delay
                ui.set_results(test_name, 1, 1, npc_type, 5, 6)
            except Exception as e:
                errors.append(e)
        
        # Start threads
        threads = []
        for test_idx in range(1, 4):
            for npc_type in ["npc0", "npc1"]:
                t = threading.Thread(target=update_progress, args=(f"test{test_idx}", npc_type))
                threads.append(t)
                t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify final state is correct
        for test_idx in range(1, 4):
            for npc_type in ["npc0", "npc1"]:
                cell_key = (f"test{test_idx}", npc_type)
                assert cell_key in ui.cells
                assert ui.cells[cell_key].status == "done"
                assert ui.cells[cell_key].passes == 5
                assert ui.cells[cell_key].total_evals == 6


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_zero_units(self):
        """Test handling of zero total units"""
        ui = TableTerminalUI()
        bar = ui._calculate_progress_bar(0, 0)
        assert bar == "[   ]"  # Should handle gracefully
    
    def test_unregistered_test_update(self):
        """Test updating unregistered test (should not crash)"""
        ui = TableTerminalUI()
        
        # This should not crash, just not do anything  
        try:
            output = StringIO()
            with redirect_stdout(output):
                ui.update_progress("nonexistent", 1, 1, "npc0", 5, "convo")
            # Should complete without error
        except Exception as e:
            pytest.fail(f"Should not crash on unregistered test update: {e}")
    
    def test_multiple_cases_same_test(self):
        """Test multiple cases for same test"""
        ui = TableTerminalUI()
        
        # Register 2 cases for test1
        ui.register_test("test1", 1, 2, "npc0", 2, 5, 3)
        ui.register_test("test1", 2, 2, "npc0", 2, 5, 3)
        
        output = StringIO()
        with redirect_stdout(output):
            ui.render_initial()
        
        result = output.getvalue()
        
        # Should have two rows for test1
        lines = [l for l in result.split("\n") if "test1" in l]
        assert len(lines) == 2, f"Expected 2 lines with test1, got {len(lines)}"
        
        # Should show case numbers
        assert "1 " in result or "_case_1" in result
        assert "2 " in result or "_case_2" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

