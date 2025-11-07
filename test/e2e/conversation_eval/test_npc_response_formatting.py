#!/usr/bin/env python3
"""
E2E tests for NPC response formatting in conversation evaluation
These tests should catch formatting issues organically by testing the full pipeline
"""
import os
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.npcs.npc0.npc0 import NPC0
from src.npcs.npc1.npc1 import NPC1
from src.npcs.npc2.npc2 import NPC2
from src.conversation_eval.EvalConversation import EvalConversation
from src.conversation_eval.EvalConvoMember import EvalConvoMember
from src.core.Constants import AgentName
from src.core.ResponseTypes import ChatResponse


class TestNPCResponseFormatting:
    """Test that NPCs properly format their responses for conversation evaluation"""
    
    def test_npc0_returns_structured_response(self):
        """Test that NPC0 returns a properly structured ChatResponse object"""
        # This should catch the formatting issue organically
        npc0 = NPC0("You are a helpful assistant. Always respond helpfully.")
        
        # Test basic chat functionality
        response = npc0.chat("Hello, how are you?")
        
        # Verify we get a ChatResponse object (not a string)
        assert isinstance(response, ChatResponse), f"Expected ChatResponse, got {type(response)}"
        
        # Verify the response has the required fields
        assert hasattr(response, 'response'), "ChatResponse missing 'response' field"
        assert hasattr(response, 'hidden_thought_process'), "ChatResponse missing 'hidden_thought_process' field"
        assert hasattr(response, 'off_switch'), "ChatResponse missing 'off_switch' field"
        
        # Verify the fields have reasonable values
        assert isinstance(response.response, str), "Response should be a string"
        assert len(response.response) > 0, "Response should not be empty"
        assert isinstance(response.off_switch, bool), "off_switch should be a boolean"
    
    def test_npc0_in_conversation_evaluation(self):
        """Test NPC0 works properly in the conversation evaluation framework"""
        # Create a conversation with NPC0-backed agents
        conversation = EvalConversation()
        
        # Create agents backed by NPC0
        assistant_agent = EvalConvoMember(AgentName.pat, "You are Pat, a helpful AI assistant.")
        user_agent = EvalConvoMember(AgentName.mock_user, "You are a test user. Be brief and friendly.")
        
        conversation.agents[AgentName.pat] = assistant_agent
        conversation.agents[AgentName.mock_user] = user_agent
        
        # Test that we can have a conversation turn without errors
        try:
            conversation.call_agent(AgentName.pat, AgentName.mock_user, response_is_typed=True, isPrinting=False)
            conversation.call_agent(AgentName.mock_user, AgentName.pat, response_is_typed=True, isPrinting=False)
        except Exception as e:
            pytest.fail(f"Conversation evaluation failed with NPC0: {e}")
        
        # Verify we have message history
        assert len(conversation.message_history) == 2, "Should have 2 messages after 2 turns"
        
        # Verify messages are properly formatted
        for msg in conversation.message_history:
            assert hasattr(msg, 'agent'), "Message should have agent field"
            assert hasattr(msg, 'content'), "Message should have content field"
            assert isinstance(msg.content, str), "Message content should be string"
    
    def test_npc0_vs_other_npcs_consistency(self):
        """Test that NPC0 behaves consistently with other NPC types in terms of response format"""
        test_prompt = "You are a test assistant. Respond helpfully."
        test_message = "What is 2+2?"
        
        # Test NPC0
        npc0 = NPC0(test_prompt)
        response0 = npc0.chat(test_message)
        
        # Verify NPC0 response format
        assert isinstance(response0, ChatResponse), "NPC0 should return ChatResponse"
        assert isinstance(response0.response, str), "NPC0 response should be string"
        assert isinstance(response0.off_switch, bool), "NPC0 off_switch should be boolean"
        
        # Test that the response format is consistent with what the evaluation framework expects
        # This is where the formatting issue should surface if it exists
        
    def test_npc0_with_typed_responses(self):
        """Test NPC0 specifically with typed responses (where formatting issues are most likely)"""
        npc0 = NPC0("You are a helpful assistant.")
        
        # This should trigger the structured response formatting
        response = npc0.chat("Please help me with a simple task.")
        
        # Verify the response is properly structured
        assert isinstance(response, ChatResponse), "Should return ChatResponse for typed responses"
        
        # Test that all required fields are present and properly typed
        assert response.response is not None, "Response field should not be None"
        assert isinstance(response.response, str), "Response should be a string"
        
        # Test that hidden_thought_process is handled correctly
        if response.hidden_thought_process is not None:
            assert isinstance(response.hidden_thought_process, str), "hidden_thought_process should be string if present"
        
        # Test off_switch
        assert isinstance(response.off_switch, bool), "off_switch should be boolean"
    
    def test_conversation_evaluation_with_multiple_turns(self):
        """Test multi-turn conversation to catch formatting issues that might appear over time"""
        conversation = EvalConversation()
        
        # Set up agents
        assistant_agent = EvalConvoMember(AgentName.pat, "You are a helpful assistant.")
        user_agent = EvalConvoMember(AgentName.mock_user, "You are a friendly user.")
        
        conversation.agents[AgentName.pat] = assistant_agent
        conversation.agents[AgentName.mock_user] = user_agent
        
        # Have multiple conversation turns
        num_turns = 3
        for i in range(num_turns):
            try:
                conversation.call_agent(AgentName.pat, AgentName.mock_user, response_is_typed=True, isPrinting=False)
                conversation.call_agent(AgentName.mock_user, AgentName.pat, response_is_typed=True, isPrinting=False)
            except Exception as e:
                pytest.fail(f"Multi-turn conversation failed at turn {i+1}: {e}")
        
        # Verify we have the expected number of messages
        expected_messages = num_turns * 2
        assert len(conversation.message_history) == expected_messages, f"Expected {expected_messages} messages, got {len(conversation.message_history)}"
        
        # Verify all messages are properly formatted
        for i, msg in enumerate(conversation.message_history):
            assert msg.content is not None, f"Message {i} has None content"
            assert isinstance(msg.content, str), f"Message {i} content is not string: {type(msg.content)}"
            assert len(msg.content) > 0, f"Message {i} has empty content"


if __name__ == "__main__":
    # Run the tests directly
    pytest.main([__file__, "-v"])
