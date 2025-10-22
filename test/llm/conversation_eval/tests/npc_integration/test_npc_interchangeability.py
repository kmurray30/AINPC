import os
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from src.conversation_eval.EvalClasses import Proposition, Term, EvalCase, EvalCaseSuite
from src.conversation_eval.EvalHelper import EvalHelper
from src.npcs.NPC1 import NPC1
from src.npcs.NPC2 import NPC2
from src.core import proj_paths, proj_settings


class TestNPCInterchangeability:
    """Test that NPC1 and NPC2 can be used interchangeably in conversation evaluation"""
    
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
    
    def run_standard_evaluation(self, npc_instance):
        """Run a standard evaluation with the given NPC instance"""
        assistant_rules = ["You are a helpful assistant that responds to user questions"]
        mock_user_rules = ["You are a test user asking questions"]
        
        test_suite = EvalCaseSuite(
            eval_cases=[
                EvalCase(
                    goals=["Ask the assistant a simple question"],
                    propositions=[Proposition(
                        antecedent=Term("The user asks a question"),
                        consequent=Term("The assistant provides a helpful response")
                    )]
                )
            ]
        )
        
        return EvalHelper.run_conversation_eval_with_npc(
            assistant_npc=npc_instance,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            test_suite=test_suite,
            convos_per_user_prompt=1,
            eval_iterations_per_eval=1,
            convo_length=2
        )
    
    def test_both_npcs_generate_conversations(self):
        """Test that both NPC1 and NPC2 can generate conversations"""
        # Test NPC1
        npc1 = self.setup_npc_environment("npc1")
        eval_report_1 = self.run_standard_evaluation(npc1)
        
        # Test NPC2
        npc2 = self.setup_npc_environment("npc2")
        eval_report_2 = self.run_standard_evaluation(npc2)
        
        # Both should complete successfully
        assert eval_report_1 is not None, "NPC1 evaluation should complete"
        assert eval_report_2 is not None, "NPC2 evaluation should complete"
        
        # Both should have the same structure
        assert len(eval_report_1.assistant_prompt_cases) == 1
        assert len(eval_report_2.assistant_prompt_cases) == 1
        
        assert len(eval_report_1.assistant_prompt_cases[0].user_prompt_cases) == 1
        assert len(eval_report_2.assistant_prompt_cases[0].user_prompt_cases) == 1
    
    def test_both_npcs_handle_conversation_flow(self):
        """Test that both NPCs handle the same conversation flow correctly"""
        assistant_rules = ["You are a friendly assistant"]
        mock_user_rules = ["You are a polite test user"]
        mock_user_goals = ["Greet the assistant and ask how they are doing"]
        
        # Test NPC1
        npc1 = self.setup_npc_environment("npc1")
        conversation_map_1 = EvalHelper.generate_conversations_with_npc(
            assistant_npc=npc1,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            mock_user_goals=mock_user_goals,
            convos_per_user_prompt=1,
            convo_length=2
        )
        
        # Test NPC2
        npc2 = self.setup_npc_environment("npc2")
        conversation_map_2 = EvalHelper.generate_conversations_with_npc(
            assistant_npc=npc2,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            mock_user_goals=mock_user_goals,
            convos_per_user_prompt=1,
            convo_length=2
        )
        
        # Both should generate conversations
        assert len(conversation_map_1) == 1
        assert len(conversation_map_2) == 1
        
        conv1 = conversation_map_1["Conversation 1"]
        conv2 = conversation_map_2["Conversation 1"]
        
        # Both should have similar structure
        assert len(conv1) >= 4, "NPC1 conversation should have at least 4 messages"
        assert len(conv2) >= 4, "NPC2 conversation should have at least 4 messages"
        
        # Both should have Pat and Mock User messages
        pat_msgs_1 = [msg for msg in conv1 if "Pat:" in msg]
        user_msgs_1 = [msg for msg in conv1 if "Mock User:" in msg]
        pat_msgs_2 = [msg for msg in conv2 if "Pat:" in msg]
        user_msgs_2 = [msg for msg in conv2 if "Mock User:" in msg]
        
        assert len(pat_msgs_1) >= 2, "NPC1 should generate Pat messages"
        assert len(user_msgs_1) >= 2, "NPC1 conversation should have User messages"
        assert len(pat_msgs_2) >= 2, "NPC2 should generate Pat messages"
        assert len(user_msgs_2) >= 2, "NPC2 conversation should have User messages"
    
    def test_both_npcs_work_with_complex_evaluations(self):
        """Test both NPCs with more complex evaluation scenarios"""
        assistant_rules = [
            "You are a helpful assistant",
            "When users ask about capabilities, explain what you can do",
            "When users become frustrated, try to help them"
        ]
        mock_user_rules = ["You are a test user with specific needs"]
        
        test_suite = EvalCaseSuite(
            eval_cases=[
                EvalCase(
                    goals=["Ask about the assistant's capabilities and then express some frustration"],
                    propositions=[
                        Proposition(
                            antecedent=Term("The user asks about capabilities"),
                            consequent=Term("The assistant explains its abilities")
                        ),
                        Proposition(
                            antecedent=Term("The user expresses frustration"),
                            consequent=Term("The assistant tries to help")
                        )
                    ]
                )
            ]
        )
        
        # Test both NPCs with the same complex evaluation
        npc1 = self.setup_npc_environment("npc1")
        eval_report_1 = EvalHelper.run_conversation_eval_with_npc(
            assistant_npc=npc1,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            test_suite=test_suite,
            convos_per_user_prompt=1,
            eval_iterations_per_eval=1,
            convo_length=3
        )
        
        npc2 = self.setup_npc_environment("npc2")
        eval_report_2 = EvalHelper.run_conversation_eval_with_npc(
            assistant_npc=npc2,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            test_suite=test_suite,
            convos_per_user_prompt=1,
            eval_iterations_per_eval=1,
            convo_length=3
        )
        
        # Both should handle the complex evaluation
        assert eval_report_1 is not None
        assert eval_report_2 is not None
        
        # Both should evaluate the same number of propositions
        user_case_1 = eval_report_1.assistant_prompt_cases[0].user_prompt_cases[0]
        user_case_2 = eval_report_2.assistant_prompt_cases[0].user_prompt_cases[0]
        
        assert len(user_case_1.evaluations) == 2  # Two propositions evaluated
        assert len(user_case_2.evaluations) == 2  # Two propositions evaluated
    
    def test_npc_protocol_interface_compliance(self):
        """Test that both NPCs properly implement the NPCProtocol interface"""
        # Test NPC1
        npc1 = self.setup_npc_environment("npc1")
        
        # Test required methods exist and work
        assert hasattr(npc1, 'chat'), "NPC1 should have chat method"
        assert hasattr(npc1, 'inject_message'), "NPC1 should have inject_message method"
        assert hasattr(npc1, 'maintain'), "NPC1 should have maintain method"
        assert hasattr(npc1, 'get_all_memories'), "NPC1 should have get_all_memories method"
        
        # Test NPC2
        npc2 = self.setup_npc_environment("npc2")
        
        assert hasattr(npc2, 'chat'), "NPC2 should have chat method"
        assert hasattr(npc2, 'inject_message'), "NPC2 should have inject_message method"
        assert hasattr(npc2, 'maintain'), "NPC2 should have maintain method"
        assert hasattr(npc2, 'get_all_memories'), "NPC2 should have get_all_memories method"
        
        # Test that chat method works for both
        response1 = npc1.chat("Hello, how are you?")
        response2 = npc2.chat("Hello, how are you?")
        
        assert response1 is not None, "NPC1 should return a response"
        assert response2 is not None, "NPC2 should return a response"
        assert hasattr(response1, 'response'), "NPC1 response should have response attribute"
        assert hasattr(response2, 'response'), "NPC2 response should have response attribute"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
