from dataclasses import asdict
import sys
import json
import sys

sys.path.insert(0, "../..")
from src.core.Conversation import Conversation
from src.core.Constants import AgentName
from src.test import TestUtil
from src.test.TestClasses import TestCaseSuite
from src.core.ChatResponse import ChatResponse
from src.test.TestReport import *
from src.utils import Utilities

# Notes:
# - See runbooks/test.ipynb for sample usage

# Settings
evals_per_goal = 1
convos_per_user_prompt = 1
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

assistant_prompt_case = AssistantPromptCase(assistant_prompt=pat_rules, deltas=[], user_prompt_cases=[], tokens=0)
test_report = TestReport(assistant_prompt_cases=[assistant_prompt_case], takeaways="", tokens=0)

for test_case in test_suite.test_cases:
    print(f"Test case: {test_case}")
    user_prompt_case = UserPromptCase(user_prompt=test_case.goals, conversations=[], tokens=0)

    for i in range (convos_per_user_prompt):
        print(f"Conversation {i}")
        conversation_case = ConversationCase(conversation=[], evaluations=[], tokens=0)

        # Create a new conversation
        conversation = Conversation()

        # Create the Pat agent using the rules in the pat_prompts.json file
        conversation.add_agent(AgentName.pat, pat_rules)

        # Create the User agent using the rules in the mock_user_prompts.json file
        conversation.add_agent(AgentName.mock_user, mock_user_base_rules + test_case.goals)

        # Converse 10 times back and forth
        conversation.converse(AgentName.pat, AgentName.mock_user, convo_length, isPrinting=True)

        message_history_list = conversation.get_message_history_as_list()
        conversation_case.conversation = message_history_list

        # # Print the conversation
        # print(conversation.get_message_history_as_string())

        # Evaluate the conversation
        for evaluation in test_case.evaluations:
            print(f"Evaluating: {evaluation}")
            evaluation_case = EvaluationCase(evaluation_prompt=evaluation, evaluation_iterations=[], result="", tokens=0)
            results = []
            for i in range(evals_per_goal):
                print(f"Evaluating (attempt {i}): {evaluation}")
                result: ChatResponse = conversation.evaluate_conversation(evaluation)
                # Print the result as a json
                print(json.dumps(result.__dict__, indent=4))
                evaluation_iteration = EvaluationIteration(explanation=result.explanation, result=result.response, tokens=0)
                evaluation_case.evaluation_iterations.append(evaluation_iteration)
                results.append(result.response)
            evaluation_case.result = ", ".join(results)
            conversation_case.evaluations.append(evaluation_case)
        user_prompt_case.conversations.append(conversation_case)
    assistant_prompt_case.user_prompt_cases.append(user_prompt_case)

# Write the test report to a json file
current_time = Utilities.get_current_time_str()
test_report_path = Utilities.get_path_from_project_root(f"src/test/reports/TestReport1_{current_time}.json")
with open(test_report_path, "w") as f:
    json.dump(asdict(test_report), f, indent=4)

# TODO:
# - Invert the report structure so it goes userprompt -> evaluation -> conversation -> iteration
#   - For this, I need to store conversations at a higher level instead of redundantly within each evaluation
# - The hostile test case is not working, it should be undetermined if the message length is 1
# - Make a helper class so unit tests can be run with a single function call
# - Custom logger that can have warning levels, and also increment and decrement indent permanently