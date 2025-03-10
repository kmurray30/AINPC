from dataclasses import asdict
import sys
import json
from typing import Dict, List
from statistics import mean

from src.test.Evaluator import Evaluator

sys.path.insert(0, "../..")
from src.core.Conversation import Conversation
from src.core.Constants import AgentName, Constants
from src.test.TestClasses import TestCaseSuite
from src.core.ChatResponse import ChatResponse
from src.test.TestReport import TestReport, AssistantPromptReport, UserPromptReport, EvaluationReport, ConversationEvaluationReport, ConversationEvaluationReport, EvaluationIterationReport
from src.utils import Utilities
from src.utils import Logger
from src.utils.Logger import Level

# Notes:
# - See runbooks/test.ipynb for sample usage

class UnitTestHelper:

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
    def score_evaluations(evaluation_report: EvaluationReport):
        for conversation_evaluation in evaluation_report.conversation_evaluations:
            correct_score = 0
            iteration_count = 0
            for evaluation_iteration in conversation_evaluation.evaluation_iterations:
                iteration_count += 1
                if evaluation_iteration.result == Constants.pass_name:
                    correct_score += 1
                elif evaluation_iteration.result == Constants.fail_name:
                    correct_score -= 1
            final_score = correct_score / iteration_count
            conversation_evaluation.score = final_score
        evaluation_report.score = mean(conversation_evaluation.score for conversation_evaluation in evaluation_report.conversation_evaluations)
    
    @staticmethod
    def run_evaluations_on_conversation(conversation_map: Dict[str, List[str]], evaluations: List[str], eval_iterations_per_eval: int) -> List[EvaluationReport]:
        evaluation_reports = []

        Logger.log("∟ Evaluating conversations", Level.VERBOSE)
            
        # Begin the evaluations
        Logger.increment_indent() # Begin evaluations section
        for evaluation_prompt in evaluations:
            evaluation_report = EvaluationReport(evaluation_prompt=evaluation_prompt, conversation_evaluations=[], score="", tokens=0)
            
            Logger.log(f"∟ Evaluating: {evaluation_prompt}", Level.VERBOSE)
            Logger.increment_indent(1) # Begin one evaluation
            for conversation_name, conversation in conversation_map.items():
                Logger.log(f"∟ {conversation_name}", Level.VERBOSE)
                conversation_evaluation_report = ConversationEvaluationReport(conversation_name=conversation_name, evaluation_iterations=[], score=0, tokens=0)
                evaluation_report.conversation_evaluations.append(conversation_evaluation_report)
                Logger.increment_indent() # Begin evaluation iterations section
                for i in range(1, eval_iterations_per_eval + 1):
                    Logger.log(f"∟ Evaluating (attempt {i}): {evaluation_prompt}", Level.VERBOSE)
                    result: ChatResponse = Evaluator.evaluate_conversation("\n".join(conversation), evaluation_prompt)
                    # Print the result as a json
                    Logger.increment_indent() # Begin result section
                    Logger.log(json.dumps(result.__dict__, indent=4), Level.VERBOSE)
                    Logger.decrement_indent() # End result section
                    evaluation_iteration_report = EvaluationIterationReport(explanation=result.explanation, result=result.response, tokens=0)
                    conversation_evaluation_report.evaluation_iterations.append(evaluation_iteration_report)
                Logger.decrement_indent() # End evaluation iterations section
            Logger.decrement_indent() # End one evaluation

            # Score the evaluations
            UnitTestHelper.score_evaluations(evaluation_report)
            evaluation_reports.append(evaluation_report)
        Logger.decrement_indent() # End evaluations section
        return evaluation_reports

    @staticmethod
    def run_unit_test(assistant_rules: List[str], mock_user_base_rules: List[str], test_suite: TestCaseSuite, convos_per_user_prompt: int, eval_iterations_per_eval: int, convo_length: int):
        assistant_prompt_report = AssistantPromptReport(assistant_prompt=Utilities.decode_list(assistant_rules), deltas=[], user_prompt_cases=[], tokens=0)
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
            Logger.log(f"Evaluations: {test_case.evaluations}", Level.VERBOSE)
            Logger.decrement_indent(2)
            user_prompt_report = UserPromptReport(user_prompt=test_case.goals, conversations=[], evaluations=[], tokens=0)
            assistant_prompt_report.user_prompt_cases.append(user_prompt_report)

            # Generate the conversations
            conversation_map = UnitTestHelper.generate_conversations(assistant_rules, mock_user_base_rules, test_case.goals, convos_per_user_prompt, convo_length)
            user_prompt_report.conversations.append(conversation_map)
                
            # Begin the evaluations
            evaluation_reports = UnitTestHelper.run_evaluations_on_conversation(conversation_map, test_case.evaluations, eval_iterations_per_eval)
            user_prompt_report.evaluations = evaluation_reports
        Logger.decrement_indent() # End test cases section

        # Write the test report to a json file
        current_time = Utilities.get_current_time_str()
        test_report_path = Utilities.get_path_from_project_root(f"src/test/reports/TestReport1_{current_time}.json")
        Logger.log(f"Writing test report to {test_report_path}", Level.INFO)
        with open(test_report_path, "w") as f:
            json.dump(asdict(test_report), f, indent=4)