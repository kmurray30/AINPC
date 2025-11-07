#!/usr/bin/env python3
"""
E2E test that demonstrates the NPC0 formatting issue without making API calls
This test examines the system prompt to identify the missing formatting suffix
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


def test_npc0_missing_formatting_suffix():
    """Test that demonstrates NPC0 is missing the formatting suffix"""
    print("🔍 Testing NPC0 Formatting Suffix Issue")
    print("=" * 60)
    
    try:
        # Import required modules
        from src.npcs.npc0.npc0 import NPC0
        from src.core.ResponseTypes import ChatResponse
        from src.utils import llm_utils
        
        print("✅ Successfully imported required modules")
        
        # Create NPC0 instance
        npc0 = NPC0("You are a helpful assistant.")
        
        # Get NPC0's system prompt
        npc0_system_prompt = npc0._build_system_prompt()
        print(f"\n📝 NPC0 System Prompt:")
        print(f"'{npc0_system_prompt}'")
        print(f"Length: {len(npc0_system_prompt)} characters")
        
        # Get the formatting suffix that should be added for ChatResponse
        expected_formatting_suffix = llm_utils.get_formatting_suffix(ChatResponse)
        print(f"\n📋 Expected Formatting Suffix for ChatResponse:")
        print(f"'{expected_formatting_suffix}'")
        print(f"Length: {len(expected_formatting_suffix)} characters")
        
        # Check if the formatting suffix is present in NPC0's system prompt
        has_formatting_suffix = expected_formatting_suffix in npc0_system_prompt
        print(f"\n🔍 Analysis:")
        print(f"NPC0 system prompt contains formatting suffix: {has_formatting_suffix}")
        
        if not has_formatting_suffix:
            print("\n🎯 ISSUE CONFIRMED!")
            print("NPC0's system prompt is missing the formatting suffix that tells the LLM")
            print("how to structure its response as a ChatResponse JSON object.")
            print("\nThis will cause 'Error extracting object from LLM response' when:")
            print("1. NPC0.chat() calls ChatBot.call_llm() with ChatResponse type")
            print("2. LLM returns unstructured text (no JSON)")
            print("3. llm_utils.extract_obj_from_llm_response() fails to parse it")
            return False
        else:
            print("\n✅ NPC0 system prompt includes formatting suffix (unexpected)")
            return True
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compare_with_agent_class():
    """Compare NPC0's approach with how Agent class handles formatting"""
    print("\n🔍 Comparing NPC0 with Agent Class Formatting")
    print("=" * 60)
    
    try:
        from src.core.Agent import Agent
        from src.core.ResponseTypes import ChatResponse
        from src.npcs.npc0.npc0 import NPC0
        
        # Create Agent instance (like NPC1 uses)
        agent = Agent("You are a helpful assistant.", ChatResponse)
        print(f"✅ Agent formatting suffix: '{agent.response_formatting_suffix[:100]}...'")
        print(f"Agent formatting suffix length: {len(agent.response_formatting_suffix)}")
        
        # Create NPC0 instance
        npc0 = NPC0("You are a helpful assistant.")
        npc0_prompt = npc0._build_system_prompt()
        print(f"\n📝 NPC0 system prompt: '{npc0_prompt}'")
        print(f"NPC0 system prompt length: {len(npc0_prompt)}")
        
        # Check if NPC0 includes the same formatting
        has_same_formatting = agent.response_formatting_suffix in npc0_prompt
        print(f"\n🔍 NPC0 includes Agent's formatting suffix: {has_same_formatting}")
        
        if not has_same_formatting:
            print("\n🎯 ROOT CAUSE IDENTIFIED!")
            print("Agent class automatically adds response_formatting_suffix to system prompts,")
            print("but NPC0 calls ChatBot.call_llm() directly without this formatting.")
            print("\nFix: NPC0 needs to add the formatting suffix to its system prompt")
            print("when calling ChatBot.call_llm() with a structured response type.")
        
        return has_same_formatting
        
    except Exception as e:
        print(f"❌ Comparison test failed: {e}")
        return False


def main():
    """Run the formatting issue demonstration"""
    print("🧪 E2E Test: NPC0 Formatting Issue Demonstration")
    print("=" * 70)
    print("Goal: Demonstrate that NPC0 lacks formatting instructions for ChatResponse")
    print("=" * 70)
    
    # Run tests
    test1_passed = test_npc0_missing_formatting_suffix()
    test2_passed = test_compare_with_agent_class()
    
    print("\n" + "=" * 70)
    if test1_passed and test2_passed:
        print("🤔 UNEXPECTED: Tests suggest NPC0 has proper formatting")
        print("The issue might be elsewhere in the pipeline.")
    else:
        print("🎯 SUCCESS: E2E test reproduced the formatting issue!")
        print("\nISSUE SUMMARY:")
        print("- NPC0 doesn't add formatting suffix to system prompts")
        print("- Agent class does add formatting suffix automatically") 
        print("- This causes LLM to return unstructured text")
        print("- ChatBot.call_llm() can't parse unstructured text as ChatResponse")
        print("- Result: 'Error extracting object from LLM response'")
        print("\nREADY TO FIX: Now we can implement the solution!")
    print("=" * 70)
    
    return not (test1_passed and test2_passed)  # Return True if issue was found


if __name__ == "__main__":
    issue_reproduced = main()
    sys.exit(0 if issue_reproduced else 1)  # Exit 0 if we successfully reproduced the issue
