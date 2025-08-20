from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

from src.core.schemas.Schemas import GameSettings
from src.core.ConversationMemory import ConversationMemory
from src.core.ResponseTypes import ChatResponse
from src.core.Constants import Constants as constants
from src.core.Constants import Role
from src.utils import llm_utils
from src.utils.ChatBot import ChatBot


class BaseNPC(ABC):
    """Abstract base class for NPCs. Concrete implementations (POC1, POC2) provide
    persistence and system-prompt construction details.
    """

    # Stateful properties common to all NPCs
    conversation_memory: ConversationMemory
    user_prompt_wrapper: str = constants.user_message_placeholder
    chat_formatting_suffix: str
    game_settings: GameSettings
    npc_name: str
    is_new_game: bool

    def __init__(self, game_settings: GameSettings, npc_name: str, is_new_game: bool):
        self.game_settings = game_settings
        self.npc_name = npc_name
        self.is_new_game = is_new_game
        self.chat_formatting_suffix = llm_utils.get_formatting_suffix(ChatResponse)

    # ---------- Public API ----------
    def maintain(self) -> None:
        """Perform periodic maintenance (e.g., summarization) and persist state."""
        self.conversation_memory.maintain()
        self.save_state()

    def inject_message(self, response: str, role: Role = Role.assistant, cot: Optional[str] = None, off_switch: bool = False) -> None:
        self.conversation_memory.append_chat(response, role=role, cot=cot, off_switch=off_switch)

    def call_llm_for_chat(self, user_message: Optional[str] = None, enable_printing: bool = False) -> ChatResponse:
        # Add the latest user prompt to the chat history. If none, skip this step
        if user_message is not None:
            self.conversation_memory.append_chat(user_message, role=Role.user, off_switch=False)

        # Get the chat history formatted for LLM
        chat_history_dict = self.conversation_memory.get_chat_memory_in_llm_format(include_hidden_details=True)

        # Prepend the system prompt to the chat history
        full_message_history_dict = self._prepend_system_prompt(chat_history_dict, self.build_system_prompt())

        # Wrap the latest user message if requested
        if user_message is not None and self.user_prompt_wrapper:
            user_prompt_wrapped = self.user_prompt_wrapper.replace(constants.user_message_placeholder, user_message)
            full_message_history_dict[-1]["content"] = user_prompt_wrapped

        # Call the LLM and append assistant response
        response_obj: ChatResponse = ChatBot.call_llm(full_message_history_dict, ChatResponse)
        self.conversation_memory.append_chat(
            response_obj.response,
            role=Role.assistant,
            off_switch=response_obj.off_switch,
            cot=response_obj.hidden_thought_process,
        )
        return response_obj

    # ---------- Helpers ----------
    def _prepend_system_prompt(self, chat_history_formatted: List[Dict[str, str]], system_prompt: str) -> List[Dict[str, str]]:
        return [{"role": Role.system.value, "content": system_prompt}] + chat_history_formatted

    # ---------- Abstracts to be implemented by subclasses ----------
    @abstractmethod
    def build_system_prompt(self) -> str:
        """Return full system prompt including context and formatting suffix."""

    @abstractmethod
    def get_initial_response(self) -> str:
        """Return initial assistant response (may be empty to trigger normal flow)."""

    @abstractmethod
    def save_state(self) -> None:
        ...

    @abstractmethod
    def load_state(self) -> None:
        ...

    @abstractmethod
    def init_state(self) -> None:
        ...


