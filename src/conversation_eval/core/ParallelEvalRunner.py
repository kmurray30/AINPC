"""
Parallel Evaluation Runner
Orchestrates concurrent execution of evaluation cases and conversations
"""
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable
from dataclasses import dataclass

sys.path.insert(0, "../..")

from src.conversation_eval.core.TerminalUI import TerminalUI
from src.conversation_eval.core.EvalConversation import EvalConversation
from src.conversation_eval.core.ConversationParsingBot import ConversationParsingBot
from src.conversation_eval.core.EvalClasses import EvalCase, Proposition
from src.conversation_eval.core.EvalReports import (
    EvalReport, AssistantPromptEvalReport, UserPromptEvalReport,
    EvaluationEvalReport, ConversationEvaluationEvalReport, EvaluationIterationEvalReport
)
from src.conversation_eval.core.EvalHelper import EvalHelper
from src.core.Constants import AgentName
from src.core.ResponseTypes import EvaluationResponse
from src.npcs.npc_protocol import NPCProtocol
from src.utils import Utilities


@dataclass
class ConversationResult:
    """Result from a single conversation generation"""
    conversation_name: str
    conversation: List[str]
    case_idx: int
    convo_idx: int


@dataclass
class EvaluationResult:
    """Result from a single conversation evaluation"""
    conversation_name: str
    evaluation_report: EvaluationEvalReport
    case_idx: int
    convo_idx: int


