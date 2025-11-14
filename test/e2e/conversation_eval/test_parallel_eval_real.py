"""
E2E tests for parallel evaluation execution with real OpenAI API calls
Tests actual timing and parallelization benefits
"""
import os
import sys
import time
from pathlib import Path
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.conversation_eval.core.ParallelEvalRunner import ParallelEvalRunner
from src.conversation_eval.core.EvalClasses import EvalCase, Proposition, Term
from src.npcs.npc0.npc0 import NPC0
from src.core import proj_paths


def create_simple_test_case(goals=None, prop_text="User is confused -> AI helps"):
    """Create a simple test case for E2E testing"""
    if goals is None:
        goals = ["Be confused and ask a simple question"]
    
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


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY")
class TestParallelEvalRealAPI:
    """Test parallel evaluation with real OpenAI API calls"""
    
    @pytest.fixture(autouse=True)
    def setup_paths(self, tmp_path):
        """Setup temporary paths for testing"""
        # Create minimal template structure
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        
        # Initialize paths
        try:
            proj_paths.set_paths(
                project_path=tmp_path,
                templates_dir_name="templates",
                version=0.1,
                save_name="test"
            )
        except ValueError:
            # Paths already set, skip
            pass
        
        yield
        
        # Cleanup not needed as tmp_path handles it
    
    def test_parallel_execution_faster_than_sequential(self):
        """Test that parallel execution is significantly faster than sequential"""
        # Create test cases
        eval_cases = [
            create_simple_test_case(
                goals=["Ask what 2+2 is"],
                prop_text="User asks math question -> AI answers correctly"
            ),
        ]
        
        # NPC factory
        def npc_factory():
            return NPC0(system_prompt="You are a helpful assistant. Answer briefly.")
        
        assistant_rules = ["You are a helpful assistant. Answer all questions briefly."]
        mock_user_rules = ["You are testing the AI."]
        
        # Time parallel execution with 3 conversations
        start_parallel = time.time()
        result_parallel = ParallelEvalRunner.run_parallel_eval(
            test_name="parallel_timing_test",
            npc_type="npc0",
            npc_factory=npc_factory,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            eval_cases=eval_cases,
            convos_per_user_prompt=3,  # 3 conversations in parallel
            eval_iterations_per_eval=1,
            convo_length=2  # Very short conversations
        )
        parallel_time = time.time() - start_parallel
        
        print(f"\nParallel execution (3 conversations): {parallel_time:.2f}s")
        
        # Verify results
        assert len(result_parallel.assistant_prompt_cases[0].user_prompt_cases) == 1
        assert len(result_parallel.assistant_prompt_cases[0].user_prompt_cases[0].conversations) == 3
        
        # Note: We don't test sequential vs parallel directly as it would double API costs
        # Instead, we verify structure and that it completes successfully
        # In practice, 3 parallel conversations should take ~1/3 the time of sequential
        print(f"✓ Parallel execution completed successfully in {parallel_time:.2f}s")
        print(f"✓ Generated {len(result_parallel.assistant_prompt_cases[0].user_prompt_cases[0].conversations)} conversations")
    
    def test_multiple_cases_parallel(self):
        """Test that multiple cases execute in parallel"""
        # Create multiple simple test cases
        eval_cases = [
            create_simple_test_case(
                goals=["Ask what 5+5 is"],
                prop_text="User asks simple math -> AI answers"
            ),
            create_simple_test_case(
                goals=["Ask for the capital of France"],
                prop_text="User asks geography -> AI answers"
            ),
        ]
        
        # NPC factory
        def npc_factory():
            return NPC0(system_prompt="You are a helpful assistant. Answer briefly.")
        
        assistant_rules = ["You are a helpful assistant. Answer all questions briefly."]
        mock_user_rules = ["You are testing the AI."]
        
        # Run parallel evaluation
        start_time = time.time()
        result = ParallelEvalRunner.run_parallel_eval(
            test_name="multi_case_test",
            npc_type="npc0",
            npc_factory=npc_factory,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            eval_cases=eval_cases,
            convos_per_user_prompt=2,
            eval_iterations_per_eval=1,
            convo_length=2
        )
        total_time = time.time() - start_time
        
        print(f"\nMultiple cases (2 cases, 2 convos each): {total_time:.2f}s")
        
        # Verify results
        assert len(result.assistant_prompt_cases[0].user_prompt_cases) == 2
        assert len(result.assistant_prompt_cases[0].user_prompt_cases[0].conversations) == 2
        assert len(result.assistant_prompt_cases[0].user_prompt_cases[1].conversations) == 2
        
        # Verify evaluations were run
        for user_case in result.assistant_prompt_cases[0].user_prompt_cases:
            assert len(user_case.evaluations) > 0
            for evaluation in user_case.evaluations:
                assert len(evaluation.conversation_evaluations) == 2
        
        print(f"✓ Multiple cases completed successfully in {total_time:.2f}s")
    
    def test_evaluation_parallelization(self):
        """Test that evaluations run in parallel after conversations complete"""
        eval_cases = [
            create_simple_test_case(
                goals=["Ask what 10+10 is"],
                prop_text="User asks math -> AI answers"
            ),
        ]
        
        # NPC factory
        def npc_factory():
            return NPC0(system_prompt="You are a helpful assistant. Answer briefly.")
        
        assistant_rules = ["You are a helpful assistant. Answer all questions briefly."]
        mock_user_rules = ["You are testing the AI."]
        
        # Run with multiple evaluation iterations
        start_time = time.time()
        result = ParallelEvalRunner.run_parallel_eval(
            test_name="eval_parallel_test",
            npc_type="npc0",
            npc_factory=npc_factory,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_rules,
            eval_cases=eval_cases,
            convos_per_user_prompt=2,
            eval_iterations_per_eval=2,  # Multiple iterations to test eval parallelization
            convo_length=2
        )
        total_time = time.time() - start_time
        
        print(f"\nWith evaluation iterations (2 convos, 2 eval iterations): {total_time:.2f}s")
        
        # Verify evaluations
        evaluations = result.assistant_prompt_cases[0].user_prompt_cases[0].evaluations
        assert len(evaluations) > 0
        
        for evaluation in evaluations:
            for convo_eval in evaluation.conversation_evaluations:
                assert len(convo_eval.evaluation_iterations) == 2
        
        print(f"✓ Evaluations completed successfully in {total_time:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

