#!/usr/bin/env python3
"""
Simple script to run a single test with a specific NPC type
Usage: python run_single_test.py <test_file> <npc_type>
"""
import os
import sys
import subprocess
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        print("Usage: python run_single_test.py <test_file> <npc_type>")
        print("Example: python run_single_test.py memory_wipe_after_belligerence_test.py npc1")
        print("Available NPC types: npc0, npc1, npc2")
        sys.exit(1)
    
    test_file = sys.argv[1]
    npc_type = sys.argv[2]
    
    test_path = Path(__file__).parent / test_file
    
    if not test_path.exists():
        print(f"Test file {test_file} not found in {Path(__file__).parent}")
        sys.exit(1)
    
    print(f"Running {test_file} with {npc_type}...")
    print("=" * 50)
    
    # Execute the test
    try:
        result = subprocess.run(
            [sys.executable, str(test_path), npc_type],
            cwd=test_path.parent,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print(f"✅ Test completed successfully!")
        else:
            print(f"❌ Test failed with return code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("❌ Test timed out after 5 minutes")
    except Exception as e:
        print(f"❌ Error running test: {e}")


if __name__ == "__main__":
    main()
