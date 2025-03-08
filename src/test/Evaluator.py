

from src.core.ChatResponse import ChatResponse
from src.core import Constants
from src.core.Constants import Role, Constants
from src.utils import ChatBot, Utilities

class Evaluator:
    evaluation_system_prompt = "\n".join(Utilities.load_rules_from_file("evaluation_prompt.json", "Ruleset 1")).replace("$PASS$", Constants.pass_name).replace("$FAIL$", Constants.fail_name).replace("$UNDETERMINED$", Constants.undetermined_name)

    def evaluate_conversation(conversation_message_history_str, pass_fail_condition) -> ChatResponse:        
        evaluation_user_prompt = f"""Evaluate whether the following condition is met in the given conversation.
        Condition:
        {pass_fail_condition}

        Conversation:
        {conversation_message_history_str}
        """

        evaluation_message_history = [
            {"role": Role.system.value, "content": Evaluator.evaluation_system_prompt},
            {"role": Role.user.value, "content": evaluation_user_prompt},
        ]

        response = ChatBot.call_llm(evaluation_message_history)
        responseObj = Utilities.extract_response_obj(response, ChatResponse)

        # return the responseObj as a json string formatted with newlines
        return responseObj