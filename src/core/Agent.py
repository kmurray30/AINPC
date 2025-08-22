from dataclasses import dataclass
from typing import List, Type, TypeVar, Dict

from src.core.ChatMessage import ChatMessage
from src.core.ResponseTypes import ChatResponse
from src.utils import llm_utils
from src.core.Constants import Constants as constants, Role, Llm
from src.utils.ChatBot import ChatBot

T = TypeVar('T')

class Agent:
    llm_model: Llm = None
    
    response_type: Type[T]
    response_formatting_suffix: str = ""

    system_prompt: str
    user_prompt_wrapper: str = constants.user_message_placeholder

    def __init__(self, system_prompt: str, response_type: Type[T], llm_model: Llm = None):
        self.system_prompt = system_prompt
        self.response_type = response_type
        if response_type is not None:
            self.response_formatting_suffix = llm_utils.get_formatting_suffix(response_type)
        self.llm_model = llm_model

    def chat_with_message(self, user_message: str) -> T:
        message = ChatMessage(role=Role.user, content=user_message, cot=None, off_switch=False)
        response_obj: T = self.chat_with_history([message])
        return response_obj

    def chat_with_history(self, message_history: List[ChatMessage]) -> T:
        if self.system_prompt is None:
            raise Exception("System prompt is required for agent chat")

        chat_history_dict = llm_utils.convert_message_history_to_llm_format(message_history, include_hidden_details=True)

        # Prepend the system prompt to the chat history
        full_system_prompt = self.system_prompt + "\n\n" + self.response_formatting_suffix
        full_message_history_dict = self._prepend_system_prompt(chat_history_dict, full_system_prompt)

        # Wrap the latest user message if requested
        if self.user_prompt_wrapper and message_history[-1].role == Role.user:
            user_message = message_history[-1].content
            user_prompt_wrapped = self.user_prompt_wrapper.replace(constants.user_message_placeholder, user_message)
            full_message_history_dict[-1]["content"] = user_prompt_wrapped

        # Call the LLM and append assistant response
        response_obj: T = ChatBot.call_llm(full_message_history_dict, self.response_type, self.llm_model)
        return response_obj
    
        
    def update_system_prompt(self, system_prompt: str) -> None:
        self.system_prompt = system_prompt
    

    # ---------- Helpers ----------
    def _prepend_system_prompt(self, chat_history_formatted: List[Dict[str, str]], system_prompt: str) -> List[Dict[str, str]]:
        return [{"role": Role.system.value, "content": system_prompt}] + chat_history_formatted
