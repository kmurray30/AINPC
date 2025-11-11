

from typing import List
from src.core.ResponseTypes import EvaluationResponse
from src.core import Constants
from src.core.Constants import Role, Constants, Llm
from src.utils import io_utils, parsing_utils
from src.utils.ChatBot import ChatBot
from src.conversation_eval.EvalClasses import Proposition
from src.conversation_eval.StreamingEvalDisplay import get_streaming_display, EvaluationResult

class ConversationParsingBot:

    chat_bot: ChatBot = ChatBot
    chat_bot.set_chat_model(Llm.gpt_4o_mini)

    @staticmethod
    def evaluate_conversation_timestamps(conversation_message_history: List[str], proposition: Proposition) -> EvaluationResponse:
        streaming_display = get_streaming_display()
        
        if streaming_display.enabled:
            streaming_display.display_evaluation_progress("Analyzing conversation for antecedent and consequent...")
        
        if proposition.antecedent is not None:
            evaluation_system_prompt_raw = "\n".join(io_utils.load_rules_from_file("evaluation_prompt.json", "Ruleset 5"))
            evaluation_system_prompt = evaluation_system_prompt_raw.replace(Constants.antecedent_placeholder, proposition.antecedent.value).replace(Constants.consequent_placeholder, proposition.consequent.value)
        else:
            evaluation_system_prompt_raw = "\n".join(io_utils.load_rules_from_file("evaluation_prompt.json", "Ruleset 6"))
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

        if streaming_display.enabled:
            streaming_display.display_evaluation_progress("Calling LLM for evaluation...")

        response = ConversationParsingBot.chat_bot.call_llm(evaluation_message_history)
        responseObj = parsing_utils.extract_obj_from_json_str(response, EvaluationResponse, trim=True)

        # Display evaluation results in streaming display
        if streaming_display.enabled:
            # Determine if evaluation passed (basic logic - can be enhanced)
            passed = len(responseObj.consequent_times) > 0
            if proposition.antecedent is not None:
                passed = passed and len(responseObj.antecedent_times) > 0
            
            eval_result = EvaluationResult(
                antecedent_timestamps=responseObj.antecedent_times,
                consequent_timestamps=responseObj.consequent_times,
                passed=passed,
                explanation=responseObj.consequent_explanation if hasattr(responseObj, 'consequent_explanation') else ""
            )
            streaming_display.display_evaluation_result(eval_result)

        return responseObj