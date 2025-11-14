"""
Virtual Terminal for Snapshot Testing
Interprets ANSI escape codes and maintains a terminal grid for visual testing
"""
import re
from typing import Tuple, List


class VirtualTerminal:
    """
    A virtual terminal that interprets ANSI escape codes and maintains
    a character grid representation of what would be displayed.
    """
    
    def __init__(self, rows: int = 100, cols: int = 80):
        """
        Initialize virtual terminal.
        
        Args:
            rows: Number of terminal rows
            cols: Number of terminal columns
        """
        self.rows = rows
        self.cols = cols
        self.grid = [[' ' for _ in range(cols)] for _ in range(rows)]
        self.cursor_row = 0
        self.cursor_col = 0
        self.saved_cursor = (0, 0)
        
        # Track which rows have content
        self.max_row_used = 0
    
    def write(self, text: str):
        """
        Write text to the virtual terminal, interpreting ANSI codes.
        
        Args:
            text: Text with ANSI codes to write
        """
        i = 0
        while i < len(text):
            # Check for ANSI escape sequence
            if text[i:i+2] == '\033[' or text[i:i+1] == '\033':
                # Find the end of the escape sequence
                end = i + 1
                while end < len(text) and not text[end].isalpha():
                    end += 1
                
                if end < len(text):
                    end += 1  # Include the letter
                    escape_seq = text[i:end]
                    self._handle_escape(escape_seq)
                    i = end
                    continue
            
            # Regular character
            char = text[i]
            
            if char == '\n':
                self.cursor_row += 1
                self.cursor_col = 0
            elif char == '\r':
                self.cursor_col = 0
            elif char == '\t':
                # Tab to next multiple of 8
                self.cursor_col = ((self.cursor_col // 8) + 1) * 8
            else:
                # Write character to grid
                if self.cursor_row < self.rows and self.cursor_col < self.cols:
                    self.grid[self.cursor_row][self.cursor_col] = char
                    self.max_row_used = max(self.max_row_used, self.cursor_row)
                self.cursor_col += 1
            
            i += 1
    
    def _handle_escape(self, escape_seq: str):
        """
        Handle an ANSI escape sequence.
        
        Args:
            escape_seq: The escape sequence to handle
        """
        # Cursor save: \033[s or \0337
        if escape_seq in ['\033[s', '\0337']:
            self.saved_cursor = (self.cursor_row, self.cursor_col)
            return
        
        # Cursor restore: \033[u or \0338
        if escape_seq in ['\033[u', '\0338']:
            self.cursor_row, self.cursor_col = self.saved_cursor
            return
        
        # Clear line: \033[K or \033[0K
        if escape_seq in ['\033[K', '\033[0K']:
            # Clear from cursor to end of line
            if self.cursor_row < self.rows:
                for col in range(self.cursor_col, self.cols):
                    self.grid[self.cursor_row][col] = ' '
            return
        
        # Clear from beginning of line: \033[1K
        if escape_seq == '\033[1K':
            if self.cursor_row < self.rows:
                for col in range(0, self.cursor_col + 1):
                    self.grid[self.cursor_row][col] = ' '
            return
        
        # Clear entire line: \033[2K
        if escape_seq == '\033[2K':
            if self.cursor_row < self.rows:
                for col in range(self.cols):
                    self.grid[self.cursor_row][col] = ' '
            return
        
        # Cursor movement
        # Cursor up: \033[<n>A
        match = re.match(r'\033\[(\d+)A', escape_seq)
        if match:
            n = int(match.group(1))
            self.cursor_row = max(0, self.cursor_row - n)
            return
        
        # Cursor down: \033[<n>B
        match = re.match(r'\033\[(\d+)B', escape_seq)
        if match:
            n = int(match.group(1))
            self.cursor_row = min(self.rows - 1, self.cursor_row + n)
            return
        
        # Cursor forward: \033[<n>C
        match = re.match(r'\033\[(\d+)C', escape_seq)
        if match:
            n = int(match.group(1))
            self.cursor_col = min(self.cols - 1, self.cursor_col + n)
            return
        
        # Cursor backward: \033[<n>D
        match = re.match(r'\033\[(\d+)D', escape_seq)
        if match:
            n = int(match.group(1))
            self.cursor_col = max(0, self.cursor_col - n)
            return
        
        # Cursor position: \033[<row>;<col>H or \033[<row>;<col>f
        match = re.match(r'\033\[(\d+);(\d+)[Hf]', escape_seq)
        if match:
            row = int(match.group(1)) - 1  # ANSI is 1-indexed
            col = int(match.group(2)) - 1
            self.cursor_row = min(self.rows - 1, max(0, row))
            self.cursor_col = min(self.cols - 1, max(0, col))
            return
        
        # Move to column: \033[<col>G
        match = re.match(r'\033\[(\d+)G', escape_seq)
        if match:
            col = int(match.group(1)) - 1  # ANSI is 1-indexed
            self.cursor_col = min(self.cols - 1, max(0, col))
            return
        
        # Color codes and other formatting - ignore for visual testing
        if re.match(r'\033\[\d*(;\d+)*m', escape_seq):
            return
        
        # Ignore other escape sequences
        # (This includes bold, reset, etc. which don't affect positioning)
    
    def get_snapshot(self, strip_trailing_spaces: bool = True) -> str:
        """
        Get the current terminal state as a string.
        
        Args:
            strip_trailing_spaces: Whether to strip trailing spaces from each line
            
        Returns:
            String representation of terminal grid
        """
        lines = []
        for row in range(self.max_row_used + 1):
            line = ''.join(self.grid[row])
            if strip_trailing_spaces:
                line = line.rstrip()
            lines.append(line)
        
        # Remove trailing empty lines
        while lines and not lines[-1]:
            lines.pop()
        
        return '\n'.join(lines)
    
    def get_cursor_position(self) -> Tuple[int, int]:
        """Get current cursor position (row, col)."""
        return (self.cursor_row, self.cursor_col)
    
    def clear(self):
        """Clear the entire terminal."""
        self.grid = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.cursor_row = 0
        self.cursor_col = 0
        self.max_row_used = 0
    
    def get_line(self, row: int) -> str:
        """
        Get a specific line from the terminal.
        
        Args:
            row: Row number (0-indexed)
            
        Returns:
            Line content
        """
        if 0 <= row < self.rows:
            return ''.join(self.grid[row]).rstrip()
        return ""
    
    def __str__(self) -> str:
        """String representation (same as get_snapshot)."""
        return self.get_snapshot()

