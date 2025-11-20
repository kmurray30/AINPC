"""
Unit tests for parallel evaluation execution with mocked LLM calls
Tests thread safety, result aggregation, and error handling
"""
import os
import sys
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.conversation_eval.core.TableTerminalUI import TableTerminalUI
from src.conversation_eval.core.ParallelEvalRunner import ParallelEvalRunner
from src.conversation_eval.core.EvalClasses import EvalCase, Proposition, Term
from src.core.Constants import PassFail
from src.core.ResponseTypes import EvaluationResponse


def create_mock_npc():
    """Create a mock NPC for testing"""
    mock_npc = Mock()
    mock_npc.chat = Mock(return_value="Test response")
    mock_npc.inject_memories = Mock()
    mock_npc.inject_conversation_history = Mock()
    return mock_npc


def create_test_eval_case(goals=None, prop_text="Test antecedent -> Test consequent"):
    """Create a test evaluation case"""
    if goals is None:
        goals = ["Test goal 1", "Test goal 2"]
    
    antecedent_text, consequent_text = prop_text.split(" -> ")
    
    return EvalCase(
        goals=goals,
        propositions=[
            Proposition(
                antecedent=Term(value=antecedent_text, negated=False),
                consequent=Term(value=consequent_text, negated=False),
                min_responses_for_consequent=1,
                max_responses_for_consequent=0,
                max_responses_for_antecedent=3
            )
        ]
    )


