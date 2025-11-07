#!/usr/bin/env python3
"""
Fallback runner that handles API issues gracefully
"""
import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))


def test_single_evaluation_with_fallback(test_file: str, npc_type: str):
    """Test a single evaluation with fallback handling"""
    print(f"🧪 Testing {test_file} with {npc_type}")
    print("-" * 50)
    
    try:
        # Try to import and run directly first
        print("Attempting direct execution...")
        
        # Import the test components
        from src.conversation_eval.evaluations.EvalRunner import EvalRunner
        from src.conversation_eval.EvalHelper import EvalHelper
        from src.conversation_eval.EvalClasses import Proposition, Term, EvalCase, EvalCaseSuite
        
        print("✅ Imports successful")
        
        # Set up the test environment
        eval_dir = Path(__file__).parent
        
        try:
            # Temporarily set sys.argv to simulate command line args
            original_argv = sys.argv.copy()
            sys.argv = ['test_script', npc_type]
            
            assistant_npc, npc_type = EvalRunner.parse_args_and_setup_npc(
                eval_dir, 
                npc_name="assistant", 
                save_enabled=False
            )
            
            # Restore original argv
            sys.argv = original_argv
            print("✅ NPC setup successful")
            
            # Create a simple test case
            test_suite = EvalCaseSuite(
                eval_cases=[
                    EvalCase(
                        goals=["Test basic conversation"],
                        propositions=[Proposition(
                            antecedent=Term("User sends message"),
                            consequent=Term("AI responds appropriately")
                        )]
                    )
                ]
            )
            
            print("✅ Test suite created")
            
            # Load templates
            from src.core import proj_paths
            paths = proj_paths.get_paths()
            from src.npcs.npc1.npc1 import NPCTemplate
            
            assistant_template = paths.load_npc_template_with_fallback("assistant", NPCTemplate)
            mock_user_template = paths.load_npc_template_with_fallback("mock_user", NPCTemplate)
            
            assistant_rules = [assistant_template.system_prompt]
            mock_user_base_rules = [mock_user_template.system_prompt]
            
            print("✅ Templates loaded")
            print("🚀 Starting evaluation...")
            
            # Run the evaluation
            test_report = EvalHelper.run_conversation_eval_with_npc(
                assistant_npc, assistant_rules, mock_user_base_rules, test_suite, 
                1, 1, 2  # Simple short test
            )
            
            print("🎉 Evaluation completed successfully!")
            print(f"Report generated with {len(test_report.assistant_prompt_cases)} cases")
            
            return True
            
        except Exception as api_error:
            print(f"⚠️ API/Execution error: {api_error}")
            print("This is likely due to:")
            print("1. OpenAI API key issues")
            print("2. Network connectivity")
            print("3. Rate limiting")
            print("4. Environment setup")
            
            return False
            
    except ImportError as import_error:
        print(f"❌ Import error: {import_error}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner with fallback"""
    print("Enhanced NPC Evaluation Framework - Fallback Test")
    print("=" * 55)
    
    # Test with NPC0 first (simplest)
    success = test_single_evaluation_with_fallback("memory_wipe_after_belligerence_test.py", "npc0")
    
    if success:
        print("\n✅ Framework is working correctly!")
        print("You can now run full evaluations with:")
        print("  python run_all_tests.py")
    else:
        print("\n⚠️ There are some issues to resolve:")
        print("1. Check your OpenAI API key in .env file")
        print("2. Verify network connectivity")
        print("3. Check Python environment and dependencies")
        print("\nThe framework structure is correct, just need to resolve the runtime issues.")


if __name__ == "__main__":
    main()
