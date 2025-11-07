#!/usr/bin/env python3
"""
E2E test runner for conversation evaluation framework
This will help us reproduce and fix the "Error extracting object from LLM response" issue
"""
import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


def run_e2e_tests():
    """Run all e2e tests and report results"""
    test_dir = Path(__file__).parent
    
    print("🧪 Running E2E Tests for Conversation Evaluation Framework")
    print("=" * 60)
    print("Goal: Reproduce 'Error extracting object from LLM response' organically")
    print("=" * 60)
    
    # Find all test files
    test_files = list(test_dir.glob("test_*.py"))
    
    if not test_files:
        print("❌ No test files found!")
        return False
    
    print(f"Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {test_file.name}")
    print()
    
    all_passed = True
    
    for test_file in test_files:
        print(f"🔍 Running {test_file.name}...")
        print("-" * 40)
        
        try:
            # Run pytest on the specific file
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_file), "-v", "-s"],
                cwd=test_dir,
                capture_output=False,  # Show output in real-time
                timeout=120  # 2 minute timeout per test file
            )
            
            if result.returncode == 0:
                print(f"✅ {test_file.name} PASSED")
            else:
                print(f"❌ {test_file.name} FAILED (return code: {result.returncode})")
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_file.name} TIMED OUT")
            all_passed = False
        except Exception as e:
            print(f"💥 {test_file.name} ERROR: {e}")
            all_passed = False
        
        print()
    
    print("=" * 60)
    if all_passed:
        print("🎉 All E2E tests PASSED!")
        print("The conversation evaluation framework is working correctly.")
    else:
        print("⚠️  Some E2E tests FAILED!")
        print("This indicates issues in the conversation evaluation framework.")
        print("Check the output above for specific error details.")
    print("=" * 60)
    
    return all_passed


def run_single_test(test_name: str):
    """Run a single test file"""
    test_dir = Path(__file__).parent
    test_file = test_dir / f"test_{test_name}.py"
    
    if not test_file.exists():
        print(f"❌ Test file {test_file} not found!")
        available_tests = [f.stem.replace('test_', '') for f in test_dir.glob("test_*.py")]
        print(f"Available tests: {', '.join(available_tests)}")
        return False
    
    print(f"🔍 Running single test: {test_file.name}")
    print("=" * 50)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "-s"],
            cwd=test_dir,
            timeout=120
        )
        
        if result.returncode == 0:
            print(f"✅ {test_file.name} PASSED")
            return True
        else:
            print(f"❌ {test_file.name} FAILED")
            return False
            
    except Exception as e:
        print(f"💥 Error running test: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        run_single_test(test_name)
    else:
        # Run all tests
        run_e2e_tests()