class TestTerminalUI:
    """Test TerminalUI line calculation and updates"""
    
    def test_line_mapping_calculation(self, capsys):
        """Test that line mappings are correctly calculated"""
        eval_cases = [
            create_test_eval_case(prop_text="Case 1 antecedent -> Case 1 consequent"),
            create_test_eval_case(prop_text="Case 2 antecedent -> Case 2 consequent"),
        ]
        
        ui = TerminalUI(
            test_name="test_terminal",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=2,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        # Verify line mappings exist for both cases
        assert 1 in ui.line_mappings
        assert 2 in ui.line_mappings
        
        # Verify each case has mappings for 2 conversations
        assert 1 in ui.line_mappings[1].conversations
        assert 2 in ui.line_mappings[1].conversations
        assert 1 in ui.line_mappings[2].conversations
        assert 2 in ui.line_mappings[2].conversations
        
        # Each conversation should have generating and evaluation line numbers
        gen_line, eval_line = ui.line_mappings[1].conversations[1]
        assert gen_line > 0
        assert eval_line > gen_line
    
    def test_update_conversation_progress_thread_safe(self):
        """Test that conversation progress updates are thread-safe"""
        eval_cases = [create_test_eval_case()]
        
        ui = TerminalUI(
            test_name="test_terminal",
            npc_type="npc0",
            eval_cases=eval_cases,
            convos_per_user_prompt=2,
            convo_length=5,
            eval_iterations_per_eval=1
        )
        
        # Simulate multiple threads updating progress
        def update_progress(case_idx, convo_idx):
            for i in range(1, 11):
                ui.update_conversation_progress(case_idx, convo_idx, i, 10)
                time.sleep(0.001)  # Small delay to simulate work
        
        threads = [
            threading.Thread(target=update_progress, args=(1, 1)),
            threading.Thread(target=update_progress, args=(1, 2)),
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # If we get here without deadlock or exceptions, thread safety is working


class TestParallelEvalRunner:
    """Test ParallelEvalRunner with mocked LLM calls"""
    
    @patch('src.conversation_eval.core.ConversationParsingBot.ConversationParsingBot.evaluate_conversation_timestamps')
    @patch('src.conversation_eval.core.EvalConversation.EvalConversation.converse')
    def test_parallel_conversation_generation(self, mock_converse, mock_evaluate):
        """Test that conversations are generated in parallel"""
        # Setup mocks
        mock_evaluate.return_value = EvaluationResponse(
            antecedent_explanation="Test",
            antecedent_times=[1],
            consequent_explanation="Test",
            consequent_times=[2]
        )
        
        # Track when each conversation starts/ends
        conversation_times = {}
        
        def mock_converse_side_effect(*args, **kwargs):
            thread_id = threading.current_thread().ident
            if thread_id not in conversation_times:
                conversation_times[thread_id] = []
            conversation_times[thread_id].append(('start', time.time()))
            time.sleep(0.1)  # Simulate work
            conversation_times[thread_id].append(('end', time.time()))
        
        mock_converse.side_effect = mock_converse_side_effect
        
        # Create test case with multiple conversations
        eval_cases = [create_test_eval_case()]
        
        # Run parallel evaluation
        npc_factory = lambda: create_mock_npc()
        
        start_time = time.time()
        ParallelEvalRunner.run_parallel_eval(
            test_name="test_parallel",
            npc_type="npc0",
            npc_factory=npc_factory,
            assistant_rules=["Test rule"],
            mock_user_base_rules=["Mock rule"],
            eval_cases=eval_cases,
            convos_per_user_prompt=3,
            eval_iterations_per_eval=1,
            convo_length=2
        )
        total_time = time.time() - start_time
        
        # Verify multiple threads were used (conversations ran in parallel)
        assert len(conversation_times) > 1, "Conversations should run in parallel threads"
        
        # Verify parallel execution is faster than sequential
        # 3 conversations * 0.1s each = 0.3s sequential, should be ~0.1s parallel
        assert total_time < 0.25, f"Parallel execution took {total_time}s, should be < 0.25s"
    
    @patch('src.conversation_eval.core.ConversationParsingBot.ConversationParsingBot.evaluate_conversation_timestamps')
    @patch('src.conversation_eval.core.EvalConversation.EvalConversation.converse')
    def test_parallel_cases_execution(self, mock_converse, mock_evaluate):
        """Test that cases are executed in parallel"""
        # Setup mocks
        mock_evaluate.return_value = EvaluationResponse(
            antecedent_explanation="Test",
            antecedent_times=[1],
            consequent_explanation="Test",
            consequent_times=[2]
        )
        
        # Track which cases run in which threads
        case_threads = {}
        
        def mock_converse_side_effect(*args, **kwargs):
            thread_id = threading.current_thread().ident
            case_threads[thread_id] = case_threads.get(thread_id, 0) + 1
            time.sleep(0.05)  # Simulate work
        
        mock_converse.side_effect = mock_converse_side_effect
        
        # Create multiple test cases
        eval_cases = [
            create_test_eval_case(prop_text="Case 1 -> Result 1"),
            create_test_eval_case(prop_text="Case 2 -> Result 2"),
            create_test_eval_case(prop_text="Case 3 -> Result 3"),
        ]
        
        # Run parallel evaluation
        npc_factory = lambda: create_mock_npc()
        
        start_time = time.time()
        result = ParallelEvalRunner.run_parallel_eval(
            test_name="test_parallel_cases",
            npc_type="npc0",
            npc_factory=npc_factory,
            assistant_rules=["Test rule"],
            mock_user_base_rules=["Mock rule"],
            eval_cases=eval_cases,
            convos_per_user_prompt=2,
            eval_iterations_per_eval=1,
            convo_length=2
        )
        total_time = time.time() - start_time
        
        # Verify multiple threads were used
        assert len(case_threads) > 1, "Cases should run in parallel threads"
        
        # Verify result has all cases
        assert len(result.assistant_prompt_cases[0].user_prompt_cases) == 3
        
        # Verify parallel execution is faster than sequential
        assert total_time < 0.3, f"Parallel execution took {total_time}s"
    
    @patch('src.conversation_eval.core.ConversationParsingBot.ConversationParsingBot.evaluate_conversation_timestamps')
    @patch('src.conversation_eval.core.EvalConversation.EvalConversation.converse')
    def test_error_handling_fail_fast(self, mock_converse, mock_evaluate):
        """Test that errors in one case stop execution (fail fast)"""
        # Setup mocks
        mock_evaluate.return_value = EvaluationResponse(
            antecedent_explanation="Test",
            antecedent_times=[1],
            consequent_explanation="Test",
            consequent_times=[2]
        )
        
        # Make one conversation fail
        call_count = [0]
        
        def mock_converse_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Fail on second conversation
                raise Exception("Test error in conversation")
            time.sleep(0.05)
        
        mock_converse.side_effect = mock_converse_side_effect
        
        # Create test cases
        eval_cases = [
            create_test_eval_case(),
            create_test_eval_case(),
        ]
        
        # Run parallel evaluation and expect exception
        npc_factory = lambda: create_mock_npc()
        
        with pytest.raises(Exception) as exc_info:
            ParallelEvalRunner.run_parallel_eval(
                test_name="test_error",
                npc_type="npc0",
                npc_factory=npc_factory,
                assistant_rules=["Test rule"],
                mock_user_base_rules=["Mock rule"],
                eval_cases=eval_cases,
                convos_per_user_prompt=2,
                eval_iterations_per_eval=1,
                convo_length=2
            )
        
        # Verify error message
        assert "Test error in conversation" in str(exc_info.value)
    
    @patch('src.conversation_eval.core.ConversationParsingBot.ConversationParsingBot.evaluate_conversation_timestamps')
    @patch('src.conversation_eval.core.EvalConversation.EvalConversation.converse')
    def test_result_aggregation(self, mock_converse, mock_evaluate):
        """Test that results from parallel execution are correctly aggregated"""
        # Setup mocks with varying evaluation results
        eval_results = [
            EvaluationResponse(
                antecedent_explanation="Passed",
                antecedent_times=[1],
                consequent_explanation="Passed",
                consequent_times=[2]
            ),
            EvaluationResponse(
                antecedent_explanation="Failed",
                antecedent_times=[1],
                consequent_explanation="Failed",
                consequent_times=[]
            ),
        ]
        
        call_count = [0]
        
        def mock_evaluate_side_effect(*args, **kwargs):
            result = eval_results[call_count[0] % len(eval_results)]
            call_count[0] += 1
            return result
        
        mock_evaluate.side_effect = mock_evaluate_side_effect
        
        # Create test cases
        eval_cases = [
            create_test_eval_case(prop_text="Case 1 -> Result 1"),
            create_test_eval_case(prop_text="Case 2 -> Result 2"),
        ]
        
        # Run parallel evaluation
        npc_factory = lambda: create_mock_npc()
        
        result = ParallelEvalRunner.run_parallel_eval(
            test_name="test_aggregation",
            npc_type="npc0",
            npc_factory=npc_factory,
            assistant_rules=["Test rule"],
            mock_user_base_rules=["Mock rule"],
            eval_cases=eval_cases,
            convos_per_user_prompt=2,
            eval_iterations_per_eval=2,
            convo_length=2
        )
        
        # Verify structure
        assert len(result.assistant_prompt_cases) == 1
        assert len(result.assistant_prompt_cases[0].user_prompt_cases) == 2
        
        # Verify each case has evaluations
        for user_case in result.assistant_prompt_cases[0].user_prompt_cases:
            assert len(user_case.evaluations) > 0
            assert len(user_case.conversations) == 2  # 2 conversations per case
    
    @patch('src.conversation_eval.core.ConversationParsingBot.ConversationParsingBot.evaluate_conversation_timestamps')
    @patch('src.conversation_eval.core.EvalConversation.EvalConversation.converse')
    def test_npc_factory_creates_new_instances(self, mock_converse, mock_evaluate):
        """Test that NPC factory creates separate instances for each thread"""
        # Setup mocks
        mock_evaluate.return_value = EvaluationResponse(
            antecedent_explanation="Test",
            antecedent_times=[1],
            consequent_explanation="Test",
            consequent_times=[2]
        )
        
        # Track NPC instances
        npc_instances = []
        
        def npc_factory():
            npc = create_mock_npc()
            npc._instance_id = id(npc)  # Track unique instance
            npc_instances.append(npc._instance_id)
            return npc
        
        # Create test case
        eval_cases = [create_test_eval_case()]
        
        # Run parallel evaluation with multiple conversations
        ParallelEvalRunner.run_parallel_eval(
            test_name="test_factory",
            npc_type="npc0",
            npc_factory=npc_factory,
            assistant_rules=["Test rule"],
            mock_user_base_rules=["Mock rule"],
            eval_cases=eval_cases,
            convos_per_user_prompt=3,
            eval_iterations_per_eval=1,
            convo_length=2
        )
        
        # Verify multiple unique NPC instances were created
        unique_instances = set(npc_instances)
        assert len(unique_instances) == 3, "Should create 3 unique NPC instances"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

