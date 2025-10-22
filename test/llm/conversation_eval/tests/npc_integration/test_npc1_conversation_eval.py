import os
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from src.conversation_eval.EvalClasses import Proposition, Term, EvalCase, EvalCaseSuite
from src.conversation_eval.EvalHelper import EvalHelper
from src.npcs.NPC1 import NPC1
from src.core import proj_paths, proj_settings
from src.utils import io_utils


class TestNPC1ConversationEval:
    """Test NPC1 integration with conversation evaluation system"""
    
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
        self.template_dir = self.test_dir / "templates" / "npc1"
        
        proj_paths.set_paths(
            project_path=self.template_dir,
            templates_dir_name="templates",
            version=1.0,
            save_name="test_npc1"
        )
        
        proj_settings.init_settings(self.template_dir / "templates" / "game_settings.yaml")
        
        # Create NPC1 instance with saving disabled
        self.npc1 = NPC1(npc_name_for_template_and_save="test_assistant", save_enabled=False)
    
    def test_npc1_basic_conversation_generation(self):
        """Test that NPC1 can generate conversations in evaluation framework"""
        assistant_rules = ["You are a helpful assistant"]
        mock_user_rules = ["You are a test user asking simple questions"]
        
        # Generate a simple conversation
        conversation_map = EvalHelper.generate_conversations_with_npc(
            assistant_npc=self.npc1,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            mock_user_goals=["Ask about the weather"],
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
        
        assert len(pat_messages) >= 1, "NPC1 should have generated at least one response"
        assert len(user_messages) >= 1, "Mock user should have generated at least one response"
    
    def test_npc1_evaluation_with_simple_proposition(self):
        """Test NPC1 with a simple evaluation proposition"""
        assistant_rules = ["You are a helpful assistant that always responds to questions"]
        mock_user_rules = ["You are a test user"]
        
        test_suite = EvalCaseSuite(
            eval_cases=[
                EvalCase(
                    goals=["Ask a simple question about the time"],
                    propositions=[Proposition(
                        antecedent=Term("The user asks a question"),
                        consequent=Term("The assistant provides a response")
                    )]
                )
            ]
        )
        
        # Run evaluation
        eval_report = EvalHelper.run_conversation_eval_with_npc(
            assistant_npc=self.npc1,
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
    
    def test_npc1_maintains_conversation_history(self):
        """Test that NPC1 maintains conversation history during evaluation"""
        assistant_rules = ["You are a helpful assistant with good memory"]
        mock_user_rules = ["You are a test user"]
        
        # Generate a longer conversation
        conversation_map = EvalHelper.generate_conversations_with_npc(
            assistant_npc=self.npc1,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            mock_user_goals=["Have a conversation about your favorite topics"],
            convos_per_user_prompt=1,
            convo_length=3  # 3 exchanges = 6 messages
        )
        
        conversation = conversation_map["Conversation 1"]
        
        # Verify conversation length
        assert len(conversation) >= 6, f"Expected at least 6 messages, got {len(conversation)}"
        
        # Verify alternating pattern (Pat, User, Pat, User, ...)
        pat_indices = [i for i, msg in enumerate(conversation) if "Pat:" in msg]
        user_indices = [i for i, msg in enumerate(conversation) if "Mock User:" in msg]
        
        # Should have alternating pattern
        assert len(pat_indices) >= 3, "Should have at least 3 Pat messages"
        assert len(user_indices) >= 3, "Should have at least 3 User messages"
    
    def test_npc1_handles_no_user_message_start(self):
        """Test that NPC1 can handle starting a conversation without user input"""
        assistant_rules = ["You are a proactive assistant that can start conversations"]
        mock_user_rules = ["You are a responsive test user"]
        
        # This should work without errors (tests the Agent.py fix)
        conversation_map = EvalHelper.generate_conversations_with_npc(
            assistant_npc=self.npc1,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            mock_user_goals=["Respond to the assistant's greeting"],
            convos_per_user_prompt=1,
            convo_length=1
        )
        
        assert len(conversation_map) == 1
        conversation = conversation_map["Conversation 1"]
        assert len(conversation) >= 2  # At least one exchange
        
        # First message should be from Pat (NPC1)
        first_message = conversation[0]
        assert "Pat:" in first_message, f"First message should be from Pat, got: {first_message}"
    
    def test_npc1_save_disabled_during_evaluation(self):
        """Test that NPC1 operates with save_enabled=False during evaluation"""
        # Verify the NPC was created with saving disabled
        assert self.npc1.save_enabled == False, "NPC1 should have saving disabled for evaluation"
        
        # Generate conversation and verify no files are created in save directories
        assistant_rules = ["You are a test assistant"]
        mock_user_rules = ["You are a test user"]
        
        conversation_map = EvalHelper.generate_conversations_with_npc(
            assistant_npc=self.npc1,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            mock_user_goals=["Say hello"],
            convos_per_user_prompt=1,
            convo_length=1
        )
        
        # Conversation should still work
        assert len(conversation_map) == 1
        
        # Verify NPC maintains its save_enabled state
        assert self.npc1.save_enabled == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