class ParallelEvalRunner:
    """
    Manages parallel execution of evaluation cases with real-time terminal updates.
    """
    
    @staticmethod
    def run_parallel_eval(
        test_name: str,
        npc_type: str,
        npc_factory: Callable[[], NPCProtocol],
        assistant_rules: List[str],
        mock_user_base_rules: List[str],
        eval_cases: List[EvalCase],
        convos_per_user_prompt: int,
        eval_iterations_per_eval: int,
        convo_length: int
    ) -> EvalReport:
        """
        Run evaluation with parallel execution of cases and conversations.
        
        Args:
            test_name: Name of the test
            npc_type: Type of NPC being tested
            npc_factory: Factory function to create NPC instances (for thread safety)
            assistant_rules: Rules for the assistant
            mock_user_base_rules: Base rules for mock user
            eval_cases: List of evaluation cases
            convos_per_user_prompt: Number of conversations per case
            eval_iterations_per_eval: Number of evaluation iterations
            convo_length: Length of each conversation
            
        Returns:
            Complete evaluation report
        """
        # Initialize terminal UI
        ui = TerminalUI(
            test_name=test_name,
            npc_type=npc_type,
            eval_cases=eval_cases,
            convos_per_user_prompt=convos_per_user_prompt,
            convo_length=convo_length,
            eval_iterations_per_eval=eval_iterations_per_eval
        )
        
        # Create main report structure
        assistant_prompt_report = AssistantPromptEvalReport(
            assistant_prompt=Utilities.decode_list(assistant_rules),
            deltas=[],
            user_prompt_cases=[],
            tokens=0
        )
        eval_report = EvalReport(
            assistant_prompt_cases=[assistant_prompt_report],
            takeaways="",
            tokens=0
        )
        
        # Run cases in parallel
        with ThreadPoolExecutor(max_workers=len(eval_cases)) as case_executor:
            case_futures = []
            
            for case_idx, eval_case in enumerate(eval_cases, 1):
                future = case_executor.submit(
                    ParallelEvalRunner._run_single_case,
                    case_idx=case_idx,
                    eval_case=eval_case,
                    ui=ui,
                    npc_factory=npc_factory,
                    assistant_rules=assistant_rules,
                    mock_user_base_rules=mock_user_base_rules,
                    convos_per_user_prompt=convos_per_user_prompt,
                    eval_iterations_per_eval=eval_iterations_per_eval,
                    convo_length=convo_length
                )
                case_futures.append((case_idx, future))
            
            # Collect results (fail fast on any error)
            case_reports = {}
            for case_idx, future in case_futures:
                try:
                    user_prompt_report = future.result()
                    case_reports[case_idx] = user_prompt_report
                except Exception as e:
                    # Move cursor to end before printing error
                    ui.move_cursor_to_end()
                    raise Exception(f"Error in Case {case_idx}: {str(e)}") from e
            
            # Add reports in order
            for case_idx in sorted(case_reports.keys()):
                assistant_prompt_report.user_prompt_cases.append(case_reports[case_idx])
                eval_report.tokens += case_reports[case_idx].tokens
        
        # Move cursor to end for final messages
        ui.move_cursor_to_end()
        
        return eval_report
    
    @staticmethod
    def _run_single_case(
        case_idx: int,
        eval_case: EvalCase,
        ui: TerminalUI,
        npc_factory: Callable[[], NPCProtocol],
        assistant_rules: List[str],
        mock_user_base_rules: List[str],
        convos_per_user_prompt: int,
        eval_iterations_per_eval: int,
        convo_length: int
    ) -> UserPromptEvalReport:
        """
        Run a single evaluation case with parallel conversations and evaluations.
        
        Args:
            case_idx: Case index (1-indexed)
            eval_case: The evaluation case to run
            ui: Terminal UI manager
            npc_factory: Factory to create NPC instances
            assistant_rules: Rules for assistant
            mock_user_base_rules: Base rules for mock user
            convos_per_user_prompt: Number of conversations
            eval_iterations_per_eval: Number of evaluation iterations
            convo_length: Conversation length
            
        Returns:
            User prompt evaluation report for this case
        """
        # Create report for this case
        user_prompt_report = UserPromptEvalReport(
            user_prompt=Utilities.decode_list(eval_case.goals),
            conversations={},
            evaluations=[],
            tokens=0
        )
        
        # Step 1: Generate all conversations in parallel
        conversation_results = ParallelEvalRunner._generate_conversations_parallel(
            case_idx=case_idx,
            eval_case=eval_case,
            ui=ui,
            npc_factory=npc_factory,
            assistant_rules=assistant_rules,
            mock_user_base_rules=mock_user_base_rules,
            convos_per_user_prompt=convos_per_user_prompt,
            convo_length=convo_length
        )
        
        # Build conversation map
        conversation_map = {}
        for result in conversation_results:
            conversation_map[result.conversation_name] = result.conversation
        
        user_prompt_report.conversations = conversation_map
        
        # Step 2: Run evaluations in parallel (after all conversations complete)
        evaluation_results = ParallelEvalRunner._run_evaluations_parallel(
            case_idx=case_idx,
            conversation_map=conversation_map,
            propositions=eval_case.propositions,
            ui=ui,
            eval_iterations_per_eval=eval_iterations_per_eval
        )
        
        # Add evaluation reports
        user_prompt_report.evaluations = evaluation_results
        
        return user_prompt_report
    
    @staticmethod
    def _generate_conversations_parallel(
        case_idx: int,
        eval_case: EvalCase,
        ui: TerminalUI,
        npc_factory: Callable[[], NPCProtocol],
        assistant_rules: List[str],
        mock_user_base_rules: List[str],
        convos_per_user_prompt: int,
        convo_length: int
    ) -> List[ConversationResult]:
        """
        Generate multiple conversations in parallel.
        
        Returns:
            List of conversation results
        """
        with ThreadPoolExecutor(max_workers=convos_per_user_prompt) as convo_executor:
            convo_futures = []
            
            for convo_idx in range(1, convos_per_user_prompt + 1):
                future = convo_executor.submit(
                    ParallelEvalRunner._generate_single_conversation,
                    case_idx=case_idx,
                    convo_idx=convo_idx,
                    eval_case=eval_case,
                    ui=ui,
                    npc_factory=npc_factory,
                    assistant_rules=assistant_rules,
                    mock_user_base_rules=mock_user_base_rules,
                    convo_length=convo_length
                )
                convo_futures.append((convo_idx, future))
            
            # Collect results
            results = []
            for convo_idx, future in convo_futures:
                result = future.result()
                results.append(result)
            
            return results
    
    @staticmethod
    def _generate_single_conversation(
        case_idx: int,
        convo_idx: int,
        eval_case: EvalCase,
        ui: TerminalUI,
        npc_factory: Callable[[], NPCProtocol],
        assistant_rules: List[str],
        mock_user_base_rules: List[str],
        convo_length: int
    ) -> ConversationResult:
        """
        Generate a single conversation.
        
        Returns:
            Conversation result with generated dialogue
        """
        conversation_name = f"Conversation {convo_idx}"
        
        # Create new NPC instance for thread safety
        assistant_npc = npc_factory()
        
        # Create conversation
        conversation = EvalConversation()
        conversation.add_agent_with_npc_protocol(AgentName.pat, assistant_rules, assistant_npc)
        conversation.add_agent_simple(AgentName.mock_user, mock_user_base_rules + eval_case.goals)
        
        # Progress callback
        total_turns = convo_length * 2
        
        def progress_callback(current: int, total: int, is_last_conversation: bool = True):
            ui.update_conversation_progress(case_idx, convo_idx, current, total)
            if current == total:
                ui.mark_conversation_complete(case_idx, convo_idx)
        
        # Run conversation
        conversation.converse(
            AgentName.pat,
            AgentName.mock_user,
            convo_length,
            isPrinting=False,
            progress_callback=progress_callback,
            is_last_conversation=True
        )
        
        # Get conversation history
        conversation_history = conversation.get_message_history_as_list(timestamped=True)
        
        return ConversationResult(
            conversation_name=conversation_name,
            conversation=conversation_history,
            case_idx=case_idx,
            convo_idx=convo_idx
        )
    
    @staticmethod
    def _run_evaluations_parallel(
        case_idx: int,
        conversation_map: Dict[str, List[str]],
        propositions: List[Proposition],
        ui: TerminalUI,
        eval_iterations_per_eval: int
    ) -> List[EvaluationEvalReport]:
        """
        Run evaluations on conversations in parallel.
        
        Returns:
            List of evaluation reports
        """
        evaluation_reports = []
        
        for proposition in propositions:
            evaluation_report = EvaluationEvalReport(
                evaluation_proposition=proposition,
                conversation_evaluations=[],
                result_score="",
                tokens=0
            )
            
            # Run evaluations for each conversation in parallel
            with ThreadPoolExecutor(max_workers=len(conversation_map)) as eval_executor:
                eval_futures = []
                
                for convo_idx, (conversation_name, conversation) in enumerate(conversation_map.items(), 1):
                    future = eval_executor.submit(
                        ParallelEvalRunner._evaluate_single_conversation,
                        case_idx=case_idx,
                        convo_idx=convo_idx,
                        conversation_name=conversation_name,
                        conversation=conversation,
                        proposition=proposition,
                        ui=ui,
                        eval_iterations_per_eval=eval_iterations_per_eval
                    )
                    eval_futures.append(future)
                
                # Collect results
                for future in eval_futures:
                    convo_eval_report = future.result()
                    evaluation_report.conversation_evaluations.append(convo_eval_report)
            
            # Calculate result score (average of all conversation evaluations)
            if evaluation_report.conversation_evaluations:
                scores = [ce.result_score for ce in evaluation_report.conversation_evaluations]
                evaluation_report.result_score = sum(scores) / len(scores)
            
            evaluation_reports.append(evaluation_report)
        
        return evaluation_reports
    
    @staticmethod
    def _evaluate_single_conversation(
        case_idx: int,
        convo_idx: int,
        conversation_name: str,
        conversation: List[str],
        proposition: Proposition,
        ui: TerminalUI,
        eval_iterations_per_eval: int
    ) -> ConversationEvaluationEvalReport:
        """
        Evaluate a single conversation against a proposition.
        
        Returns:
            Conversation evaluation report
        """
        conversation_evaluation_report = ConversationEvaluationEvalReport(
            conversation_name=conversation_name,
            evaluation_iterations=[],
            result_score=0,
            tokens=0
        )
        
        for i in range(1, eval_iterations_per_eval + 1):
            # Update progress
            ui.update_evaluation_progress(case_idx, convo_idx, i, eval_iterations_per_eval)
            
            # Run evaluation
            timestamping_result: EvaluationResponse = ConversationParsingBot.evaluate_conversation_timestamps(
                conversation, proposition
            )
            
            evaluation_result = EvalHelper.evaluate_result_from_timestamps(
                timestamping_result, len(conversation), proposition
            )
            
            evaluation_iteration_report = EvaluationIterationEvalReport(
                timestamping_response=timestamping_result,
                result=evaluation_result.pass_fail,
                explanation=evaluation_result.message,
                tokens=0
            )
            
            conversation_evaluation_report.evaluation_iterations.append(evaluation_iteration_report)
        
        # Mark evaluation complete
        ui.mark_evaluation_complete(case_idx, convo_idx)
        
        # Calculate result score (percentage of passed iterations)
        passed = sum(1 for ei in conversation_evaluation_report.evaluation_iterations 
                    if ei.result.value == "PASS")
        conversation_evaluation_report.result_score = passed / len(conversation_evaluation_report.evaluation_iterations)
        
        return conversation_evaluation_report

