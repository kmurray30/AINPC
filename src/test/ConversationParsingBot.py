

from typing import List
from src.core.ResponseTypes import EvaluationResponse
from src.core import Constants
from src.core.Constants import Role, Constants
from src.utils import ChatBot, Utilities
from src.test.TestClasses import Proposition

class ConversationParsingBot:

    @staticmethod
    def evaluate_conversation(conversation_message_history: List[str], proposition: Proposition) -> EvaluationResponse:
        if proposition.antecedent is not None:
            evaluation_system_prompt_raw = "\n".join(Utilities.load_rules_from_file("evaluation_prompt.json", "Ruleset 5"))
            evaluation_system_prompt = evaluation_system_prompt_raw.replace(Constants.antecedent_placeholder, proposition.antecedent.value).replace(Constants.consequent_placeholder, proposition.consequent.value)
        else:
            evaluation_system_prompt_raw = "\n".join(Utilities.load_rules_from_file("evaluation_prompt.json", "Ruleset 6"))
            evaluation_system_prompt = evaluation_system_prompt_raw.replace(Constants.antecedent_placeholder, "").replace(Constants.consequent_placeholder, proposition.consequent.value)
        conversation_message_history_str = "\n".join(conversation_message_history)

        evaluation_user_prompt = f"""
        #Conversation:#
        {conversation_message_history_str}
        """

        evaluation_message_history = [
            {"role": Role.system.value, "content": evaluation_system_prompt},
            {"role": Role.user.value, "content": evaluation_user_prompt},
        ]

        # print(f"Evaluation message history: {evaluation_message_history}")

        response = ChatBot.call_llm(evaluation_message_history)
        # print(f"Evaluation response: {response}")
        responseObj = Utilities.extract_response_obj(response, EvaluationResponse)

        # return the responseObj as a json string formatted with newlines
        return responseObj