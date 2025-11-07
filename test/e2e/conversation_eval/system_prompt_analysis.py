#!/usr/bin/env python3
"""
System prompt analysis to identify the formatting issue without making API calls
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


def analyze_npc0_system_prompt():
    """Analyze NPC0's system prompt to identify formatting issues"""
    print("🔍 Analyzing NPC0 System Prompt")
    print("=" * 50)
    
    try:
        # Import without triggering API calls
        from src.npcs.npc0.npc0 import NPC0
        
        # Create NPC0 instance
        npc0 = NPC0("You are a helpful assistant.")
        
        # Get the system prompt
        system_prompt = npc0._build_system_prompt()
        
        print(f"📝 NPC0 System Prompt:")
        print(f"Length: {len(system_prompt)} characters")
        print(f"Content: '{system_prompt}'")
        print()
        
        # Analyze for formatting instructions
        formatting_indicators = {
            "json": "json" in system_prompt.lower(),
            "JSON": "JSON" in system_prompt,
            "format": "format" in system_prompt.lower(),
            "response": "response" in system_prompt,
            "hidden_thought_process": "hidden_thought_process" in system_prompt,
            "off_switch": "off_switch" in system_prompt,
            "structure": any(word in system_prompt.lower() for word in ["structure", "structured"]),
        }
        
        print("🔍 Formatting Instruction Analysis:")
        for indicator, present in formatting_indicators.items():
            status = "✅" if present else "❌"
            print(f"  {status} {indicator}: {present}")
        
        has_any_formatting = any(formatting_indicators.values())
        print(f"\n📊 Overall formatting instructions present: {has_any_formatting}")
        
        if not has_any_formatting:
            print("\n🎯 ISSUE IDENTIFIED!")
            print("NPC0's system prompt lacks formatting instructions for structured responses.")
            print("This will cause 'Error extracting object from LLM response' when ChatBot.call_llm")
            print("tries to parse the response as a ChatResponse object.")
            return False
        else:
            print("\n✅ NPC0 system prompt appears to have formatting instructions.")
            return True
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_with_expected_format():
    """Show what the system prompt should look like"""
    print("\n🔍 Expected System Prompt Format")
    print("=" * 50)
    
    expected_format = """You are a helpful assistant.

You must respond in the following JSON format:
{
    "hidden_thought_process": "Your internal reasoning and thought process",
    "response": "Your actual response to the user",
    "off_switch": false
}

Always respond in this exact JSON format."""
    
    print("📝 Expected system prompt should include:")
    print(expected_format)
    print()
    print("🔍 Key elements needed:")
    print("  - JSON format specification")
    print("  - Field definitions (hidden_thought_process, response, off_switch)")
    print("  - Instruction to always use this format")


def analyze_other_npcs():
    """Analyze other NPC types to see if they have proper formatting"""
    print("\n🔍 Analyzing Other NPC Types")
    print("=" * 50)
    
    # This is just to understand the pattern - we won't actually test them
    # since they might have complex setup requirements
    
    print("📝 NPC1 and NPC2 likely have proper formatting because:")
    print("  - They use Agent class which may add formatting instructions")
    print("  - They have more sophisticated prompt building")
    print("  - The error specifically mentions NPC0")
    
    print("\n🎯 The issue is likely that NPC0 is too simple and doesn't add")
    print("the necessary formatting instructions that other NPCs include.")


def main():
    """Run the system prompt analysis"""
    print("🧪 System Prompt Analysis for LLM Response Extraction Issue")
    print("=" * 60)
    print("Goal: Identify why NPC0 causes 'Error extracting object from LLM response'")
    print("=" * 60)
    
    # Analyze NPC0
    npc0_has_formatting = analyze_npc0_system_prompt()
    
    # Show expected format
    compare_with_expected_format()
    
    # Analyze other NPCs
    analyze_other_npcs()
    
    print("\n" + "=" * 60)
    if npc0_has_formatting:
        print("🤔 Unexpected: NPC0 appears to have formatting instructions")
        print("The issue might be elsewhere in the pipeline.")
    else:
        print("🎯 ISSUE CONFIRMED!")
        print("NPC0 lacks formatting instructions in its system prompt.")
        print("This causes LLM to return unstructured text that can't be parsed as ChatResponse.")
        print("\nNext step: Add formatting instructions to NPC0's system prompt.")
    print("=" * 60)


if __name__ == "__main__":
    main()
