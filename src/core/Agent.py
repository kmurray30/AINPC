from dataclasses import dataclass
from typing import Type, TypeVar

from src.utils import llm_utils

T = TypeVar('T')

class Agent:
    system_prompt: str
    response_type: Type[T]
    response_formatting_suffix: str

    def __init__(self, system_prompt: str, response_type: Type[T]):
        self.system_prompt = system_prompt
        self.response_type = response_type
        self.response_formatting_suffix = llm_utils.get_formatting_suffix(response_type)

    def get_response(self, user_message: str) -> T:
        pass

    def get_response_with_chat_history(self, chat_history: List[ChatMessage], user_message: str) -> T:
        pass
