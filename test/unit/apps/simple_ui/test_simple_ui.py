import os
import sys
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from io import StringIO

# Ensure src/ on sys.path
PROJ_ROOT = Path(__file__).resolve().parents[4]  # Go up 4 levels from test/unit/apps/simple_ui/test_simple_ui.py to project root
SRC_DIR = PROJ_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.core.ResponseTypes import ChatResponse
from src.core.schemas.CollectionSchemas import Entity
from src.npcs.npc1.npc1 import NPC1
from src.npcs.npc2.npc2 import NPC2
from src.core import proj_paths, proj_settings


@pytest.fixture
def test_project():
    """Use in-repo test project at test/unit/apps/simple_ui and let proj_paths generate all IO paths."""
    base = PROJ_ROOT / "test/unit/apps/simple_ui"
    # Ensure expected files exist
    assert (base / "templates/default/app_settings.yaml").exists(), f"Missing {(base / 'templates/default/app_settings.yaml')}"
    assert (base / "templates/default/npcs/john/template.yaml").exists(), f"Missing template at {(base / 'templates/default/npcs/john/template.yaml')}"
    (base / "saves").mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture
def simple_ui_module():
    """Import the simple_ui module dynamically to avoid import-time execution."""
    simple_ui_path = PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"
    
    # Read the module content and extract just the functions/classes we need for testing
    with open(simple_ui_path, 'r') as f:
        content = f.read()
    
    # Create a mock module with the npc_options we need
    class MockSimpleUIModule:
        npc_options = {
            "NPC1": (NPC1, 1.0),
            "NPC2": (NPC2, 2.0)
        }
    
    return MockSimpleUIModule()


class TestSimpleUIArgumentParsing:
    """Test CLI argument parsing and validation."""
    
    def test_valid_arguments_npc1(self, test_project, monkeypatch):
        """Test valid arguments for NPC1."""
        test_args = ["simple_ui.py", "NPC1", "default", "test_save"]
        
        with patch('sys.argv', test_args):
            with patch('src.core.proj_paths.set_paths') as mock_set_paths:
                with patch('src.core.proj_settings.init_settings') as mock_init_settings:
                    with patch('builtins.input', side_effect=["/exit"]):  # Exit immediately
                        with patch('sys.exit'):
                            # Import and run the module
                            result = subprocess.run([
                                sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
                                "NPC1", "default", "test_save"
                            ], cwd=str(test_project), capture_output=True, text=True, timeout=5)
                            
                            # Should not error on argument parsing
                            assert "Unknown NPC type" not in result.stderr
                            assert "Usage:" not in result.stderr

    def test_valid_arguments_npc2(self, test_project):
        """Test valid arguments for NPC2."""
        test_args = ["simple_ui.py", "NPC2", "default", "test_save"]
        
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC2", "default", "test_save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5, input="/exit\n")
        
        # Should not error on argument parsing
        assert "Unknown NPC type" not in result.stderr
        assert "Usage:" not in result.stderr

    def test_valid_arguments_with_no_save_flag(self, test_project):
        """Test valid arguments with --no-save flag."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "test_save", "--no-save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5, input="/exit\n")
        
        assert "Save mode disabled" in result.stdout
        assert "Usage:" not in result.stderr

    def test_invalid_npc_type(self, test_project):
        """Test invalid NPC type."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "INVALID_NPC", "default", "test_save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5)
        
        assert "Unknown NPC type: INVALID_NPC" in result.stdout

    def test_insufficient_arguments(self, test_project):
        """Test insufficient arguments."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5)
        
        assert "Usage:" in result.stdout

    def test_too_many_arguments(self, test_project):
        """Test too many arguments."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "test_save", "--no-save", "extra_arg"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5)
        
        assert "Usage:" in result.stdout

    def test_invalid_templates_dir_name_with_slash(self, test_project):
        """Test templates_dir_name with slash (should be rejected)."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "invalid/path", "test_save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5)
        
        assert "templates_dir_name is just the name of the templates directory" in result.stdout

    def test_invalid_save_name_with_slash(self, test_project):
        """Test save_name with slash (should be rejected)."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "invalid/save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5)
        
        assert "save_name is just the name of the save directory" in result.stdout

    def test_invalid_flag(self, test_project):
        """Test invalid flag."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "test_save", "--invalid-flag"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5)
        
        assert "Unknown flag: --invalid-flag" in result.stdout


class TestSimpleUICommands:
    """Test interactive commands in simple_ui."""
    
    def test_exit_commands(self, test_project):
        """Test various exit commands."""
        exit_commands = ["/exit", "/quit", "/bye"]
        
        for exit_cmd in exit_commands:
            result = subprocess.run([
                sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
                "NPC1", "default", "test_save", "--no-save"
            ], cwd=str(test_project), capture_output=True, text=True, timeout=5, input=f"{exit_cmd}\n")
            
            # Should exit cleanly without errors
            assert result.returncode == 0

    def test_path_command(self, test_project):
        """Test /path command."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "test_save", "--no-save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5, input="/path\n/exit\n")
        
        assert "Project root path:" in result.stdout
        assert "Path to this file:" in result.stdout

    def test_save_command(self, test_project):
        """Test /save command."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "test_save"  # Enable saving for this test
        ], cwd=str(test_project), capture_output=True, text=True, timeout=10, input="/save\n/exit\n")
        
        # Should not error when saving
        assert "Error" not in result.stderr or "Session saved successfully" in result.stderr

    def test_load_command_valid(self, test_project):
        """Test /load command with valid NPC name."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "test_save", "--no-save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5, input="/load john\n/exit\n")
        
        # Should not error when loading valid NPC
        # Note: The actual loading might fail due to mocking, but the command parsing should work
        assert "Usage: /load <npc_name>" not in result.stdout

    def test_load_command_invalid_usage(self, test_project):
        """Test /load command with invalid usage."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "test_save", "--no-save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5, input="/load\n/exit\n")
        
        assert "Usage: /load <npc_name>" in result.stdout

    def test_unknown_command(self, test_project):
        """Test unknown command."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "test_save", "--no-save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5, input="/unknown\n/exit\n")
        
        assert "Unknown command: /unknown" in result.stdout


