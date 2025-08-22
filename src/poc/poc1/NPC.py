from dataclasses import dataclass
import os
from typing import List

from src.core.BaseNPC import BaseNPC
from src.core.schemas.Schemas import GameSettings
from src.utils import io_utils, llm_utils
from src.utils import Logger
from src.utils.Logger import Level
from src.core.ConversationMemory import ConversationMemory, ConversationMemoryState
from src.core.ResponseTypes import ChatResponse
from src.core.Constants import Role
from src.poc import proj_paths, proj_settings


@dataclass
class NPCState:
    conversation_memory: ConversationMemoryState
    system_context: str
    user_prompt_wrapper: str


@dataclass
class NPCTemplate:
    initial_system_context: str
    initial_response: str | None = None


class NPC(BaseNPC):
    save_paths: proj_paths.SavePaths
    template: NPCTemplate

    def __init__(self, is_new_game: bool, npc_name: str):
        self.save_paths = proj_paths.get_paths()
        game_settings = proj_settings.get_settings().game_settings
        super().__init__(game_settings=game_settings, npc_name=npc_name, is_new_game=is_new_game)

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


