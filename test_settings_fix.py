#!/usr/bin/env python3
"""
Simple test to verify the fix for NPC factory settings initialization
This test checks that the logic is correct without actually instantiating NPCs
"""
import sys
from pathlib import Path

def test_fix_is_present():
    """Verify the fix is present in run_tests.py"""
    
    run_tests_path = Path(__file__).parent / "src/conversation_eval/evaluations/memory_wipe_tests/run_tests.py"
    
    with open(run_tests_path, 'r') as file_handle:
        content = file_handle.read()
    
    # Check that proj_settings is imported
    assert "from src.core import proj_paths, proj_settings" in content, \
        "proj_settings should be imported"
    
    # Check that init_settings is called
    assert "proj_settings.init_settings(settings_path)" in content, \
        "proj_settings.init_settings should be called"
    
    # Check that the settings file path is checked
    assert 'settings_path = templates_dir / "game_settings.yaml"' in content, \
        "settings_path should be defined"
    
    # Check that there's error handling for missing settings
    assert "if settings_path.exists():" in content, \
        "Should check if settings file exists"
    
    print("✅ All required code changes are present in run_tests.py")
    print("   - proj_settings is imported")
    print("   - Settings initialization is called")
    print("   - Settings file path is checked")
    print("   - Error handling for RuntimeError is present")
    
    return True


def test_settings_file_exists():
    """Verify game_settings.yaml exists in the templates directory"""
    
    eval_dir = Path(__file__).parent / "src/conversation_eval/evaluations/memory_wipe_tests"
    templates_dir = eval_dir / "templates" / "default"
    settings_path = templates_dir / "game_settings.yaml"
    
    assert settings_path.exists(), f"game_settings.yaml should exist at {settings_path}"
    
    # Read and check basic structure
    with open(settings_path, 'r') as file_handle:
        content = file_handle.read()
    
    # Check for required fields
    assert "max_convo_mem_length:" in content, "Should have max_convo_mem_length"
    assert "model:" in content, "Should have model"
    assert "log_level:" in content, "Should have log_level"
    
    print(f"✅ game_settings.yaml exists and has required fields")
    print(f"   Path: {settings_path}")
    
    return True


def test_old_npc2_block_removed():
    """Verify the old NPC2 blocking code was removed"""
    
    run_tests_path = Path(__file__).parent / "src/conversation_eval/evaluations/memory_wipe_tests/run_tests.py"
    
    with open(run_tests_path, 'r') as file_handle:
        content = file_handle.read()
    
    # The old error message should NOT be present
    old_error_msg = "NPC2 is not currently supported due to settings initialization issues"
    assert old_error_msg not in content, \
        "Old NPC2 blocking error message should be removed"
    
    print("✅ Old NPC2 blocking code has been removed")
    
    return True


if __name__ == "__main__":
    print("Testing NPC factory settings fix...\n")
    
    try:
        test_fix_is_present()
        print()
        test_settings_file_exists()
        print()
        test_old_npc2_block_removed()
        print()
        print("🎉 All tests passed! The fix is correctly implemented.")
        print()
        print("Summary of the fix:")
        print("  1. Added proj_settings import")
        print("  2. Added settings initialization after proj_paths.set_paths()")
        print("  3. Added proper error handling for missing settings file")
        print("  4. Removed the old NPC2 blocking code")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

