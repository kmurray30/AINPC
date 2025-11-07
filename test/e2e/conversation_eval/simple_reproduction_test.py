#!/usr/bin/env python3
"""
Simple reproduction test for the "Error extracting object from LLM response" issue
This test runs without pytest to avoid environment issues
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


def test_npc0_response_extraction():
    """Test NPC0 response extraction to reproduce the formatting issue"""
    print("🔍 Testing NPC0 Response Extraction")
    print("=" * 50)
    
    try:
        from src.npcs.npc0.npc0 import NPC0
        print("✅ Successfully imported NPC0")
        
        # Create NPC0 instance
        npc0 = NPC0("You are a helpful assistant.")
        print("✅ Successfully created NPC0 instance")
        
        # Check the system prompt
        system_prompt = npc0._build_system_prompt()
        print(f"📝 NPC0 system prompt: {system_prompt}")
        print(f"📏 System prompt length: {len(system_prompt)}")
        
        # Check if formatting instructions are present
        has_json_format = "json" in system_prompt.lower() or "JSON" in system_prompt
        has_response_format = "response" in system_prompt and "hidden_thought_process" in system_prompt
        
        print(f"🔍 Has JSON format instructions: {has_json_format}")
        print(f"🔍 Has response format instructions: {has_response_format}")
        
        if not (has_json_format or has_response_format):
            print("⚠️  WARNING: NPC0 system prompt appears to be missing formatting instructions!")
            print("This is likely the cause of the 'Error extracting object from LLM response' issue.")
        
        # Now try to make a chat call
        print("\n🚀 Testing NPC0 chat call...")
        try:
            response = npc0.chat("Hello, please introduce yourself briefly.")
            print(f"✅ Chat call successful!")
            print(f"📤 Response type: {type(response)}")
            print(f"📤 Response: {response}")
            
            # Verify it's a ChatResponse object
            from src.core.ResponseTypes import ChatResponse
            if isinstance(response, ChatResponse):
                print("✅ Response is properly formatted as ChatResponse")
            else:
                print(f"❌ Response is not ChatResponse, got: {type(response)}")
                
        except Exception as e:
            print(f"❌ Chat call failed with error: {e}")
            if "Error extracting object from LLM response" in str(e):
                print("🎯 REPRODUCED THE ISSUE! This is the formatting error we're looking for.")
                return False
            else:
                print(f"Different error occurred: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False


def test_chatbot_direct_call():
    """Test ChatBot direct call to isolate the issue"""
    print("\n🔍 Testing ChatBot Direct Call")
    print("=" * 50)
    
    try:
        from src.utils.ChatBot import ChatBot
        from src.core.ResponseTypes import ChatResponse
        print("✅ Successfully imported ChatBot and ChatResponse")
        
        # Test with basic system prompt (no formatting)
        messages_no_format = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"}
        ]
        
        print("🧪 Testing ChatBot call with no formatting instructions...")
        try:
            response = ChatBot.call_llm(messages_no_format, ChatResponse)
            print(f"✅ Call successful with no formatting: {type(response)}")
        except Exception as e:
            print(f"❌ Call failed with no formatting: {e}")
            if "Error extracting object from LLM response" in str(e):
                print("🎯 REPRODUCED! No formatting instructions cause extraction error.")
                
        # Test with explicit formatting instructions
        messages_with_format = [
            {"role": "system", "content": """You are a helpful assistant.

You must respond in the following JSON format:
{
    "hidden_thought_process": "Your internal reasoning",
    "response": "Your actual response to the user",
    "off_switch": false
}

Always respond in this exact JSON format."""},
            {"role": "user", "content": "Hello"}
        ]
        
        print("\n🧪 Testing ChatBot call with explicit formatting instructions...")
        try:
            response = ChatBot.call_llm(messages_with_format, ChatResponse)
            print(f"✅ Call successful with formatting: {type(response)}")
            print(f"📤 Response: {response}")
        except Exception as e:
            print(f"❌ Call failed even with formatting: {e}")
            
    except Exception as e:
        print(f"❌ ChatBot test setup failed: {e}")


def test_compare_npc_system_prompts():
    """Compare system prompts between NPC types"""
    print("\n🔍 Comparing NPC System Prompts")
    print("=" * 50)
    
    try:
        from src.npcs.npc0.npc0 import NPC0
        
        # Test NPC0
        npc0 = NPC0("You are a helpful assistant.")
        npc0_prompt = npc0._build_system_prompt()
        
        print(f"NPC0 system prompt:")
        print(f"Length: {len(npc0_prompt)}")
        print(f"Content: {npc0_prompt}")
        print()
        
        # Check for formatting instructions
        formatting_keywords = ["json", "JSON", "format", "response", "hidden_thought_process"]
        found_keywords = [kw for kw in formatting_keywords if kw in npc0_prompt]
        
        print(f"Formatting keywords found: {found_keywords}")
        
        if not found_keywords:
            print("🎯 ISSUE IDENTIFIED: NPC0 system prompt lacks formatting instructions!")
            print("This explains why LLM response extraction fails.")
            
    except Exception as e:
        print(f"❌ System prompt comparison failed: {e}")


def main():
    """Run all reproduction tests"""
    print("🧪 E2E Reproduction Test for LLM Response Extraction Issue")
    print("=" * 60)
    print("Goal: Organically reproduce 'Error extracting object from LLM response'")
    print("=" * 60)
    
    # Run tests
    test1_passed = test_npc0_response_extraction()
    test_chatbot_direct_call()
    test_compare_npc_system_prompts()
    
    print("\n" + "=" * 60)
    if test1_passed:
        print("✅ Tests completed - no issues found (unexpected)")
    else:
        print("🎯 Successfully reproduced the LLM response extraction issue!")
        print("The issue is that NPC0 doesn't include formatting instructions in its system prompt.")
    print("=" * 60)


if __name__ == "__main__":
    main()
