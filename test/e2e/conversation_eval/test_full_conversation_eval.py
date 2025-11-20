#!/usr/bin/env python3
"""
Full E2E test to verify the NPC0 fix works in actual conversation evaluation
This test attempts to run a real conversation evaluation with NPC0
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


def test_npc0_conversation_evaluation():
    """Test NPC0 in actual conversation evaluation context"""
    print("🔍 Testing NPC0 in Conversation Evaluation")
    print("=" * 60)
    
    try:
        # Import conversation evaluation components
        from src.conversation_eval.core.EvalConversation import EvalConversation
        from src.conversation_eval.core.EvalConvoMember import EvalConvoMember
        from src.core.Constants import AgentName
        
        print("✅ Successfully imported conversation evaluation components")
        
        # Create a conversation with NPC0-backed agents
        conversation = EvalConversation()
        
        # Create agents (EvalConvoMember defaults to NPC0 if no npc_protocol provided)
        assistant_agent = EvalConvoMember(AgentName.pat, "You are Pat, a helpful AI assistant.")
        user_agent = EvalConvoMember(AgentName.mock_user, "You are a test user. Be brief and friendly.")
        
        conversation.agents[AgentName.pat] = assistant_agent
        conversation.agents[AgentName.mock_user] = user_agent
        
        print("✅ Successfully created conversation with NPC0-backed agents")
        
        # Test that we can have a conversation turn without the formatting error
        print("\n🚀 Testing conversation turn...")
        try:
            # This should now work without "Error extracting object from LLM response"
            conversation.call_agent(AgentName.pat, AgentName.mock_user, response_is_typed=True, isPrinting=False)
            print("✅ First conversation turn successful!")
            
            # Try a second turn
            conversation.call_agent(AgentName.mock_user, AgentName.pat, response_is_typed=True, isPrinting=False)
            print("✅ Second conversation turn successful!")
            
            # Verify we have message history
            assert len(conversation.message_history) == 2, f"Expected 2 messages, got {len(conversation.message_history)}"
            print(f"✅ Message history contains {len(conversation.message_history)} messages")
            
            # Verify messages are properly formatted
            for i, msg in enumerate(conversation.message_history):
                assert hasattr(msg, 'agent'), f"Message {i} missing agent field"
                assert hasattr(msg, 'content'), f"Message {i} missing content field"
                assert isinstance(msg.content, str), f"Message {i} content is not string: {type(msg.content)}"
                print(f"✅ Message {i}: {msg.agent} - '{msg.content[:50]}...'")
            
            print("\n🎉 SUCCESS: NPC0 conversation evaluation works!")
            print("The formatting fix resolved the 'Error extracting object from LLM response' issue.")
            return True
            
        except Exception as e:
            if "Error extracting object from LLM response" in str(e):
                print(f"❌ FORMATTING ERROR STILL EXISTS: {e}")
                print("The fix did not resolve the issue.")
                return False
            else:
                print(f"❌ Different error occurred: {e}")
                print("This might be an environment issue, not the formatting problem.")
                return False
                
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        print("This might be due to environment issues (segfaults, imports, etc.)")
        return False


def test_npc0_direct_chat():
    """Test NPC0 chat method directly"""
    print("\n🔍 Testing NPC0 Chat Method Directly")
    print("=" * 50)
    
    try:
        from src.npcs.npc0.npc0 import NPC0
        from src.core.ResponseTypes import ChatResponse
        
        print("✅ Successfully imported NPC0 and ChatResponse")
        
        # Create NPC0 instance
        npc0 = NPC0("You are a helpful assistant.")
        print("✅ Successfully created NPC0 instance")
        
        # Test chat method
        print("\n🚀 Testing NPC0.chat() method...")
        try:
            response = npc0.chat("Hello, please introduce yourself briefly.")
            print(f"✅ Chat call successful!")
            print(f"Response type: {type(response)}")
            
            # Verify it's a ChatResponse object
            if isinstance(response, ChatResponse):
                print("✅ Response is properly formatted as ChatResponse")
                print(f"Response content: '{response.response[:100]}...'")
                print(f"Hidden thought process: '{response.hidden_thought_process[:100]}...'")
                print(f"Off switch: {response.off_switch}")
                return True
            else:
                print(f"❌ Response is not ChatResponse, got: {type(response)}")
                return False
                
        except Exception as e:
            if "Error extracting object from LLM response" in str(e):
                print(f"❌ FORMATTING ERROR STILL EXISTS: {e}")
                return False
            else:
                print(f"❌ Different error: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Direct chat test failed: {e}")
        return False


def main():
    """Run the full conversation evaluation test"""
    print("🧪 Full E2E Test: NPC0 Fix in Conversation Evaluation")
    print("=" * 70)
    print("Goal: Verify that the NPC0 formatting fix resolves the issue in practice")
    print("=" * 70)
    
    # Test NPC0 directly first
    direct_test_passed = test_npc0_direct_chat()
    
    # Test in conversation evaluation context
    conversation_test_passed = test_npc0_conversation_evaluation()
    
    print("\n" + "=" * 70)
    if direct_test_passed and conversation_test_passed:
        print("🎉 ALL TESTS PASSED!")
        print("The NPC0 formatting fix successfully resolved the issue.")
        print("NPC0 now works properly in conversation evaluations.")
    elif direct_test_passed:
        print("🔄 PARTIAL SUCCESS:")
        print("NPC0 direct chat works, but conversation evaluation had issues.")
        print("The formatting fix worked, but there may be other environment issues.")
    else:
        print("❌ TESTS FAILED:")
        print("The formatting fix did not resolve the issue.")
        print("Further investigation needed.")
    print("=" * 70)
    
    return direct_test_passed and conversation_test_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
