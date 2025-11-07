#!/usr/bin/env python3
"""
E2E tests for LLM response extraction in conversation evaluation
These tests should catch the "Error extracting object from LLM response" issue organically
"""
import os
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.npcs.npc0.npc0 import NPC0
from src.utils.ChatBot import ChatBot
from src.core.ResponseTypes import ChatResponse
from src.utils import llm_utils


class TestLLMResponseExtraction:
    """Test that LLM responses are properly extracted and parsed"""
    
    def test_npc0_llm_call_returns_structured_response(self):
        """Test that NPC0's LLM calls return properly structured responses"""
        npc0 = NPC0("You are a helpful assistant.")
        
        # This should trigger the LLM call and response extraction
        try:
            response = npc0.chat("Hello")
        except Exception as e:
            if "Error extracting object from LLM response" in str(e):
                pytest.fail(f"LLM response extraction failed: {e}")
            else:
                # Re-raise if it's a different error
                raise
        
        # Verify we got a proper response
        assert isinstance(response, ChatResponse), f"Expected ChatResponse, got {type(response)}"
    
    def test_chatbot_call_llm_with_response_type(self):
        """Test ChatBot.call_llm with ChatResponse type directly"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello"}
        ]
        
        try:
            response = ChatBot.call_llm(messages, ChatResponse)
        except Exception as e:
            if "Error extracting object from LLM response" in str(e):
                pytest.fail(f"ChatBot LLM response extraction failed: {e}")
            else:
                # Re-raise if it's a different error
                raise
        
        assert isinstance(response, ChatResponse), f"Expected ChatResponse, got {type(response)}"
    
    def test_llm_response_format_requirements(self):
        """Test what format the LLM response needs to be in for proper extraction"""
        # Test with a system prompt that should produce structured output
        system_prompt = """You are a helpful assistant. 
        
        You must respond in the following JSON format:
        {
            "hidden_thought_process": "Your reasoning process",
            "response": "Your actual response to the user",
            "off_switch": false
        }"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        try:
            response = ChatBot.call_llm(messages, ChatResponse)
            assert isinstance(response, ChatResponse), "Should return ChatResponse"
        except Exception as e:
            if "Error extracting object from LLM response" in str(e):
                # This is the error we're trying to catch!
                pytest.fail(f"LLM response extraction failed - this indicates a formatting issue: {e}")
            else:
                raise
    
    def test_npc0_system_prompt_includes_formatting_instructions(self):
        """Test that NPC0's system prompt includes proper formatting instructions for structured responses"""
        npc0 = NPC0("You are a helpful assistant.")
        
        # Get the system prompt that NPC0 builds
        system_prompt = npc0._build_system_prompt()
        
        # Check if the system prompt includes formatting instructions
        # This test will help us identify if the formatting suffix is missing
        print(f"NPC0 system prompt: {system_prompt}")
        
        # Try to make a call and see if it works
        try:
            response = npc0.chat("Test message")
            assert isinstance(response, ChatResponse), "Should return structured response"
        except Exception as e:
            if "Error extracting object from LLM response" in str(e):
                # This suggests the system prompt doesn't include proper formatting instructions
                pytest.fail(f"NPC0 system prompt missing formatting instructions. Error: {e}")
            else:
                raise
    
    def test_compare_npc_system_prompts(self):
        """Compare system prompts between different NPC types to identify differences"""
        npc0 = NPC0("You are a helpful assistant.")
        
        # Get NPC0's system prompt
        npc0_prompt = npc0._build_system_prompt()
        print(f"NPC0 system prompt length: {len(npc0_prompt)}")
        print(f"NPC0 system prompt: {npc0_prompt}")
        
        # Test if NPC0 can handle structured responses
        try:
            response = npc0.chat("Please respond to this test message.")
            print(f"NPC0 response type: {type(response)}")
            print(f"NPC0 response: {response}")
        except Exception as e:
            print(f"NPC0 failed with error: {e}")
            if "Error extracting object from LLM response" in str(e):
                pytest.fail(f"NPC0 system prompt formatting issue detected: {e}")
            else:
                raise
    
    def test_manual_llm_call_with_formatting(self):
        """Test manual LLM call with explicit formatting instructions"""
        # This test will help us understand what formatting is needed
        system_prompt_with_formatting = """You are a helpful assistant.

You must respond in the following JSON format:
{
    "hidden_thought_process": "Your internal reasoning and thought process",
    "response": "Your actual response to the user",
    "off_switch": false
}

Always respond in this exact JSON format."""
        
        messages = [
            {"role": "system", "content": system_prompt_with_formatting},
            {"role": "user", "content": "Hello, please introduce yourself."}
        ]
        
        try:
            response = ChatBot.call_llm(messages, ChatResponse)
            assert isinstance(response, ChatResponse), "Should successfully parse with formatting instructions"
            print(f"Successful response with formatting: {response}")
        except Exception as e:
            pytest.fail(f"Even with explicit formatting instructions, parsing failed: {e}")
    
    def test_npc0_missing_formatting_detection(self):
        """Specific test to detect if NPC0 is missing formatting instructions"""
        npc0 = NPC0("You are a helpful assistant.")
        
        # Check the actual system prompt NPC0 uses
        system_prompt = npc0._build_system_prompt()
        
        # Look for formatting instructions
        has_json_format = "json" in system_prompt.lower() or "JSON" in system_prompt
        has_response_format = "response" in system_prompt and "hidden_thought_process" in system_prompt
        has_format_instructions = has_json_format or has_response_format
        
        print(f"NPC0 system prompt has formatting instructions: {has_format_instructions}")
        print(f"System prompt: {system_prompt}")
        
        if not has_format_instructions:
            pytest.fail("NPC0 system prompt is missing formatting instructions for structured responses")
        
        # Now test if it actually works
        try:
            response = npc0.chat("Test message")
            assert isinstance(response, ChatResponse), "Should work with formatting instructions"
        except Exception as e:
            if "Error extracting object from LLM response" in str(e):
                pytest.fail(f"NPC0 formatting instructions are insufficient: {e}")
            else:
                raise


if __name__ == "__main__":
    # Run the tests directly
    pytest.main([__file__, "-v", "-s"])  # -s to show print statements
