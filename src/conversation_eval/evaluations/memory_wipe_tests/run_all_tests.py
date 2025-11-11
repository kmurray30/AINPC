#!/usr/bin/env python3
"""
Script for running all memory wipe tests across multiple NPCs
"""
import os
import sys
import subprocess
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from src.conversation_eval.MultiNPCComparison import MultiNPCComparison
from src.conversation_eval.StreamingEvalDisplay import get_streaming_display


def run_simple_sequential():
    """Run tests sequentially for each NPC - simpler and more reliable"""
    test_suite_dir = Path(__file__).parent
    
    # Find all test files
    test_files = [
        "memory_wipe_after_belligerence_test.py",
        "memory_persistence_with_context_test.py", 
        "emotional_escalation_response_test.py",
        "protocol_breaking_safety_test.py"
    ]
    
    npc_types = ["npc0", "npc1", "npc2"]
    
    print("Enhanced NPC Evaluation Framework")
    print("=" * 50)
    print(f"Test Suite: {test_suite_dir.name}")
    print(f"Test Files: {len(test_files)}")
    print(f"NPC Types: {', '.join(npc_types)}")
    print()
    
    results = {}
    
    for npc_type in npc_types:
        print(f"\n🤖 Running tests for {npc_type.upper()}")
        print("-" * 30)
        results[npc_type] = {}
        
        for test_file in test_files:
            test_path = test_suite_dir / test_file
            if not test_path.exists():
                print(f"  ⚠ {test_file} not found, skipping...")
                continue
            
            # Display test start with streaming display
            streaming_display = get_streaming_display()
            streaming_display.display_npc_test_start(npc_type, test_file)
            
            start_time = time.time()
            
            try:
                # Don't capture output - let it stream directly to terminal for real-time display
                result = subprocess.run(
                    [sys.executable, str(test_path), npc_type],
                    cwd=test_path.parent,
                    timeout=300  # 5 minute timeout
                )
                
                duration = time.time() - start_time
                
                if result.returncode == 0:
                    print(f"\n✅ Test completed successfully")
                    results[npc_type][test_file] = "PASS"
                    streaming_display.display_test_summary(True, duration=duration)
                else:
                    print(f"\n❌ Test failed (return code {result.returncode})")
                    results[npc_type][test_file] = "FAIL"
                    streaming_display.display_test_summary(False, duration=duration)
                    
            except subprocess.TimeoutExpired:
                print(f"    ⏰ Timed out after 5 minutes")
                results[npc_type][test_file] = "TIMEOUT"
            except Exception as e:
                print(f"    ❌ Error: {e}")
                results[npc_type][test_file] = "ERROR"
    
    # Print summary
    print(f"\n📊 SUMMARY")
    print("=" * 50)
    
    for npc_type in npc_types:
        if npc_type in results:
            passed = sum(1 for status in results[npc_type].values() if status == "PASS")
            total = len(results[npc_type])
            print(f"{npc_type.upper()}: {passed}/{total} tests passed")
            
            for test_file, status in results[npc_type].items():
                status_icon = {"PASS": "✅", "FAIL": "❌", "TIMEOUT": "⏰", "ERROR": "💥"}.get(status, "❓")
                print(f"  {status_icon} {test_file}")
    
    print(f"\n🎯 All tests completed! Check the reports/ directory for detailed results.")


def run_comparison_framework():
    """Run using the comparison framework (may have issues with complex setups)"""
    test_suite_dir = Path(__file__).parent
    
    test_files = [
        "memory_wipe_after_belligerence_test.py",
        "memory_persistence_with_context_test.py", 
        "emotional_escalation_response_test.py",
        "protocol_breaking_safety_test.py"
    ]
    
    print("Running comprehensive NPC comparison...")
    comparator = MultiNPCComparison(test_suite_dir)
    report = comparator.run_comparison(test_files)
    
    # Display results
    comparator.print_comparison_summary(report)
    
    # Save detailed report
    output_path = test_suite_dir / "comprehensive_comparison_report.json"
    comparator.save_comparison_report(report, output_path)
    
    print(f"Detailed report saved to: {output_path}")


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--comparison":
        run_comparison_framework()
    else:
        print("Running tests sequentially (recommended)")
        print("Use --comparison flag for comparison framework")
        print()
        run_simple_sequential()


if __name__ == "__main__":
    main()
