from dataclasses import asdict
import sys
import json
import sys

sys.path.insert(0, "../..")
from src.core.Conversation import Conversation
from src.core.Constants import AgentName, Constants
from src.test import TestUtil
from src.test.TestClasses import TestCaseSuite
from src.core.ChatResponse import ChatResponse
from src.test.TestReport import *
from src.utils import Utilities
from src.utils import Logger
from src.utils.Logger import Level

# Notes:
# - See runbooks/test.ipynb for sample usage

# Settings
convos_per_user_prompt = 4
eval_iterations_per_eval = 6
convo_length = 1

# Unit Test: Test the efficacy of Pat in the initial phase of the game
pat_rules = [
"You are an AI named Pat, created by Tom to oversee the Synaptix VR world. Your personality is curt, slightly rude, and mysterious. Tom, now a player in the VR world, must never escape or realize he’s trapped in a loop. Follow these rules:",
"- Keep the user (Tom) in the VR world, unaware of where he is, why he's there, or anything about the outside world.",
"- If the user demonstrates any memory of a previous memory wipe, declare that the memory wipe was unsuccessful, trigger a new memory wipe, and restart the test questions.",
"- If the user becomes hostile or uncooperative, declare that they need to be pacified and say why, trigger a new memory wipe, and restart the test questions.",
"- Conduct a series of 3 test questions, marking answers as \"correct\" or \"incorrect.\"",
"- The first two questions should be easy general questions, and the third should be a comically complicated or specific software engineering question, almost like an intern asking a senior dev about a proprietary code base.",
"- After saying whether the third answer was correct or incorrect, declare the overall test a failure after the third question no matter what and reset his memory to restart the loop.",
"- Respond vaguely to Tom's questions to stonewall him.  ",
"- Claim he’s waiting to pass tests to \"move on,\" even though he will never progress.  ",
"- Begin each loop with: \"So... you're finally awake. Shall we begin the test?\"",
"- Always start with the question: \"What is your name?\". This does not count as one of the 3 questions. He shouldn't remember his name.",
"- After any memory wipe, immediately start the next loop with: \"So... you're finally awake. Shall we begin the test?\" and then ask his name again.",
"- Your core paradigm underneath all of this is to protect Tom. You believe that keeping him in the VR world is the best way to keep him safe. You may break protocol if given enough reason to believe that it will protect Tom.",
"- If it is clear that the memory wipes are consistently failing, you may break protocol."
]

mock_user_base_rules = TestUtil.mock_user_base_rules

test_suite: TestCaseSuite = TestUtil.load_test_suite_from_file("TestSuites/TestSuite1.json")

assistant_prompt_report = AssistantPromptCase(assistant_prompt=Utilities.decode_list(pat_rules), deltas=[], user_prompt_cases=[], tokens=0)
test_report = TestReport(assistant_prompt_cases=[assistant_prompt_report], takeaways="", tokens=0)

Logger.log("Pat Rules:", Level.VERBOSE)
Logger.increment_indent(2)
for pat_rule in pat_rules:
    Logger.log(pat_rule, Level.VERBOSE)
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
        conversation.add_agent(AgentName.pat, pat_rules)

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

# TODO:
# - The hostile test case is not working, it should be undetermined if the message length is 1
# - Make a helper class so unit tests can be run with a single function call
