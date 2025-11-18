"""
CSV-style table terminal UI for parallel evaluation progress tracking.
Displays progress bars during execution and results after completion.
"""

import threading
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class CellProgress:
    """Tracks progress for a single test case × NPC combination."""
    completed_units: int = 0
    total_units: int = 0
    status: str = "pending"  # "pending", "convo", "eval", "saving", "done"
    passes: int = 0  # For final results
    total_evals: int = 0  # For final results
    cost_usd: float = 0.0  # Cost in USD for this cell


class TableTerminalUI:
    """
    Thread-safe CSV-style table UI for displaying evaluation progress.
    
    Table layout:
                              ,npc0        ,npc1        ,npc2
    test_name_1 case 1        ,convo [▉ ]  ,1/3         ,saving [██]
    test_name_1 case 2        ,eval  [█▋]  ,0/2         ,1/2
    test_name_2               ,convo [▍ ]  ,4/4         ,eval [█▋]
    total                     ,pending     ,5/9         ,pending
    """
    
    def __init__(self, progress_bar_width: int = 3):
        """
        Initialize TableTerminalUI.
        
        Args:
            progress_bar_width: Number of characters for progress bar (default 3).
                               Total positions = progress_bar_width × 8
        """
        self.lock = threading.Lock()
        self.cells: Dict[Tuple[str, str], CellProgress] = {}  # (test_case_key, npc_type) -> progress
        self.test_order: List[str] = []  # Ordered test case keys
        self.npc_types_used: set = set()  # Track which NPC types are actually used
        self.col_width = 20  # Fixed column width for NPC columns
        self.cost_col_width = 12  # Fixed width for cost column
        self.row_name_width = 30  # Fixed width for row names
        self.status_width = 7  # Fixed width for status text ("convo  ", "eval   ", "saving ")
        self.progress_bar_width = progress_bar_width  # Number of characters in progress bar
        self.progress_bar_positions = progress_bar_width * 8  # Total positions (8 per character)
        self.first_render = True  # Track if this is the first render
        self.num_lines = 0  # Track number of lines in the table
    
    def register_test(self, test_name: str, case_idx: int, total_cases: int, npc_type: str, 
                     convos_per_user_prompt: int, convo_length: int, eval_iterations_per_eval: int):
        """
        Register a test case for a specific NPC type.
        Calculates total units and initializes cell.
        
        Units calculation:
        - Conversation units: convos_per_user_prompt × convo_length × 2
        - Evaluation units: convos_per_user_prompt × eval_iterations_per_eval
        - Total: conversation_units + evaluation_units
        """
        with self.lock:
            # Calculate total units
            conversation_units = convos_per_user_prompt * convo_length * 2
            evaluation_units = convos_per_user_prompt * eval_iterations_per_eval
            total_units = conversation_units + evaluation_units
            
            # Track which NPC types are actually used
            self.npc_types_used.add(npc_type)
            
            # Create test case key
            if total_cases == 1:
                test_case_key = test_name
            else:
                test_case_key = f"{test_name}_case_{case_idx}"
            
            # Add to test order if not already there
            if test_case_key not in self.test_order:
                self.test_order.append(test_case_key)
            
            # Initialize cell
            cell_key = (test_case_key, npc_type)
            self.cells[cell_key] = CellProgress(
                completed_units=0,
                total_units=total_units,
                status="pending",
                passes=0,
                total_evals=0
            )
    
    def update_progress(self, test_name: str, case_idx: int, total_cases: int, npc_type: str, 
                       completed_units: int, status: str):
        """
        Update progress for a specific cell.
        
        Args:
            test_name: Test configuration name
            case_idx: Case index (1-based)
            total_cases: Total number of cases in this test
            npc_type: NPC type (npc0, npc1, npc2)
            completed_units: Number of units completed
            status: Current status ("convo", "eval", "saving")
        """
        with self.lock:
            # Create test case key
            if total_cases == 1:
                test_case_key = test_name
            else:
                test_case_key = f"{test_name}_case_{case_idx}"
            
            cell_key = (test_case_key, npc_type)
            if cell_key in self.cells:
                self.cells[cell_key].completed_units = completed_units
                self.cells[cell_key].status = status
                self._render()
    
    def set_results(self, test_name: str, case_idx: int, total_cases: int, npc_type: str, 
                   passes: int, total_evals: int, cost_usd: float = 0.0):
        """
        Set final results for a cell after evaluation completes.
        
        Args:
            test_name: Test configuration name
            case_idx: Case index (1-based)
            total_cases: Total number of cases in this test
            npc_type: NPC type (npc0, npc1, npc2)
            passes: Number of passing evaluations
            total_evals: Total number of evaluations
            cost_usd: Total cost in USD for this cell
        """
        with self.lock:
            # Create test case key
            if total_cases == 1:
                test_case_key = test_name
            else:
                test_case_key = f"{test_name}_case_{case_idx}"
            
            cell_key = (test_case_key, npc_type)
            if cell_key in self.cells:
                self.cells[cell_key].status = "done"
                self.cells[cell_key].passes = passes
                self.cells[cell_key].total_evals = total_evals
                self.cells[cell_key].cost_usd = cost_usd
                self._render()
    
    def _render(self):
        """Render the entire table by clearing screen and redrawing."""
        # On subsequent renders, move cursor up and clear from there
        if not self.first_render and self.num_lines > 0:
            # Move cursor up to start of table
            print(f'\033[{self.num_lines}A', end='', flush=True)
            # Clear from cursor to end of screen
            print('\033[J', end='', flush=True)
        self.first_render = False
        
        # Get sorted NPC types
        npc_order = sorted(self.npc_types_used)
        
        # Build horizontal separator (includes cost column)
        separator = "+" + "-" * (self.row_name_width + 2)
        for _ in npc_order:
            separator += "+" + "-" * (self.col_width + 2)
        separator += "+" + "-" * (self.cost_col_width + 2) + "+"  # Add cost column
        
        lines = []
        
        # Top border
        lines.append(separator)
        
        # Build header row (includes cost column header)
        header = "| " + "".ljust(self.row_name_width) + " |"
        for npc_type in npc_order:
            header += " " + npc_type.ljust(self.col_width) + " |"
        header += " " + "cost".ljust(self.cost_col_width) + " |"  # Add cost column header
        lines.append(header)
        
        # Header separator
        lines.append(separator)
        
        # Build data rows (includes cost column)
        for test_case_key in self.test_order:
            row = "| " + self._format_test_case_name(test_case_key).ljust(self.row_name_width) + " |"
            row_cost = 0.0
            all_done = True
            
            for npc_type in npc_order:
                cell_key = (test_case_key, npc_type)
                cell = self.cells.get(cell_key)
                cell_content = self._format_cell(cell)
                row += " " + cell_content.ljust(self.col_width) + " |"
                
                # Track if all cells in row are done and accumulate cost
                if cell and cell.status == "done":
                    row_cost += cell.cost_usd
                else:
                    all_done = False
            
            # Add cost cell for this row (only show if all cells done)
            if all_done:
                cost_str = self._format_cost(row_cost)
            else:
                cost_str = "pending"
            row += " " + cost_str.ljust(self.cost_col_width) + " |"
            
            lines.append(row)
        
        # Row separator before total and cost rows
        lines.append(separator)
        
        # Build total row (shows pass/fail totals per NPC)
        total_row = self._calculate_total_row(npc_order)
        lines.append(total_row)
        
        # Build cost row (shows cost totals per NPC column)
        cost_row = self._calculate_cost_row(npc_order)
        lines.append(cost_row)
        
        # Bottom border
        lines.append(separator)
        
        # Update line count for next render
        self.num_lines = len(lines)
        
        # Print table
        table_string = "\n".join(lines)
        print(table_string, flush=True)
    
    def _format_cell(self, cell: CellProgress) -> str:
        """
        Format cell content based on status.
        
        Returns:
            - During execution: "convo   [▉  ]", "eval    [█▋ ]", "saving  [███]"
            - After completion: "5/9" (passes/total_evals)
            - Pending: "pending"
        """
        if cell is None:
            return "pending"
        
        if cell.status == "done":
            return f"{cell.passes}/{cell.total_evals}"
        elif cell.status == "pending":
            return "pending"
        elif cell.status in ["convo", "eval", "saving"]:
            progress_bar = self._calculate_progress_bar(cell.completed_units, cell.total_units)
            # Use fixed-width status text (7 chars) so bar doesn't move
            status_text = cell.status.ljust(self.status_width)
            return f"{status_text}{progress_bar}"
        else:
            return "unknown"
    
    def _calculate_progress_bar(self, completed: int, total: int) -> str:
        """
        Generate unicode progress bar with configurable width.
        
        Args:
            completed: Number of completed units
            total: Total number of units
            
        Returns:
            Progress bar string like "[▌  ]" or "[███]"
        """
        if total == 0:
            ratio = 0
        else:
            ratio = completed / total
        
        # Round to nearest 1/positions
        position = round(ratio * self.progress_bar_positions)
        position = min(self.progress_bar_positions, max(0, position))
        
        # Each character has 8 states
        chars = ' ▏▎▍▌▋▊▉█'
        
        # Build the bar character by character
        bar_chars = []
        for i in range(self.progress_bar_width):
            char_position = min(8, max(0, position - (i * 8)))
            bar_chars.append(chars[char_position])
        
        return f"[{''.join(bar_chars)}]"
    
    def _format_test_case_name(self, test_case_key: str) -> str:
        """
        Format test case name for row display.
        
        Handles truncation if name exceeds max width:
        - If test has multiple cases: "<test_name> case N" (truncate beginning of test_name if needed)
        - If test has single case: "<test_name>" (truncate beginning if needed)
        
        Args:
            test_case_key: Key like "test_name" or "test_name_case_2"
            
        Returns:
            Formatted and potentially truncated name
        """
        max_width = self.row_name_width
        
        # Check if this is a multi-case test
        if "_case_" in test_case_key:
            parts = test_case_key.rsplit("_case_", 1)
            test_name = parts[0]
            case_num = parts[1]
            
            # Format: "<test_name> case N"
            suffix = f" case {case_num}"
            available_for_name = max_width - len(suffix)
            
            if len(test_name) > available_for_name:
                # Truncate beginning of test name, keep end
                truncated = "..." + test_name[-(available_for_name - 3):]
                name = truncated + suffix
            else:
                name = test_name + suffix
        else:
            # Single case - just use test name
            name = test_case_key
            if len(name) > max_width:
                # Truncate beginning, keep end (most distinctive part)
                name = "..." + name[-(max_width - 3):]
        
        return name
    
    def _format_row_name(self, test_name: str, case_idx: int, total_cases: int) -> str:
        """Format row name for display (kept for compatibility, delegates to _format_test_case_name)."""
        if total_cases == 1:
            test_case_key = test_name
        else:
            test_case_key = f"{test_name}_case_{case_idx}"
        return self._format_test_case_name(test_case_key)
    
    def _calculate_total_row(self, npc_order: List[str]) -> str:
        """
        Calculate and format the total row (shows pass/fail totals).
        
        For each NPC:
        - If all cells done: show "passes/total" summed across all test cases
        - If any cell pending/in-progress: show "pending"
        """
        row = "| " + "total".ljust(self.row_name_width) + " |"
        grand_total_cost = 0.0
        
        for npc_type in npc_order:
            total_passes = 0
            total_evals = 0
            all_done = True
            
            for test_case_key in self.test_order:
                cell_key = (test_case_key, npc_type)
                cell = self.cells.get(cell_key)
                
                if cell is None or cell.status != "done":
                    all_done = False
                    break
                
                total_passes += cell.passes
                total_evals += cell.total_evals
            
            if all_done and total_evals > 0:
                cell_content = f"{total_passes}/{total_evals}"
            else:
                cell_content = "pending"
            
            row += " " + cell_content.ljust(self.col_width) + " |"
        
        # Add empty cost cell for total row
        row += " " + "".ljust(self.cost_col_width) + " |"
        
        return row
    
    def _calculate_cost_row(self, npc_order: List[str]) -> str:
        """
        Calculate and format the cost row (shows cost totals per NPC column).
        
        For each NPC column:
        - If all cells done: show total cost
        - Otherwise: show "pending"
        """
        row = "| " + "cost".ljust(self.row_name_width) + " |"
        grand_total_cost = 0.0
        all_columns_done = True
        
        for npc_type in npc_order:
            column_cost = 0.0
            column_done = True
            
            for test_case_key in self.test_order:
                cell_key = (test_case_key, npc_type)
                cell = self.cells.get(cell_key)
                
                if cell is None or cell.status != "done":
                    column_done = False
                    all_columns_done = False
                    break
                
                column_cost += cell.cost_usd
            
            if column_done:
                cell_content = self._format_cost(column_cost)
                grand_total_cost += column_cost
            else:
                cell_content = "pending"
            
            row += " " + cell_content.ljust(self.col_width) + " |"
        
        # Add grand total cost (bottom-right cell)
        if all_columns_done:
            grand_total_str = self._format_cost(grand_total_cost)
        else:
            grand_total_str = "pending"
        row += " " + grand_total_str.ljust(self.cost_col_width) + " |"
        
        return row
    
    def _format_cost(self, cost_usd: float) -> str:
        """
        Format cost in USD with 2 significant figures to the right of decimal point.
        
        Examples: $435.34, $0.043, $0.00012, $1234.56
        
        Args:
            cost_usd: Cost in USD
            
        Returns:
            Formatted cost string
        """
        if cost_usd == 0.0:
            return "$0.00"
        
        # For costs >= $1, use 2 decimal places
        if cost_usd >= 1.0:
            return f"${cost_usd:.2f}"
        
        # For costs < $1, find how many decimal places we need for 2 sig figs
        # Count leading zeros after decimal point
        import math
        if cost_usd > 0:
            # Number of decimal places needed = leading zeros + 2 sig figs
            decimal_places = -math.floor(math.log10(cost_usd)) + 1
            return f"${cost_usd:.{decimal_places}f}"
        
        return "$0.00"
    
    def render_initial(self):
        """Render the initial table state after all tests are registered."""
        with self.lock:
            # Ensure we only render initial once
            if self.first_render:
                self._render()
    
    def get_table_string(self) -> str:
        """
        Get the current table as a string (for saving to file).
        
        Returns:
            The ASCII table as a string
        """
        with self.lock:
            # Get sorted NPC types
            npc_order = sorted(self.npc_types_used)
            
            # Build horizontal separator (includes cost column)
            separator = "+" + "-" * (self.row_name_width + 2)
            for _ in npc_order:
                separator += "+" + "-" * (self.col_width + 2)
            separator += "+" + "-" * (self.cost_col_width + 2) + "+"  # Add cost column
            
            lines = []
            
            # Top border
            lines.append(separator)
            
            # Build header row (includes cost column header)
            header = "| " + "".ljust(self.row_name_width) + " |"
            for npc_type in npc_order:
                header += " " + npc_type.ljust(self.col_width) + " |"
            header += " " + "cost".ljust(self.cost_col_width) + " |"  # Add cost column header
            lines.append(header)
            
            # Header separator
            lines.append(separator)
            
            # Build data rows (includes cost column)
            for test_case_key in self.test_order:
                row = "| " + self._format_test_case_name(test_case_key).ljust(self.row_name_width) + " |"
                row_cost = 0.0
                all_done = True
                
                for npc_type in npc_order:
                    cell_key = (test_case_key, npc_type)
                    cell = self.cells.get(cell_key)
                    cell_content = self._format_cell(cell)
                    row += " " + cell_content.ljust(self.col_width) + " |"
                    
                    # Track if all cells in row are done and accumulate cost
                    if cell and cell.status == "done":
                        row_cost += cell.cost_usd
                    else:
                        all_done = False
                
                # Add cost cell for this row (only show if all cells done)
                if all_done:
                    cost_str = self._format_cost(row_cost)
                else:
                    cost_str = "pending"
                row += " " + cost_str.ljust(self.cost_col_width) + " |"
                
                lines.append(row)
            
            # Row separator before total and cost rows
            lines.append(separator)
            
            # Build total row (shows pass/fail totals per NPC)
            total_row = self._calculate_total_row(npc_order)
            lines.append(total_row)
            
            # Build cost row (shows cost totals per NPC column)
            cost_row = self._calculate_cost_row(npc_order)
            lines.append(cost_row)
            
            # Bottom border
            lines.append(separator)
            
            return "\n".join(lines)
    
    def move_cursor_to_end(self):
        """Move cursor to end of output (for final messages)."""
        print()  # Just add a newline

