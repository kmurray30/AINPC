import os
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from src.conversation_eval.Conversation import Conversation
from src.conversation_eval.EvalAgent import EvalAgent
from src.core.Constants import AgentName
from src.npcs.NPC1 import NPC1
from src.npcs.NPC2 import NPC2
from src.core import proj_paths, proj_settings


class TestConversationFrameworkIntegration:
    """Test the integration of NPCs with the conversation evaluation framework components"""
    
    def setup_npc_environment(self, npc_type: str):
        """Set up test environment for specified NPC type"""
        # Reset singleton states
        import src.core.proj_paths as proj_paths_module
        import src.core.proj_settings as proj_settings_module
        
        proj_paths_module._paths = None
        proj_paths_module._frozen = False
        proj_settings_module._settings = None
        proj_settings_module._frozen = False
        
        # Set up test paths
        test_dir = Path(__file__).parent
        template_dir = test_dir / "templates" / npc_type
        
        version = 1.0 if npc_type == "npc1" else 2.0
        
        proj_paths.set_paths(
            project_path=template_dir,
            templates_dir_name="templates",
            version=version,
            save_name=f"test_{npc_type}"
        )
        
        proj_settings.init_settings(template_dir / "templates" / "game_settings.yaml")
        
        # Create appropriate NPC instance
        if npc_type == "npc1":
            return NPC1(npc_name_for_template_and_save="test_assistant", save_enabled=False)
        else:
            return NPC2(npc_name_for_template_and_save="test_assistant", save_enabled=False)
    
    def test_eval_agent_npc_integration(self):
        """Test EvalAgent integration with NPC protocols"""
        npc1 = self.setup_npc_environment("npc1")
        
        # Create EvalAgent with NPC protocol
        agent_rules = ["You are a test assistant"]
        eval_agent = EvalAgent(AgentName.pat, "\n".join(agent_rules), npc1)
        
        # Test EvalAgent methods
        assert eval_agent.is_npc_backed() == True, "Agent should be NPC-backed"
        assert eval_agent.npc_protocol == npc1, "Agent should reference the NPC"
        
        # Test chat functionality
        response = eval_agent.chat_with_npc("Hello, how are you?")
        assert response is not None, "Agent should return a response"
        assert hasattr(response, 'response'), "Response should have response attribute"
        
        # Test inject message functionality
        from src.core.Constants import Role
        eval_agent.inject_message_to_npc("Test message", Role.user)
        
        # Test maintenance
        eval_agent.maintain_npc()  # Should not raise errors
    
    def test_conversation_add_agent_with_npc_protocol(self):
        """Test Conversation.add_agent_with_npc_protocol method"""
        npc2 = self.setup_npc_environment("npc2")
        
        conversation = Conversation()
        agent_rules = ["You are a helpful assistant"]
        
        # Add NPC-backed agent
        agent = conversation.add_agent_with_npc_protocol(
            AgentName.pat, 
            agent_rules, 
            npc2
        )
        
        # Verify agent was added correctly
        assert agent is not None, "Agent should be returned"
        assert agent.is_npc_backed() == True, "Agent should be NPC-backed"
        assert AgentName.pat in conversation.agents, "Agent should be in conversation"
        assert conversation.agents[AgentName.pat] == agent, "Agent should be stored correctly"
    
    def test_conversation_mixed_agent_types(self):
        """Test Conversation with both NPC-backed and simple agents"""
        npc1 = self.setup_npc_environment("npc1")
        
        conversation = Conversation()
        
        # Add NPC-backed agent
        npc_agent = conversation.add_agent_with_npc_protocol(
            AgentName.pat,
            ["You are an NPC-backed assistant"],
            npc1
        )
        
        # Add simple agent
        conversation.add_agent_simple(
            AgentName.mock_user,
            ["You are a simple test user", "Ask questions about the assistant"]
        )
        
        # Verify both agents exist
        assert AgentName.pat in conversation.agents
        assert AgentName.mock_user in conversation.agents
        
        # Verify agent types
        assert conversation.agents[AgentName.pat].is_npc_backed() == True
        assert conversation.agents[AgentName.mock_user].is_npc_backed() == False
    
    def test_conversation_call_agent_npc_backed(self):
        """Test Conversation.call_agent with NPC-backed agents"""
        npc2 = self.setup_npc_environment("npc2")
        
        conversation = Conversation()
        
        # Add NPC-backed agent
        conversation.add_agent_with_npc_protocol(
            AgentName.pat,
            ["You are a helpful assistant"],
            npc2
        )
        
        # Add simple agent
        conversation.add_agent_simple(
            AgentName.mock_user,
            ["You are a test user"]
        )
        
        # Test calling NPC-backed agent first (no prior messages)
        conversation.call_agent(AgentName.pat, AgentName.mock_user, False, isPrinting=False)
        
        # Verify message was added to history
        assert len(conversation.message_history) == 1
        assert conversation.message_history[0].agent == AgentName.pat
        
        # Test calling simple agent in response
        conversation.call_agent(AgentName.mock_user, AgentName.pat, False, isPrinting=False)
        
        # Verify both messages in history
        assert len(conversation.message_history) == 2
        assert conversation.message_history[1].agent == AgentName.mock_user
    
    def test_conversation_converse_with_npc(self):
        """Test full conversation flow with NPC-backed agent"""
        npc1 = self.setup_npc_environment("npc1")
        
        conversation = Conversation()
        
        # Add agents
        conversation.add_agent_with_npc_protocol(
            AgentName.pat,
            ["You are a conversational assistant"],
            npc1
        )
        
        conversation.add_agent_simple(
            AgentName.mock_user,
            ["You are a friendly test user", "Engage in conversation"]
        )
        
        # Run conversation
        conversation.converse(AgentName.pat, AgentName.mock_user, iterations=2, isPrinting=False)
        
        # Verify conversation occurred
        assert len(conversation.message_history) == 4  # 2 iterations * 2 agents
        
        # Verify alternating pattern
        assert conversation.message_history[0].agent == AgentName.pat
        assert conversation.message_history[1].agent == AgentName.mock_user
        assert conversation.message_history[2].agent == AgentName.pat
        assert conversation.message_history[3].agent == AgentName.mock_user
        
        # Verify messages have content
        for msg in conversation.message_history:
            assert len(msg.content.strip()) > 0, f"Message should have content: {msg.content}"
    
    def test_conversation_history_management(self):
        """Test that conversation history is properly managed with NPC agents"""
        npc2 = self.setup_npc_environment("npc2")
        
        conversation = Conversation()
        
        # Add NPC-backed agent
        conversation.add_agent_with_npc_protocol(
            AgentName.pat,
            ["You are a memory-capable assistant"],
            npc2
        )
        
        # Add simple agent
        conversation.add_agent_simple(
            AgentName.mock_user,
            ["You are a test user"]
        )
        
        # Run multiple conversation turns
        conversation.converse(AgentName.pat, AgentName.mock_user, iterations=3, isPrinting=False)
        
        # Verify conversation history in framework
        framework_history = conversation.get_message_history_as_list()
        assert len(framework_history) == 6  # 3 iterations * 2 agents
        
        # Verify NPC also maintains its own history
        # (This is handled internally by the NPC, but we can verify it doesn't interfere)
        assert len(conversation.message_history) == 6
    
    def test_npc_state_isolation_between_conversations(self):
        """Test that NPCs maintain proper state isolation between different conversations"""
        npc1 = self.setup_npc_environment("npc1")
        
        # First conversation
        conversation1 = Conversation()
        conversation1.add_agent_with_npc_protocol(
            AgentName.pat,
            ["You are assistant #1"],
            npc1
        )
        conversation1.add_agent_simple(
            AgentName.mock_user,
            ["You are user #1"]
        )
        
        conversation1.converse(AgentName.pat, AgentName.mock_user, iterations=1, isPrinting=False)
        history1_length = len(conversation1.message_history)
        
        # Second conversation with same NPC
        conversation2 = Conversation()
        conversation2.add_agent_with_npc_protocol(
            AgentName.pat,
            ["You are assistant #2"],
            npc1
        )
        conversation2.add_agent_simple(
            AgentName.mock_user,
            ["You are user #2"]
        )
        
        conversation2.converse(AgentName.pat, AgentName.mock_user, iterations=1, isPrinting=False)
        history2_length = len(conversation2.message_history)
        
        # Verify conversations are independent
        assert history1_length == 2, "First conversation should have 2 messages"
        assert history2_length == 2, "Second conversation should have 2 messages"
        
        # Verify conversation histories are separate
        assert conversation1.message_history != conversation2.message_history


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
