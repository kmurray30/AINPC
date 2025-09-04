from dataclasses import dataclass
import os
from typing import List, Optional

from src.core.schemas.Schemas import GameSettings
from src.utils import io_utils, llm_utils
from src.utils import Logger
from src.utils.Logger import Level
from src.core.ConversationMemory import ConversationMemory, ConversationMemoryState
from src.core.ResponseTypes import ChatResponse
from src.core.Constants import Role, Constants as constants
from src.core.Agent import Agent
from src.core import proj_paths, proj_settings


@dataclass
class NPCState:
    conversation_memory: ConversationMemoryState
    system_context: str
    user_prompt_wrapper: str


@dataclass
class NPCTemplate:
    initial_system_context: str
    initial_response: str | None = None


class NPC:
    # Stateful properties common to all NPCs
    conversation_memory: ConversationMemory
    user_prompt_wrapper: str = constants.user_message_placeholder
    response_agent: Agent
    game_settings: GameSettings
    npc_name: str
    is_new_game: bool
    save_paths: proj_paths.SavePaths
    template: NPCTemplate

    def __init__(self, is_new_game: bool, npc_name: str):
        self.save_paths = proj_paths.get_paths()
        self.game_settings = proj_settings.get_settings().game_settings
        self.npc_name = npc_name
        self.is_new_game = is_new_game
        self.response_agent = Agent(system_prompt=None, response_type=ChatResponse)

        self.template = io_utils.load_yaml_into_dataclass(self.save_paths.npc_template(npc_name), NPCTemplate)

        if not is_new_game:
            self.load_state()
        else:
            self.init_state()

    # -------- Base overrides --------
    def build_system_prompt(self) -> str:
        parts: List[str] = []
        parts.append("Context:\n" + self.template.initial_system_context)
        parts.append("Prior conversation summary:\n" + self.conversation_memory.get_chat_summary_as_string())
        return "\n\n".join(parts) + "\n\n"

    def get_initial_response(self) -> str:
        return self.template.initial_response or ""

    def save_state(self) -> None:
        os.makedirs(self.save_paths.npc_save(self.npc_name), exist_ok=True)
        save_path = self.save_paths.npc_save_state(self.npc_name)
        current_state = NPCState(
            conversation_memory=self.conversation_memory.get_state(),
            system_context=self.template.initial_system_context,
            user_prompt_wrapper=self.user_prompt_wrapper,
        )
        io_utils.save_to_yaml_file(current_state, save_path)
        Logger.log(f"Session saved successfully to {save_path}", Level.INFO)

    def load_state(self) -> None:
        try:
            prior: NPCState = io_utils.load_yaml_into_dataclass(self.save_paths.npc_save_state(self.npc_name), NPCState)
            self.conversation_memory = ConversationMemory.from_state(prior.conversation_memory)
            self.user_prompt_wrapper = prior.user_prompt_wrapper
        except FileNotFoundError as e:
            Logger.log(f"NPC state file not found: {e}", Level.ERROR)
            Logger.log("Starting a new game.", Level.INFO)
            self.init_state()

    def init_state(self) -> None:
        self.conversation_memory = ConversationMemory.new_game()

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

        self.response_agent.update_system_prompt(self.build_system_prompt())
        response_obj: ChatResponse = self.response_agent.chat_with_history(self.conversation_memory.chat_memory)
        self.conversation_memory.append_chat(
            response_obj.response,
            role=Role.assistant,
            off_switch=response_obj.off_switch,
            cot=response_obj.hidden_thought_process,
        )
        return response_obj


