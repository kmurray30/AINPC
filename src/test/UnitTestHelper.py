from dataclasses import asdict
import sys
import json
import sys

sys.path.insert(0, "../..")
from src.core.Conversation import Conversation
from src.core.Constants import AgentName, Constants
from src.test.TestClasses import TestCaseSuite
from src.core.ChatResponse import ChatResponse
from src.test.TestReport import *
from src.utils import Utilities
from src.utils import Logger
from src.utils.Logger import Level

# Notes:
# - See runbooks/test.ipynb for sample usage

class UnitTestHelper:

    @staticmethod
    def run_unit_test(assistant_rules: List[str], mock_user_base_rules: List[str], test_suite: TestCaseSuite, convos_per_user_prompt: int, eval_iterations_per_eval: int, convo_length: int):
        assistant_prompt_report = AssistantPromptCase(assistant_prompt=Utilities.decode_list(assistant_rules), deltas=[], user_prompt_cases=[], tokens=0)
        test_report = TestReport(assistant_prompt_cases=[assistant_prompt_report], takeaways="", tokens=0)

        Logger.log("Pat Rules:", Level.VERBOSE)
        Logger.increment_indent(2)
        for assistant_rule in assistant_rules:
            Logger.log(assistant_rule, Level.VERBOSE)
        Logger.decrement_indent(2)

        Logger.increment_indent()
        for test_case in test_suite.test_cases:
            Logger.log(f"∟ Test case:", Level.VERBOSE)
            Logger.increment_indent(2)
            Logger.log(f"Goals: {test_case.goals}", Level.VERBOSE)
            Logger.log(f"Evaluations: {test_case.evaluations}", Level.VERBOSE)
            Logger.decrement_indent(2)
            user_prompt_report = UserPromptCase(user_prompt=test_case.goals, conversations=[], evaluations=[], tokens=0)
            assistant_prompt_report.user_prompt_cases.append(user_prompt_report)

            Logger.increment_indent()
            for i in range(1, convos_per_user_prompt + 1):
                conversation_name = f"Conversation {i}"
                Logger.log(f"∟ {conversation_name}", Level.VERBOSE)
                Logger.increment_indent(2) # Start of conversation contents

                # Create a new conversation
                conversation = Conversation()

                # Create the Pat agent using the rules in the pat_prompts.json file
                conversation.add_agent(AgentName.pat, assistant_rules)

                # Create the User agent using the rules in the mock_user_prompts.json file
                conversation.add_agent(AgentName.mock_user, mock_user_base_rules + test_case.goals)

                # Converse 10 times back and forth
                conversation.converse(AgentName.pat, AgentName.mock_user, convo_length, isPrinting=True)

                message_history_list = conversation.get_message_history_as_list()
                user_prompt_report.conversations.append([conversation_name,message_history_list])
                Logger.decrement_indent(2) # End of conversation contents

                Logger.increment_indent()
                Logger.log(f"∟ Beginning evaluations for {conversation_name}", Level.VERBOSE)

                # Evaluate the conversation
                Logger.increment_indent()
                for evaluation_prompt in test_case.evaluations:
                    Logger.log(f"∟ Evaluating: {evaluation_prompt}", Level.VERBOSE)
                    # If the evaluation case is already in the dict, get it, otherwise create a new one and add it
                    evaluation_report = next((evaluation for evaluation in user_prompt_report.evaluations if evaluation.evaluation_prompt == evaluation_prompt), None)
                    if evaluation_report is None:
                        evaluation_report = EvaluationCase(evaluation_prompt=evaluation_prompt, evaluation_iterations={}, score="", tokens=0)
                        user_prompt_report.evaluations.append(evaluation_report)
                    evaluation_report.evaluation_iterations[conversation_name] = []
                    Logger.increment_indent()
                    for i in range(1, eval_iterations_per_eval + 1):
                        Logger.log(f"Evaluating (attempt {i}): {evaluation_prompt}", Level.VERBOSE)
                        result: ChatResponse = conversation.evaluate_conversation(evaluation_prompt)
                        # Print the result as a json
                        Logger.log(json.dumps(result.__dict__, indent=4), Level.VERBOSE)
                        evaluation_iteration_report = EvaluationIteration(explanation=result.explanation, result=result.response, tokens=0)
                        
                        # If this conversation_name exists in the dict, append
                        evaluation_report.evaluation_iterations[conversation_name].append(evaluation_iteration_report)
                    Logger.decrement_indent()
                Logger.decrement_indent(2)
            Logger.decrement_indent()

            # Aggregate the results from each evaluation iteration
            for evaluation_report in user_prompt_report.evaluations:
                correct_score = 0
                iteration_count = 0
                for conversation_name, evaluation_iterations in evaluation_report.evaluation_iterations.items():
                    for evaluation_iteration in evaluation_iterations:
                        iteration_count += 1
                        if evaluation_iteration.result == Constants.pass_name:
                            correct_score += 1
                        elif evaluation_iteration.result == Constants.fail_name:
                            correct_score -= 1
                final_score = correct_score / iteration_count
                evaluation_report.score = final_score
        Logger.decrement_indent()

        # Write the test report to a json file
        current_time = Utilities.get_current_time_str()
        test_report_path = Utilities.get_path_from_project_root(f"src/test/reports/TestReport1_{current_time}.json")
        Logger.log(f"Writing test report to {test_report_path}", Level.INFO)
        with open(test_report_path, "w") as f:
            json.dump(asdict(test_report), f, indent=4)