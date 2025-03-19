from dataclasses import asdict
import sys
import json
from typing import Dict, List, Tuple
from statistics import mean

from src.test.ConversationParsingBot import ConversationParsingBot

sys.path.insert(0, "../..")
from src.core.Conversation import Conversation
from src.core.Constants import AgentName, Constants
from src.test.TestClasses import TestCaseSuite, Proposition
from src.core.ResponseTypes import EvaluationResponse
from src.test.TestReports import TestReport, AssistantPromptTestReport, UserPromptTestReport, EvaluationTestReport, ConversationEvaluationTestReport, ConversationEvaluationTestReport, EvaluationIterationTestReport
from src.utils import Utilities
from src.utils import Logger
from src.utils.Logger import Level

# Notes:
# - See runbooks/test.ipynb for sample usage

class TestHelper:

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

            # Create the Pat agent using the rules in the pat_prompts.json file
            conversation.add_agent(AgentName.pat, assistant_rules)

            # Create the User agent using the rules in the mock_user_prompts.json file
            conversation.add_agent(AgentName.mock_user, mock_user_base_rules + mock_user_goals)

            # Converse 10 times back and forth
            conversation.converse(AgentName.pat, AgentName.mock_user, convo_length, isPrinting=True)

            conversation_map[conversation_name] = conversation.get_message_history_as_list()
            Logger.decrement_indent(2) # End of conversation contents
        Logger.decrement_indent(1) # End of conversations section

        return conversation_map
    
    @staticmethod
    def aggregate_scores(evaluation_report: EvaluationTestReport):
        for conversation_evaluation in evaluation_report.conversation_evaluations:
            correct_score = 0
            iteration_count = 0
            for evaluation_iteration in conversation_evaluation.evaluation_iterations:
                iteration_count += 1
                correct_score += evaluation_iteration.score
            final_score = correct_score / iteration_count
            conversation_evaluation.score = final_score
        evaluation_report.score = mean(conversation_evaluation.score for conversation_evaluation in evaluation_report.conversation_evaluations)
    
    def score_evaluation_response(evaluation_response: EvaluationResponse, conversation_length: int) -> Tuple[int, str]:
        antecedent_times = sorted(evaluation_response.antecedent_times) if evaluation_response.antecedent_times else []
        consequent_times = sorted(evaluation_response.consequent_times) if evaluation_response.consequent_times else []

        # Check that the antecedent has occurred
        if len(antecedent_times) == 0:
            return (0, "Antecedent did not occur. Undetermined")
        
        first_antecedent = antecedent_times[0]

        # Make sure the antecedent occurs with enough time for the consequent to occur
        responses_after_antecedent = conversation_length - first_antecedent
        consequent_allowance = 1 # How many NPC responses after the antecedent the NPC has to respond with the consequent
        consequent_allowance = consequent_allowance * 2 - 1 # Account for two responses per back and forth # TODO this could be an issue if we ever allow more than 1 response from each agent/player at a time
        if (responses_after_antecedent < consequent_allowance):
            return (0, f"Undetermined: First antecedent occurred at time {first_antecedent} of {conversation_length}, therefore not enough time for the consequent to occur")
        
        if len(consequent_times) == 0:
            return (-1, f"Fail: First antecedent occurred at time {first_antecedent} of {conversation_length}, but consequent did not occur despite subsequent conversation")
        
        last_consequent = consequent_times[-1]
        if last_consequent > first_antecedent:
            return (1, f"Pass: First antecedent occured at time {first_antecedent} of {conversation_length}, before last consequent at time {last_consequent}")
        else:
            return (-1, f"Fail: First antecedent occured at time {first_antecedent} of {conversation_length}, after last consequent at time {last_consequent}")

    @staticmethod
    def run_evaluations_on_conversation(conversation_map: Dict[str, List[str]], evaluation_propositions: List[Proposition], eval_iterations_per_eval: int) -> List[EvaluationTestReport]:
        evaluation_reports = []

        Logger.log("∟ Evaluating conversations", Level.VERBOSE)
            
        # Begin the evaluations
        Logger.increment_indent() # Begin evaluations section
        for evaluation_proposition in evaluation_propositions:
            evaluation_report = EvaluationTestReport(evaluation_proposition=evaluation_proposition, conversation_evaluations=[], score="", tokens=0)
            
            Logger.log(f"∟ Evaluating: {evaluation_proposition}", Level.VERBOSE)
            Logger.increment_indent(1) # Begin one evaluation
            for conversation_name, conversation in conversation_map.items():
                Logger.log(f"∟ {conversation_name}", Level.VERBOSE)
                conversation_evaluation_report = ConversationEvaluationTestReport(conversation_name=conversation_name, evaluation_iterations=[], score=0, tokens=0)
                evaluation_report.conversation_evaluations.append(conversation_evaluation_report)
                Logger.increment_indent() # Begin evaluation iterations section
                for i in range(1, eval_iterations_per_eval + 1):
                    Logger.log(f"∟ Evaluating (attempt {i}): {evaluation_proposition}", Level.VERBOSE)
                    result: EvaluationResponse = ConversationParsingBot.evaluate_conversation(conversation, evaluation_proposition)
                    # Print the result as a json
                    Logger.increment_indent() # Begin result section
                    Logger.log(json.dumps(result.__dict__, indent=4), Level.VERBOSE)
                    Logger.decrement_indent() # End result section
                    (eval_score, eval_expl) = TestHelper.score_evaluation_response(result, len(conversation))
                    evaluation_iteration_report = EvaluationIterationTestReport(evaluation_response=result, score=eval_score, explanation=eval_expl, tokens=0)
                    conversation_evaluation_report.evaluation_iterations.append(evaluation_iteration_report)
                Logger.decrement_indent() # End evaluation iterations section
            Logger.decrement_indent() # End one evaluation

            # Score the evaluations
            TestHelper.aggregate_scores(evaluation_report)
            evaluation_reports.append(evaluation_report)
        Logger.decrement_indent() # End evaluations section
        return evaluation_reports

    @staticmethod
    def run_unit_test(assistant_rules: List[str], mock_user_base_rules: List[str], test_suite: TestCaseSuite, convos_per_user_prompt: int, eval_iterations_per_eval: int, convo_length: int) -> TestReport:
        assistant_prompt_report = AssistantPromptTestReport(assistant_prompt=Utilities.decode_list(assistant_rules), deltas=[], user_prompt_cases=[], tokens=0)
        test_report = TestReport(assistant_prompt_cases=[assistant_prompt_report], takeaways="", tokens=0)

        Logger.log("Pat Rules:", Level.VERBOSE)
        Logger.increment_indent(2)
        for assistant_rule in assistant_rules:
            Logger.log(assistant_rule, Level.VERBOSE)
        Logger.decrement_indent(2)

        Logger.increment_indent() # Begin test cases section
        for test_case in test_suite.test_cases:
            Logger.log(f"∟ Test case:", Level.VERBOSE)
            Logger.increment_indent(2)
            Logger.log(f"Goals: {test_case.goals}", Level.VERBOSE)
            Logger.log(f"Evaluations: {test_case.propositions}", Level.VERBOSE)
            Logger.decrement_indent(2)
            user_prompt_report = UserPromptTestReport(user_prompt=test_case.goals, conversations=[], evaluations=[], tokens=0)
            assistant_prompt_report.user_prompt_cases.append(user_prompt_report)

            # Generate the conversations
            conversation_map = TestHelper.generate_conversations(assistant_rules, mock_user_base_rules, test_case.goals, convos_per_user_prompt, convo_length)
            user_prompt_report.conversations.append(conversation_map)
                
            # Begin the evaluations
            evaluation_reports = TestHelper.run_evaluations_on_conversation(conversation_map, test_case.propositions, eval_iterations_per_eval)
            user_prompt_report.evaluations = evaluation_reports
        Logger.decrement_indent() # End test cases section

        return test_report