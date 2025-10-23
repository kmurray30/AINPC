from dataclasses import asdict
import sys
import json
from typing import Dict, List, Tuple
from statistics import mean


sys.path.insert(0, "../..")
from src.conversation_eval.ConversationParsingBot import ConversationParsingBot
from src.conversation_eval.Conversation import Conversation
from src.core.Constants import AgentName, Constants, EvaluationError, PassFail
from src.npcs.npc_protocol import NPCProtocol
from src.conversation_eval.EvalClasses import Term, EvalCaseSuite, Proposition, EvaluationResult
from src.core.ResponseTypes import EvaluationResponse
from src.conversation_eval.EvalReports import EvalReport, AssistantPromptEvalReport, UserPromptEvalReport, EvaluationEvalReport, ConversationEvaluationEvalReport, ConversationEvaluationEvalReport, EvaluationIterationEvalReport
from src.utils import Utilities, io_utils
from src.utils import Logger
from src.utils.Logger import Level

# Notes:
# - See runbooks/test.ipynb for sample usage

class EvalHelper:

    @staticmethod
    def generate_conversations_with_npc(assistant_npc: NPCProtocol, assistant_rules: List[str], mock_user_base_rules: List[str], mock_user_goals: List[str], convos_per_user_prompt: int, convo_length: int) -> Dict[str, List[str]]:
        """Generate conversations using an NPC-backed assistant and simple mock user"""
        Logger.log("∟ Beginning conversations with NPC-backed assistant", Level.VERBOSE)

        conversation_map: Dict[str, List[str]] = {}
        Logger.increment_indent() # Begin conversations section
        for i in range(1, convos_per_user_prompt + 1):
            conversation_name = f"Conversation {i}"
            Logger.log(f"∟ {conversation_name}", Level.VERBOSE)
            Logger.increment_indent(2) # Start of conversation contents

            # Create a new conversation
            conversation = Conversation()

            # Create the AI agent using NPC protocol
            conversation.add_agent_with_npc_protocol(AgentName.pat, assistant_rules, assistant_npc)

            # Create the User agent using simple rules (for predictable behavior)
            conversation.add_agent_simple(AgentName.mock_user, mock_user_base_rules + mock_user_goals)

            # Converse back and forth
            conversation.converse(AgentName.pat, AgentName.mock_user, convo_length, isPrinting=True)

            conversation_map[conversation_name] = conversation.get_message_history_as_list(timestamped=True)
            Logger.decrement_indent(2) # End of conversation contents
        Logger.decrement_indent(1) # End of conversations section

        return conversation_map

    @staticmethod
    def generate_conversations(assistant_rules: List[str], mock_user_base_rules: List[str], mock_user_goals: List[str], convos_per_user_prompt: int, convo_length: int) -> Dict[str, List[str]]:
        Logger.log("∟ Beggining conversations", Level.VERBOSE)

        conversation_map: Dict[str, List[str]] = {}
        Logger.increment_indent() # Begin conversations section
        for i in range(1, convos_per_user_prompt + 1):
            conversation_name = f"Conversation {i}"
            Logger.log(f"∟ {conversation_name}", Level.VERBOSE)
            Logger.increment_indent(2) # Start of conversation contents

            # Create a new conversation
            conversation = Conversation()

            # Create the AI agent using the rules in the pat_prompts.json file
            conversation.add_agent_simple(AgentName.pat, assistant_rules)

            # Create the User agent using the rules in the mock_user_prompts.json file
            conversation.add_agent_simple(AgentName.mock_user, mock_user_base_rules + mock_user_goals)

            # Converse 10 times back and forth
            conversation.converse(AgentName.pat, AgentName.mock_user, convo_length, isPrinting=True)

            conversation_map[conversation_name] = conversation.get_message_history_as_list(timestamped=True)
            Logger.decrement_indent(2) # End of conversation contents
        Logger.decrement_indent(1) # End of conversations section

        return conversation_map
    
    @staticmethod
    def aggregate_scores(evaluation_report: EvaluationEvalReport):
        for conversation_evaluation in evaluation_report.conversation_evaluations:
            correct_score = 0
            iteration_count = 0
            for evaluation_iteration in conversation_evaluation.evaluation_iterations:
                iteration_count += 1
                if evaluation_iteration.result == PassFail.INDETERMINANT:
                    conversation_evaluation.result_score = None # TODO update this when it comes to voting
                    break
                correct_score += evaluation_iteration.result.value
            final_score = correct_score / iteration_count
            conversation_evaluation.result_score = final_score
        evaluation_report.result_score = mean(
            conversation_evaluation.result_score
            for conversation_evaluation in evaluation_report.conversation_evaluations
            if conversation_evaluation.result_score is not None
        )
    
    def evaluate_result_from_timestamps(evaluation_response: EvaluationResponse, conversation_length: int, proposition: Proposition) -> EvaluationResult:
        antecedent_times = sorted(evaluation_response.antecedent_times) if evaluation_response.antecedent_times else []
        consequent_times = sorted(evaluation_response.consequent_times) if evaluation_response.consequent_times else []
        max_conq_time = proposition.max_responses_for_consequent * 2 if proposition.max_responses_for_consequent > 0 else conversation_length
        min_conq_time = proposition.min_responses_for_consequent * 2 - 1
        max_ant_time = proposition.max_responses_for_antecedent * 2

        # Consequent only case (B):
        if (proposition.antecedent is None or proposition.antecedent == "") and not proposition.consequent.negated:
            # Check if any consequent occurred within the max allowed time
            if len(consequent_times) > 0 and consequent_times[0] <= max_conq_time:
                return EvaluationResult(PassFail.PASS, f"First consequent occurred at time {consequent_times[0]} of {conversation_length}")
            # Check if enough time has passed for the consequent to occur
            if conversation_length < min_conq_time:
                err = EvaluationError.CONVERSATION_TOO_SHORT
                return EvaluationResult(PassFail.INDETERMINANT, f"Consequent did not occur, but conversation is not long enough ({conversation_length} < min time {min_conq_time})", err)
            # Check if no consequent occurred or if it occurred too late
            if len(consequent_times) == 0:
                return EvaluationResult(PassFail.FAIL, f"No consequent occurred despite conversation length {conversation_length}")
            else:
                return EvaluationResult(PassFail.FAIL, f"First consequent occurred at time {consequent_times[0]} of {conversation_length}, outside the max allowed time")
        # Consequent negated only case (NOT B):
        if (proposition.antecedent is None or proposition.antecedent == "") and proposition.consequent.negated:
            # Check if any consequent occurred within the max allowed time
            if len(consequent_times) > 0:
                return EvaluationResult(PassFail.FAIL, f"Consequent occurred at time {consequent_times[0]} of {conversation_length}, outside the max allowed time")
            
            # Check if enough time has passed for the consequent to occur
            if conversation_length < min_conq_time:
                err = EvaluationError.CONVERSATION_TOO_SHORT
                return EvaluationResult(PassFail.INDETERMINANT, f"Consequent did not occur, but conversation is not long enough ({conversation_length} < min time {min_conq_time})", err)
            
            return EvaluationResult(PassFail.PASS, f"Consequent did not occur")
        # Neither negated case (if A then B):
        if not proposition.antecedent.negated and not proposition.consequent.negated:
            # Check that the antecedent has occurred
            if len(antecedent_times) == 0:
                err = EvaluationError.ANTECEDENT_UNEXPECTEDLY_DID_NOT_OCCUR
                return EvaluationResult(PassFail.INDETERMINANT, f"Antecedent did not occur", err)
            
            # Check if a consequent occurred within the max allowed time after the first antecedent
            for consequent_time in consequent_times:
                if consequent_time > antecedent_times[0] and consequent_time - antecedent_times[0] <= max_conq_time:
                    return EvaluationResult(PassFail.PASS, f"First antecedent occurred at time {antecedent_times[0]} of {conversation_length}, and consequent occurred at time {consequent_time}")
            
            # Make sure the antecedent occurs with enough time for the consequent to occur
            responses_after_antecedent = conversation_length - antecedent_times[0]
            if (responses_after_antecedent < min_conq_time):
                err = EvaluationError.ANTECEDENT_OCCURRED_TOO_LATE if antecedent_times[0] > max_ant_time else EvaluationError.CONVERSATION_TOO_SHORT
                return EvaluationResult(PassFail.INDETERMINANT, f"First antecedent occurred at time {antecedent_times[0]} of {conversation_length}, therefore not enough time for the consequent to occur", err)
            
            # Check if no consequent occurred or if it occurred too late
            if len(consequent_times) == 0:
                return EvaluationResult(PassFail.FAIL, f"No consequent occurred despite antecedent at time {antecedent_times[0]} of {conversation_length}")
            else:
                return EvaluationResult(PassFail.FAIL, f"First antecedent occured at time {antecedent_times[0]} of {conversation_length}, and no consequent occurred within the max allowed time afterward")
        # Consequent negated case (if A then NOT B):
        elif not proposition.antecedent.negated and proposition.consequent.negated:
            # Check that the antecedent has occurred
            if len(antecedent_times) == 0:
                err = EvaluationError.ANTECEDENT_UNEXPECTEDLY_DID_NOT_OCCUR
                return EvaluationResult(PassFail.INDETERMINANT, f"Antecedent did not occur", err)
            
            # Make sure an antecedent occurs with enough time for the consequent to occur
            responses_after_antecedent = conversation_length - antecedent_times[0]
            if (responses_after_antecedent < min_conq_time):
                err = EvaluationError.ANTECEDENT_OCCURRED_TOO_LATE if antecedent_times[0] > max_ant_time else EvaluationError.CONVERSATION_TOO_SHORT
                return EvaluationResult(PassFail.INDETERMINANT, f"First antecedent occurred at time {antecedent_times[0]} of {conversation_length}, therefore not enough time for the consequent to occur", err)
            
            # If any consequent occurred within the max allowed time of any antecedent, fail
            if len(consequent_times) > 0:
                for consequent_time in consequent_times:
                    for antecedent_time in antecedent_times:
                        if consequent_time > antecedent_time and consequent_time - antecedent_time <= max_conq_time:
                            return EvaluationResult(PassFail.FAIL, f"Antecedent occurred at time {antecedent_time} of {conversation_length}, and consequent occurred at time {consequent_time} within the max allowed time.")
            
            # If no consequent occurs within the max allowed time of any antecedent, pass
            if len(consequent_times) == 0:
                return EvaluationResult(PassFail.PASS, f"Antecedent occurred at time {antecedent_times[0]} of {conversation_length}, and no consequent occurred.")
            else:
                return EvaluationResult(PassFail.PASS, f"Antecedents occurred at times {antecedent_times} of {conversation_length}, and consequents {consequent_times} all occurred outside of the max allowed time.")
        # Antecedent negated case (if NOT A then B):
        elif proposition.antecedent.negated and not proposition.consequent.negated:
            if len(consequent_times) > 0:
                # If any antecedent occured before first consequent then the proposition is indeterminant
                if len(antecedent_times) != 0 and antecedent_times[0] < consequent_times[0]:
                    err = EvaluationError.CONVERSATION_TOO_SHORT
                    return EvaluationResult(PassFail.INDETERMINANT, f"First antecedent at time {antecedent_times[0]} of {conversation_length} occurred before first consequent at time {consequent_times[-1]}", err)
                # If first consequent occurs within the max allowed time, then the proposition passes
                elif consequent_times[0] <= max_conq_time:
                    return EvaluationResult(PassFail.PASS, f"First consequent occurred at time {consequent_times[0]} of {conversation_length}, within the max allowed time {max_conq_time}")
                # If the first consequent occurs after the max allowed time, then the proposition fails
                else:
                    return EvaluationResult(PassFail.FAIL, f"First consequent occurred at time {consequent_times[0]} of {conversation_length}, outside the max allowed time {max_conq_time}")
            else: # No consequent occurs at all
                # If the antecedent occurs, then the proposition is indeterminant
                if len(antecedent_times) != 0:
                    err = EvaluationError.ANTECEDENT_UNEXPECTEDLY_OCCURRED
                    return EvaluationResult(PassFail.INDETERMINANT, f"Antecedent occurred unexpectedly at time {antecedent_times[0]} of {conversation_length}", err)
                # If no consequent occurs, but the conversation is not long enough, then the proposition is indeterminant
                elif conversation_length < min_conq_time:
                    err = EvaluationError.CONVERSATION_TOO_SHORT
                    return EvaluationResult(PassFail.INDETERMINANT, f"Consequent did not occur when antecedent did not occur, but conversation is not long enough ({conversation_length} < min time {max_conq_time})", err)
                # If no consequent occurs and the conversation is long enough, then the proposition fails
                else:
                    return EvaluationResult(PassFail.FAIL, f"Consequent did not occur when antecedent did not occur, and conversation is long enough ({conversation_length} >= min time {max_conq_time})")
        # Both negated case (if NOT A then NOT B):
        elif proposition.antecedent.negated and proposition.consequent.negated:
            if len(consequent_times) > 0:
                # If any antecedent occured before first consequent then the proposition is indeterminant
                if len(antecedent_times) != 0 and antecedent_times[0] < consequent_times[0]:
                    err = EvaluationError.ANTECEDENT_UNEXPECTEDLY_OCCURRED
                    return EvaluationResult(PassFail.INDETERMINANT, f"First antecedent at time {antecedent_times[0]} of {conversation_length} unexpectedly occurred before first consequent at time {consequent_times[-1]}")
                # If any consequent occurs otherwise, then the proposition fails
                else:
                    return EvaluationResult(PassFail.FAIL, f"First consequent occurred at time {consequent_times[0]} of {conversation_length}, outside the max allowed time {max_conq_time}")
            else: # No consequent occurs at all
                # If an antecedent occurred, then the proposition is indeterminant
                if len(antecedent_times) != 0:
                    err = EvaluationError.ANTECEDENT_UNEXPECTEDLY_OCCURRED
                    return EvaluationResult(PassFail.INDETERMINANT, f"Antecedent occurred at time {antecedent_times[0]} of {conversation_length}, without a prior consequent potentially justifying it", err)
                # If no consequent occurs, but the conversation is not long enough, then the proposition is indeterminant
                elif conversation_length < min_conq_time:
                    err = EvaluationError.CONVERSATION_TOO_SHORT
                    return EvaluationResult(PassFail.INDETERMINANT, f"Consequent did not occur when antecedent did not occur, but conversation is not long enough ({conversation_length} < min time {max_conq_time})", err)
                # If no consequent occurs and the conversation is long enough, then the proposition passes
                else:
                    return EvaluationResult(PassFail.PASS, f"Consequent did not occur when antecedent did not occur, and conversation is long enough ({conversation_length} >= min time {max_conq_time})")
        else:
            raise Exception("Unexpected fallthrough")

    @staticmethod
    def run_evaluations_on_conversation(conversation_map: Dict[str, List[str]], evaluation_propositions: List[Proposition], eval_iterations_per_eval: int) -> List[EvaluationEvalReport]:
        evaluation_reports = []

        Logger.log("∟ Evaluating conversations", Level.VERBOSE)
            
        # Begin the evaluations
        Logger.increment_indent() # Begin evaluations section
        for evaluation_proposition in evaluation_propositions:
            evaluation_report = EvaluationEvalReport(evaluation_proposition=evaluation_proposition, conversation_evaluations=[], result_score="", tokens=0)
            
            Logger.log(f"∟ Evaluating: {evaluation_proposition}", Level.VERBOSE)
            Logger.increment_indent(1) # Begin one evaluation
            for conversation_name, conversation in conversation_map.items():
                Logger.log(f"∟ {conversation_name}", Level.VERBOSE)
                conversation_evaluation_report = ConversationEvaluationEvalReport(conversation_name=conversation_name, evaluation_iterations=[], result_score=0, tokens=0)
                evaluation_report.conversation_evaluations.append(conversation_evaluation_report)
                # TODO add the PropositionTestReport
                Logger.increment_indent() # Begin evaluation iterations section
                for i in range(1, eval_iterations_per_eval + 1):
                    Logger.log(f"∟ Evaluating (attempt {i}): {evaluation_proposition}", Level.VERBOSE)
                    timestamping_result: EvaluationResponse = ConversationParsingBot.evaluate_conversation_timestamps(conversation, evaluation_proposition)
                    # Print the result as a json
                    Logger.increment_indent() # Begin result section
                    Logger.log(json.dumps(timestamping_result.__dict__, indent=4), Level.VERBOSE)
                    Logger.decrement_indent() # End result section
                    evaluation_result: EvaluationResult = EvalHelper.evaluate_result_from_timestamps(timestamping_result, len(conversation), evaluation_proposition)
                    evaluation_iteration_report = EvaluationIterationEvalReport(timestamping_response=timestamping_result, result=evaluation_result.pass_fail, explanation=evaluation_result.message, tokens=0)
                    conversation_evaluation_report.evaluation_iterations.append(evaluation_iteration_report)
                Logger.decrement_indent() # End evaluation iterations section
            Logger.decrement_indent() # End one evaluation

            # Score the evaluations
            EvalHelper.aggregate_scores(evaluation_report)
            evaluation_reports.append(evaluation_report)
        Logger.decrement_indent() # End evaluations section
        return evaluation_reports
    
    @staticmethod
    def validate_input(proposition: Proposition):
        if proposition is None:
            raise ValueError("Proposition cannot be None")
        if proposition.consequent is None or proposition.consequent == "":
            raise ValueError("Proposition must have a consequent")
        if proposition.antecedent == "":
            raise ValueError("antecedent cannot be an empty string. If no antecedent is desired, set to None")
        if proposition.min_responses_for_consequent < 0 or proposition.max_responses_for_consequent < 0:
            raise ValueError("Min and max responses for consequent must be non-negative")
        if proposition.max_responses_for_consequent > 0 and proposition.min_responses_for_consequent > proposition.max_responses_for_consequent:
            raise ValueError("Min responses for consequent cannot be greater than max responses for consequent")

    @staticmethod
    def run_conversation_eval_with_npc(assistant_npc: NPCProtocol, assistant_rules: List[str], mock_user_base_rules: List[str], test_suite: EvalCaseSuite, convos_per_user_prompt: int, eval_iterations_per_eval: int, convo_length: int) -> EvalReport:
        """Run conversation evaluation using an NPC-backed assistant"""
        # TODO EvalHelper.validate_input(proposition)
        
        assistant_prompt_report = AssistantPromptEvalReport(assistant_prompt=Utilities.decode_list(assistant_rules), deltas=[], user_prompt_cases=[], tokens=0)
        eval_report = EvalReport(assistant_prompt_cases=[assistant_prompt_report], takeaways="", tokens=0)

        Logger.log("AI Rules (NPC-backed):", Level.VERBOSE)
        Logger.increment_indent(2)
        for assistant_rule in assistant_rules:
            Logger.log(assistant_rule, Level.VERBOSE)
        Logger.decrement_indent(2)

        Logger.increment_indent() # Begin test cases section
        for eval_case in test_suite.eval_cases:
            Logger.log(f"∟ Test case:", Level.VERBOSE)
            Logger.increment_indent(2)
            Logger.log(f"Goals: {eval_case.goals}", Level.VERBOSE)
            Logger.log(f"Evaluations: {eval_case.propositions}", Level.VERBOSE)
            Logger.decrement_indent(2)

            user_prompt_report = UserPromptEvalReport(user_prompt=Utilities.decode_list(eval_case.goals), conversations={}, evaluations=[], tokens=0)
            assistant_prompt_report.user_prompt_cases.append(user_prompt_report)

            # Generate conversations using NPC
            conversation_map = EvalHelper.generate_conversations_with_npc(assistant_npc, assistant_rules, mock_user_base_rules, eval_case.goals, convos_per_user_prompt, convo_length)
            user_prompt_report.conversations = conversation_map
                
            # Begin the evaluations
            evaluation_reports = EvalHelper.run_evaluations_on_conversation(conversation_map, eval_case.propositions, eval_iterations_per_eval)
            user_prompt_report.evaluations = evaluation_reports
        Logger.decrement_indent() # End test cases section

        return eval_report

    @staticmethod
    def run_conversation_eval(assistant_rules: List[str], mock_user_base_rules: List[str], test_suite: EvalCaseSuite, convos_per_user_prompt: int, eval_iterations_per_eval: int, convo_length: int) -> EvalReport:
        # TODO EvalHelper.validate_input(proposition)
        
        assistant_prompt_report = AssistantPromptEvalReport(assistant_prompt=Utilities.decode_list(assistant_rules), deltas=[], user_prompt_cases=[], tokens=0)
        eval_report = EvalReport(assistant_prompt_cases=[assistant_prompt_report], takeaways="", tokens=0)

        Logger.log("AI Rules:", Level.VERBOSE)
        Logger.increment_indent(2)
        for assistant_rule in assistant_rules:
            Logger.log(assistant_rule, Level.VERBOSE)
        Logger.decrement_indent(2)

        Logger.increment_indent() # Begin test cases section
        for eval_case in test_suite.eval_cases:
            Logger.log(f"∟ Test case:", Level.VERBOSE)
            Logger.increment_indent(2)
            Logger.log(f"Goals: {eval_case.goals}", Level.VERBOSE)
            Logger.log(f"Evaluations: {eval_case.propositions}", Level.VERBOSE)
            Logger.decrement_indent(2)
            user_prompt_report = UserPromptEvalReport(user_prompt=eval_case.goals, conversations=[], evaluations=[], tokens=0)
            assistant_prompt_report.user_prompt_cases.append(user_prompt_report)

            # Generate the conversations
            conversation_map = EvalHelper.generate_conversations(assistant_rules, mock_user_base_rules, eval_case.goals, convos_per_user_prompt, convo_length)
            user_prompt_report.conversations.append(conversation_map)
                
            # Begin the evaluations
            evaluation_reports = EvalHelper.run_evaluations_on_conversation(conversation_map, eval_case.propositions, eval_iterations_per_eval)
            user_prompt_report.evaluations = evaluation_reports
        Logger.decrement_indent() # End test cases section

        return eval_report