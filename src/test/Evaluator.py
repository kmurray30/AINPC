

from typing import List
from src.core.ChatResponse import ChatResponse
from src.core import Constants
from src.core.Constants import Role, Constants
from src.utils import ChatBot, Utilities
from src.test.TestClasses import Condition

class Evaluator:
    evaluation_system_prompt = "\n".join(Utilities.load_rules_from_file("evaluation_prompt.json", "Ruleset 3")).replace("$PASS$", Constants.pass_name).replace("$FAIL$", Constants.fail_name).replace("$UNDETERMINED$", Constants.undetermined_name)
    # print(evaluation_system_prompt)

    def evaluate_conversation(conversation_message_history: List[str], pass_fail_condition: Condition) -> ChatResponse:
        conversation_message_history_str = "\n".join(conversation_message_history)

        evaluation_user_prompt = f"""
        #Condition:#
        Antecedent - {pass_fail_condition.antecedent}
        Consequent - {pass_fail_condition.consequent}

        #Conversation:#
        {conversation_message_history_str}
        """

        # print(evaluation_user_prompt)

        evaluation_message_history = [
            {"role": Role.system.value, "content": Evaluator.evaluation_system_prompt},
            {"role": Role.user.value, "content": evaluation_user_prompt},
        ]

        response = ChatBot.call_llm(evaluation_message_history)
        responseObj = Utilities.extract_response_obj(response, ChatResponse)

        # return the responseObj as a json string formatted with newlines
        return responseObj