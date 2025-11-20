#!/usr/bin/env python3
"""
Mock test to verify the framework is working without API calls
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from src.npcs.npc0.npc0 import NPC0
from src.conversation_eval.core.EvalConversation import EvalConversation
from src.conversation_eval.core.EvalConvoMember import EvalConvoMember
from src.core.Constants import AgentName
from src.core.ResponseTypes import ChatResponse


# Mock ChatBot to avoid API calls
class MockChatBot:
    @staticmethod
    def call_llm(message_history, response_type=None):
        if response_type == ChatResponse:
            return ChatResponse(
                hidden_thought_process="Mock thought process",
                response="This is a mock response for testing",
                off_switch=False
            )
        else:
            return "Mock string response"


def test_framework_without_api():
    """Test the framework components without making API calls"""
    print("Testing Enhanced NPC Evaluation Framework (Mock Mode)")
    print("=" * 55)
    
    # Temporarily replace ChatBot with mock
    import src.utils.ChatBot as ChatBotModule
    original_call_llm = ChatBotModule.ChatBot.call_llm
    ChatBotModule.ChatBot.call_llm = MockChatBot.call_llm
    
    try:
        # Test NPC0 creation and basic functionality
        print("1. Testing NPC0 creation...")
        npc0 = NPC0("You are a test assistant")
        print("   ✅ NPC0 created successfully")
        
        # Test state injection
        print("2. Testing state injection...")
        npc0.inject_memories(["Test memory 1", "Test memory 2"])
        npc0.inject_conversation_history([
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Hi there"}
        ])
        
        memories = npc0.get_all_memories()
        history = npc0.get_message_history()
        print(f"   ✅ Injected {len(memories)} memories and {len(history)} history items")
        
        # Test conversation
        print("3. Testing conversation...")
        response = npc0.chat("How are you?")
        print(f"   ✅ Got response: {response.response[:50]}...")
        
        # Test EvalConversation integration
        print("4. Testing EvalConversation integration...")
        conversation = EvalConversation()
        
        # Create agents
        agent1 = EvalConvoMember(AgentName.pat, "You are Pat")
        agent2 = EvalConvoMember(AgentName.mock_user, "You are a mock user")
        
        conversation.agents[AgentName.pat] = agent1
        conversation.agents[AgentName.mock_user] = agent2
        
        print("   ✅ EvalConversation set up with NPC-backed agents")
        
        # Test a conversation turn
        print("5. Testing conversation turn...")
        conversation.call_agent(AgentName.pat, AgentName.mock_user, response_is_typed=True, isPrinting=True)
        
        print(f"   ✅ Conversation has {len(conversation.message_history)} messages")
        
        print("\n🎉 All framework components working correctly!")
        print("\nFramework is ready for real API calls once you set up your OpenAI API key.")
        
    finally:
        # Restore original ChatBot
        ChatBotModule.ChatBot.call_llm = original_call_llm


if __name__ == "__main__":
    test_framework_without_api()
