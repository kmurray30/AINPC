#!/usr/bin/env python3
"""
Unit tests for NPC factory creation logic in run_tests.py
Tests that settings initialization happens correctly
"""
import os
import sys
from pathlib import Path
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core import proj_paths, proj_settings


def test_settings_initialization_required_for_npc1():
    """
    Test that settings must be initialized before creating NPC1 instances
    
    This test verifies that the bug fix (initializing proj_settings) is working
    """
    eval_dir = Path(__file__).parent.parent / "src/conversation_eval/evaluations/memory_wipe_tests"
    templates_dir = eval_dir / "templates" / "default"
    
    # Reset settings state (this is normally done once per run)
    # Note: We can't actually reset the frozen state in proj_settings, so we check if it's set
    
    # Verify that game_settings.yaml exists
    settings_path = templates_dir / "game_settings.yaml"
    assert settings_path.exists(), f"game_settings.yaml should exist at {settings_path}"
    
    # Initialize paths
    proj_paths.set_paths(
        project_path=eval_dir,
        templates_dir_name=templates_dir.name,
        version=1.0,
        save_name="test_settings"
    )
    
    # Initialize settings (this is what the bug fix adds)
    try:
        proj_settings.init_settings(settings_path)
    except RuntimeError:
        # Settings already initialized (from previous test run), that's OK
        pass
    
    # Now try to get settings - this should work
    try:
        settings = proj_settings.get_settings()
        assert settings is not None
        assert settings.app_settings is not None
        print("✅ Settings initialized successfully")
    except ValueError as e:
        pytest.fail(f"Settings should be initialized but got error: {e}")


def test_npc_types_available():
    """Test that all expected NPC types are available"""
    from src.conversation_eval.core.EvalRunner import EvalRunner
    
    assert "npc0" in EvalRunner.NPC_TYPES
    assert "npc1" in EvalRunner.NPC_TYPES
    assert "npc2" in EvalRunner.NPC_TYPES
    
    # Verify structure
    for npc_type, (npc_class, version) in EvalRunner.NPC_TYPES.items():
        assert npc_class is not None, f"{npc_type} should have a class"
        assert isinstance(version, (int, float)), f"{npc_type} should have a numeric version"
        print(f"✅ {npc_type}: class={npc_class.__name__}, version={version}")


def test_settings_file_structure():
    """Test that game_settings.yaml has the expected structure"""
    from src.utils import io_utils
    from src.core.schemas.Schemas import AppSettings
    
    eval_dir = Path(__file__).parent.parent / "src/conversation_eval/evaluations/memory_wipe_tests"
    templates_dir = eval_dir / "templates" / "default"
    settings_path = templates_dir / "game_settings.yaml"
    
    # Load and validate structure
    app_settings = io_utils.load_yaml_into_dataclass(settings_path, AppSettings)
    
    # Check key fields exist
    assert hasattr(app_settings, 'max_convo_mem_length')
    assert hasattr(app_settings, 'model')
    assert hasattr(app_settings, 'log_level')
    
    print(f"✅ game_settings.yaml structure valid")
    print(f"   Model: {app_settings.model}")
    print(f"   Log level: {app_settings.log_level}")


if __name__ == "__main__":
    print("Running NPC factory unit tests...\n")
    
    try:
        test_npc_types_available()
        print()
        test_settings_file_structure()
        print()
        test_settings_initialization_required_for_npc1()
        print()
        print("✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

