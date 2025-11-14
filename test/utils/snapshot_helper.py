"""
Snapshot Testing Helpers
Utilities for capturing, comparing, and managing terminal snapshots
"""
import os
import sys
from pathlib import Path
from typing import Optional
import difflib


# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from test.utils.virtual_terminal import VirtualTerminal


class SnapshotMismatchError(AssertionError):
    """Raised when a snapshot doesn't match the expected output."""
    pass


def get_snapshot_dir() -> Path:
    """Get the directory where snapshots are stored."""
    return Path(__file__).parent.parent / "fixtures" / "terminal_snapshots"


def save_snapshot(snapshot: str, filename: str):
    """
    Save a snapshot to a file.
    
    Args:
        snapshot: The snapshot content
        filename: Name of the snapshot file
    """
    snapshot_dir = get_snapshot_dir()
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = snapshot_dir / filename
    with open(filepath, 'w') as f:
        f.write(snapshot)


def load_snapshot(filename: str) -> Optional[str]:
    """
    Load a snapshot from a file.
    
    Args:
        filename: Name of the snapshot file
        
    Returns:
        Snapshot content or None if file doesn't exist
    """
    snapshot_dir = get_snapshot_dir()
    filepath = snapshot_dir / filename
    
    if not filepath.exists():
        return None
    
    with open(filepath, 'r') as f:
        return f.read()


def compare_snapshots(actual: str, expected: str, context_lines: int = 3) -> Optional[str]:
    """
    Compare two snapshots and return a diff if they don't match.
    
    Args:
        actual: Actual snapshot content
        expected: Expected snapshot content
        context_lines: Number of context lines to show in diff
        
    Returns:
        Diff string if snapshots don't match, None if they match
    """
    if actual == expected:
        return None
    
    # Generate unified diff
    actual_lines = actual.splitlines(keepends=True)
    expected_lines = expected.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        expected_lines,
        actual_lines,
        fromfile='expected',
        tofile='actual',
        lineterm='',
        n=context_lines
    )
    
    return ''.join(diff)


def assert_snapshot_matches(actual: str, filename: str, update_snapshots: bool = False):
    """
    Assert that actual content matches a saved snapshot.
    
    Args:
        actual: Actual content to compare
        filename: Name of the snapshot file
        update_snapshots: If True, update the snapshot file instead of comparing
        
    Raises:
        SnapshotMismatchError: If snapshots don't match
    """
    if update_snapshots:
        save_snapshot(actual, filename)
        print(f"Updated snapshot: {filename}")
        return
    
    expected = load_snapshot(filename)
    
    if expected is None:
        # Snapshot doesn't exist yet - save it
        save_snapshot(actual, filename)
        print(f"Created new snapshot: {filename}")
        return
    
    diff = compare_snapshots(actual, expected)
    
    if diff is not None:
        error_msg = f"\nSnapshot mismatch: {filename}\n\n{diff}\n"
        raise SnapshotMismatchError(error_msg)


def strip_ansi_codes(text: str) -> str:
    """
    Strip ANSI escape codes from text for easier reading.
    
    Args:
        text: Text with ANSI codes
        
    Returns:
        Text without ANSI codes
    """
    import re
    # Remove ANSI escape sequences
    ansi_pattern = r'\033\[[0-9;]*[a-zA-Z]|\033\[|\0337|\0338'
    return re.sub(ansi_pattern, '', text)


def normalize_snapshot(snapshot: str) -> str:
    """
    Normalize a snapshot by removing dynamic content like timestamps.
    
    Args:
        snapshot: Raw snapshot content
        
    Returns:
        Normalized snapshot
    """
    # For now, just return as-is
    # Can add timestamp normalization etc. if needed
    return snapshot


class SnapshotContext:
    """Context manager for snapshot testing with a virtual terminal."""
    
    def __init__(self, vterm: VirtualTerminal):
        """
        Initialize snapshot context.
        
        Args:
            vterm: Virtual terminal instance
        """
        self.vterm = vterm
        self.original_stdout = None
    
    def __enter__(self):
        """Enter context - redirect stdout to virtual terminal."""
        import io
        
        class VTermWriter(io.StringIO):
            def __init__(self, vterm):
                super().__init__()
                self.vterm = vterm
            
            def write(self, text):
                self.vterm.write(text)
                return len(text)
            
            def flush(self):
                pass
        
        self.original_stdout = sys.stdout
        sys.stdout = VTermWriter(self.vterm)
        return self.vterm
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore stdout."""
        sys.stdout = self.original_stdout


def redirect_to_vterm(vterm: VirtualTerminal):
    """
    Create a context manager that redirects stdout to a virtual terminal.
    
    Args:
        vterm: Virtual terminal instance
        
    Returns:
        Context manager
    """
    return SnapshotContext(vterm)