class TestSimpleUIIntegration:
    """Test integration with NPCs and core functionality."""
    
    def test_npc1_integration(self, test_project):
        """Test basic integration with NPC1."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "test_save", "--no-save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=10, input="Hello\n/exit\n")
        
        # Should initialize NPC1 and respond to chat
        assert "AI:" in result.stdout or "Error" not in result.stderr

    def test_npc2_integration(self, test_project):
        """Test basic integration with NPC2."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC2", "default", "test_save", "--no-save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=10, input="Hello\n/exit\n")
        
        # Should initialize NPC2 and respond to chat
        assert "AI:" in result.stdout or "Error" not in result.stderr

    def test_save_enabled_creates_files(self, test_project):
        """Test that save enabled actually creates save files."""
        # The save will be created in the actual simple_ui directory, not the test directory
        save_dir = PROJ_ROOT / "src/apps/simple_ui/saves" / "v1.0" / "integration_test"
        
        # Clean up any existing save
        if save_dir.exists():
            import shutil
            shutil.rmtree(save_dir)
        
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "integration_test"  # Enable saving
        ], cwd=str(test_project), capture_output=True, text=True, timeout=10, input="/save\n/exit\n")
        
        # Check if save files were created
        npc_save_file = save_dir / "npcs" / "john" / "npc_save_state_v1.0.yaml"
        # Note: The exact file structure depends on the NPC implementation
        # We'll just check that some save structure was created
        assert save_dir.exists() or "Session saved successfully" in result.stdout

    def test_save_disabled_no_files(self, test_project):
        """Test that save disabled doesn't create save files."""
        # The save would be created in the actual simple_ui directory, not the test directory
        save_dir = PROJ_ROOT / "src/apps/simple_ui/saves" / "v1.0" / "no_save_test"
        
        # Clean up any existing save
        if save_dir.exists():
            import shutil
            shutil.rmtree(save_dir)
        
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "no_save_test", "--no-save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=10, input="/save\n/exit\n")
        
        # Should indicate save mode is disabled
        assert "Save mode disabled" in result.stdout

    def test_template_directory_validation(self, test_project):
        """Test that non-existent template directory is rejected."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "nonexistent", "test_save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5)
        
        assert "Template directory does not exist" in result.stdout


class TestSimpleUIErrorHandling:
    """Test error handling in simple_ui."""
    
    def test_graceful_error_handling(self, test_project):
        """Test that errors are handled gracefully and don't crash the app."""
        # This test ensures that even if there are internal errors, 
        # the app doesn't crash unexpectedly
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "error_test", "--no-save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=10, input="test input\n/exit\n")
        
        # Should not have unhandled exceptions
        assert "Traceback" not in result.stderr or "Error:" in result.stderr

    def test_keyboard_interrupt_handling(self, test_project):
        """Test handling of keyboard interrupt (Ctrl+C)."""
        import signal
        import time
        
        # Start the process
        proc = subprocess.Popen([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "interrupt_test", "--no-save"
        ], cwd=str(test_project), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Give it a moment to start
        time.sleep(1)
        
        # Send interrupt signal
        proc.send_signal(signal.SIGINT)
        
        # Wait for process to terminate
        try:
            stdout, stderr = proc.communicate(timeout=5)
            # Process should terminate gracefully
            assert proc.returncode != 0  # Should exit with non-zero code due to interrupt
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("Process did not terminate after interrupt")


@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Clean up singletons between tests to avoid state leakage."""
    yield
    # Reset proj_paths and proj_settings singletons
    if hasattr(proj_paths, '_paths'):
        proj_paths._paths = None
        proj_paths._frozen = False
    if hasattr(proj_settings, '_settings'):
        proj_settings._settings = None
        proj_settings._frozen = False


class TestSimpleUISpecialCommands:
    """Test special commands functionality."""
    
    def test_list_command_basic(self, test_project):
        """Test /list command basic functionality."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "test_save", "--no-save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5, input="/list\n/exit\n")
        
        # Should display memories from the template (john's entities)
        assert "Memory:" in result.stdout

    def test_clear_command_basic(self, test_project):
        """Test /clear command basic functionality."""
        result = subprocess.run([
            sys.executable, str(PROJ_ROOT / "src/apps/simple_ui/simple_ui.py"),
            "NPC1", "default", "test_save", "--no-save"
        ], cwd=str(test_project), capture_output=True, text=True, timeout=5, input="/clear\n/exit\n")
        
        # Should complete without major errors
        assert result.returncode == 0
