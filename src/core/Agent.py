from dataclasses import dataclass
from typing import List, Type, TypeVar, Dict

from src.core.ChatMessage import ChatMessage
from src.core.ResponseTypes import ChatResponse
from src.utils import llm_utils
from src.core.Constants import Constants as constants, Role
from src.utils.ChatBot import ChatBot

T = TypeVar('T')

class Agent:
    response_type: Type[T]
    response_formatting_suffix: str

    system_prompt: str
    message_history: List[ChatMessage]
    user_prompt_wrapper: str = constants.user_message_placeholder

    def __init__(self, system_prompt: str, response_type: Type[T]):
        self.system_prompt = system_prompt
        self.response_type = response_type
        self.response_formatting_suffix = llm_utils.get_formatting_suffix(response_type)
        self.message_history = []

    def chat(self, user_message: str) -> T:
        if self.system_prompt is None:
            raise Exception("System prompt is required for agent chat")

        if self.message_history is None:
            raise Exception("Message history is required for agent chat")

        chat_history_dict = llm_utils.convert_messaget_history_to_llm_format(self.message_history, include_hidden_details=True)

        # Prepend the system prompt to the chat history
        full_message_history_dict = self._prepend_system_prompt(chat_history_dict, self.system_prompt)

        # Wrap the latest user message if requested
        if user_message is not None and self.user_prompt_wrapper:
            user_prompt_wrapped = self.user_prompt_wrapper.replace(constants.user_message_placeholder, user_message)
            full_message_history_dict[-1]["content"] = user_prompt_wrapped

        # Call the LLM and append assistant response
        response_obj: ChatResponse = ChatBot.call_llm(full_message_history_dict, ChatResponse)
        return response_obj
    
        
    def update_system_prompt(self, system_prompt: str) -> None:
        self.system_prompt = system_prompt

    def update_message_history(self, message_history: List[ChatMessage]) -> None:
        self.message_history = message_history
    

    # ---------- Helpers ----------
    def _prepend_system_prompt(self, chat_history_formatted: List[Dict[str, str]], system_prompt: str) -> List[Dict[str, str]]:
        return [{"role": Role.system.value, "content": system_prompt}] + chat_history_formatted
