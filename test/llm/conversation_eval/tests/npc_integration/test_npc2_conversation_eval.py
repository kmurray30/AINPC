import os
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from src.conversation_eval.core.EvalClasses import Proposition, Term, EvalCase, EvalCaseSuite
from src.conversation_eval.core.EvalHelper import EvalHelper
from src.npcs.npc2.npc2 import NPC2
from src.core import proj_paths, proj_settings
from src.utils import io_utils


class TestNPC2ConversationEval:
    """Test NPC2 integration with conversation evaluation system"""
    
    def setup_method(self):
        """Set up test environment for each test"""
        # Reset singleton states
        import src.core.proj_paths as proj_paths_module
        import src.core.proj_settings as proj_settings_module
        
        proj_paths_module._paths = None
        proj_paths_module._frozen = False
        proj_settings_module._settings = None
        proj_settings_module._frozen = False
        
        # Set up test paths
        self.test_dir = Path(__file__).parent
        self.template_dir = self.test_dir / "templates" / "npc2"
        
        proj_paths.set_paths(
            project_path=self.template_dir,
            templates_dir_name="templates",
            version=2.0,
            save_name="test_npc2"
        )
        
        proj_settings.init_settings(self.template_dir / "templates" / "game_settings.yaml")
        
        # Create NPC2 instance with saving disabled
        self.npc2 = NPC2(npc_name_for_template_and_save="test_assistant", save_enabled=False)
    
    def test_npc2_basic_conversation_generation(self):
        """Test that NPC2 can generate conversations in evaluation framework"""
        assistant_rules = ["You are a helpful assistant with memory capabilities"]
        mock_user_rules = ["You are a test user asking questions"]
        
        # Generate a simple conversation
        conversation_map = EvalHelper.generate_conversations_with_npc(
            assistant_npc=self.npc2,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            mock_user_goals=["Ask about the assistant's capabilities"],
            convos_per_user_prompt=1,
            convo_length=2
        )
        
        # Verify conversation was generated
        assert len(conversation_map) == 1
        assert "Conversation 1" in conversation_map
        
        conversation = conversation_map["Conversation 1"]
        assert len(conversation) >= 4  # At least 2 exchanges (4 messages)
        
        # Verify both agents participated
        pat_messages = [msg for msg in conversation if "Pat:" in msg]
        user_messages = [msg for msg in conversation if "Mock User:" in msg]
        
        assert len(pat_messages) >= 1, "NPC2 should have generated at least one response"
        assert len(user_messages) >= 1, "Mock user should have generated at least one response"
    
    def test_npc2_evaluation_with_complex_proposition(self):
        """Test NPC2 with a more complex evaluation proposition"""
        assistant_rules = [
            "You are a helpful assistant that processes user input",
            "When users ask about memory, explain your capabilities"
        ]
        mock_user_rules = ["You are a test user"]
        
        test_suite = EvalCaseSuite(
            eval_cases=[
                EvalCase(
                    goals=["Ask the assistant about its memory capabilities"],
                    propositions=[Proposition(
                        antecedent=Term("The user asks about memory"),
                        consequent=Term("The assistant explains its capabilities")
                    )]
                )
            ]
        )
        
        # Run evaluation
        eval_report = EvalHelper.run_conversation_eval_with_npc(
            assistant_npc=self.npc2,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            test_suite=test_suite,
            convos_per_user_prompt=1,
            eval_iterations_per_eval=1,
            convo_length=2
        )
        
        # Verify evaluation completed
        assert eval_report is not None
        assert len(eval_report.assistant_prompt_cases) == 1
        assert len(eval_report.assistant_prompt_cases[0].user_prompt_cases) == 1
        
        user_case = eval_report.assistant_prompt_cases[0].user_prompt_cases[0]
        assert len(user_case.evaluations) == 1
    
    def test_npc2_preprocessing_functionality(self):
        """Test that NPC2's preprocessing functionality works during evaluation"""
        assistant_rules = ["You are an assistant that processes user input carefully"]
        mock_user_rules = ["You are a test user"]
        
        # Generate conversation that should trigger preprocessing
        conversation_map = EvalHelper.generate_conversations_with_npc(
            assistant_npc=self.npc2,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            mock_user_goals=["Ask a complex question with multiple parts"],
            convos_per_user_prompt=1,
            convo_length=2
        )
        
        conversation = conversation_map["Conversation 1"]
        
        # Verify conversation was generated (preprocessing should not break the flow)
        assert len(conversation) >= 4
        
        # Verify NPC2 responded appropriately
        pat_messages = [msg for msg in conversation if "Pat:" in msg]
        assert len(pat_messages) >= 1
        
        # Check that responses are substantive (not just error messages)
        for pat_msg in pat_messages:
            content = pat_msg.split("Pat:", 1)[1].strip()
            assert len(content) > 10, f"Pat response should be substantive: {content}"
    
    def test_npc2_memory_disabled_during_evaluation(self):
        """Test that NPC2's memory system is disabled during evaluation"""
        # Verify the NPC was created with saving disabled
        assert self.npc2.save_enabled == False, "NPC2 should have saving disabled for evaluation"
        
        # Verify brain memory is also disabled
        assert self.npc2.brain_memory.save_enabled == False, "Brain memory should be disabled"
        
        # Generate conversation and verify memory operations are skipped
        assistant_rules = ["You are a test assistant"]
        mock_user_rules = ["You are a test user"]
        
        conversation_map = EvalHelper.generate_conversations_with_npc(
            assistant_npc=self.npc2,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            mock_user_goals=["Tell the assistant something to remember"],
            convos_per_user_prompt=1,
            convo_length=2
        )
        
        # Conversation should still work despite disabled memory
        assert len(conversation_map) == 1
        conversation = conversation_map["Conversation 1"]
        assert len(conversation) >= 4
    
    def test_npc2_handles_no_user_message_start(self):
        """Test that NPC2 can handle starting a conversation without user input"""
        assistant_rules = ["You are a proactive assistant that can start conversations"]
        mock_user_rules = ["You are a responsive test user"]
        
        # This should work without errors
        conversation_map = EvalHelper.generate_conversations_with_npc(
            assistant_npc=self.npc2,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            mock_user_goals=["Respond to the assistant's greeting"],
            convos_per_user_prompt=1,
            convo_length=1
        )
        
        assert len(conversation_map) == 1
        conversation = conversation_map["Conversation 1"]
        assert len(conversation) >= 2  # At least one exchange
        
        # First message should be from Pat (NPC2)
        first_message = conversation[0]
        assert "Pat:" in first_message, f"First message should be from Pat, got: {first_message}"
    
    def test_npc2_longer_conversation_flow(self):
        """Test NPC2 with longer conversations to verify stability"""
        assistant_rules = ["You are a conversational assistant that engages with users"]
        mock_user_rules = ["You are an engaged test user"]
        
        # Generate a longer conversation
        conversation_map = EvalHelper.generate_conversations_with_npc(
            assistant_npc=self.npc2,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            mock_user_goals=["Have an extended conversation about various topics"],
            convos_per_user_prompt=1,
            convo_length=4  # 4 exchanges = 8 messages
        )
        
        conversation = conversation_map["Conversation 1"]
        
        # Verify conversation length
        assert len(conversation) >= 8, f"Expected at least 8 messages, got {len(conversation)}"
        
        # Verify alternating pattern
        pat_indices = [i for i, msg in enumerate(conversation) if "Pat:" in msg]
        user_indices = [i for i, msg in enumerate(conversation) if "Mock User:" in msg]
        
        assert len(pat_indices) >= 4, "Should have at least 4 Pat messages"
        assert len(user_indices) >= 4, "Should have at least 4 User messages"
        
        # Verify no empty responses (allow for initial empty response when starting conversation)
        pat_messages = [msg for msg in conversation if "Pat:" in msg]
        non_empty_pat_messages = []
        for msg in pat_messages:
            content = msg.split("Pat:", 1)[1].strip()
            if len(content) > 0:
                non_empty_pat_messages.append(msg)
        
        # Should have at least some non-empty Pat responses
        assert len(non_empty_pat_messages) >= 3, f"Should have at least 3 non-empty Pat responses, got {len(non_empty_pat_messages)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
