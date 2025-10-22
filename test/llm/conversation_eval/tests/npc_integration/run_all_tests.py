#!/usr/bin/env python3
"""
Comprehensive test runner for NPC integration with conversation evaluation framework.

This script runs all NPC integration tests and provides a summary of results.
"""

import os
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))


def main():
    """Run all NPC integration tests"""
    test_dir = Path(__file__).parent
    
    print("=" * 80)
    print("NPC CONVERSATION EVALUATION INTEGRATION TESTS")
    print("=" * 80)
    print()
    
    # Test files to run
    test_files = [
        "test_npc1_conversation_eval.py",
        "test_npc2_conversation_eval.py", 
        "test_npc_interchangeability.py",
        "test_conversation_framework_integration.py"
    ]
    
    print("Running the following test suites:")
    for i, test_file in enumerate(test_files, 1):
        print(f"  {i}. {test_file}")
    print()
    
    # Run tests with verbose output
    args = [
        str(test_dir),
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure for easier debugging
        "--disable-warnings"  # Reduce noise
    ]
    
    print("Starting test execution...")
    print("-" * 40)
    
    exit_code = pytest.main(args)
    
    print("-" * 40)
    if exit_code == 0:
        print("✅ All NPC integration tests PASSED!")
        print()
        print("Summary:")
        print("- NPC1 conversation evaluation: ✅")
        print("- NPC2 conversation evaluation: ✅") 
        print("- NPC interchangeability: ✅")
        print("- Framework integration: ✅")
    else:
        print("❌ Some tests FAILED!")
        print()
        print("Please check the output above for details.")
        print("Common issues:")
        print("- Missing template files")
        print("- Qdrant server not running (for NPC2 tests)")
        print("- Import path issues")
        print("- Singleton state conflicts")
    
    print()
    print("=" * 80)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
