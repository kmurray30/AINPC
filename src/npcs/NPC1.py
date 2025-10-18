from dataclasses import dataclass
import os
from pathlib import Path
from typing import List, Optional

from src.core.schemas.CollectionSchemas import Entity
from src.core.schemas.Schemas import AppSettings
from src.utils import Utilities, io_utils, llm_utils
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
    summarization_prompt: str
    brain_entities: List[Entity]


@dataclass
class NPCTemplate:
    initial_system_context: str
    initial_response: str | None = None
    summarization_prompt: str | None = None


# NPC1 has the following features:
# - A static system prompt
# - Conversation memory that can be summarized ad hoc
class NPC1:
    # Stateful properties common to all NPCs
    conversation_memory: ConversationMemory
    user_prompt_wrapper: str = constants.user_message_placeholder
    response_agent: Agent
    app_settings: AppSettings
    npc_name: str
    is_new_game: bool
    save_paths: proj_paths.SavePaths
    template: NPCTemplate
    brain_entities: List[Entity]

    def __init__(self, npc_name_for_template_and_save: str):
        self.save_paths = proj_paths.get_paths()
        self.app_settings = proj_settings.get_settings().app_settings
        self.npc_name = npc_name_for_template_and_save
        self.response_agent = Agent(system_prompt=None, response_type=ChatResponse)

        self.template = io_utils.load_yaml_into_dataclass(self.save_paths.npc_template(npc_name_for_template_and_save), NPCTemplate)

        existing_save_found = self._check_for_existing_save()
        if existing_save_found:
            self._load_state()
        else:
            self._init_state()

    # -------- Private API --------
    def _check_for_existing_save(self) -> bool:
        return os.path.exists(self.save_paths.save_dir)

    def _build_system_prompt(self) -> str:
        parts: List[str] = []
        parts.append("Context:\n" + self.template.initial_system_context)
        parts.append("Brain context:\n" + "\n".join([e.content for e in self.brain_entities]))
        parts.append("Prior conversation summary:\n" + self.conversation_memory.get_chat_summary_as_string())
        return "\n\n".join(parts) + "\n\n"

    def _get_initial_response(self) -> str:
        return self.template.initial_response or ""

    def _get_state(self) -> NPCState:
        return NPCState(
            conversation_memory=self.conversation_memory.get_state(),
            system_context=self.template.initial_system_context,
            user_prompt_wrapper=self.user_prompt_wrapper,
            summarization_prompt=self.template.summarization_prompt,
            brain_entities=self.brain_entities,
        )

    def _save_state(self) -> None:
        os.makedirs(self.save_paths.npc_save_dir(self.npc_name), exist_ok=True)
        save_path = self.save_paths.npc_save_state(self.npc_name)
        current_state = self._get_state()
        io_utils.save_to_yaml_file(current_state, save_path)
        Logger.log(f"Session saved successfully to {save_path}", Level.INFO)

    def _load_state(self) -> None:
        Logger.log(f"Loading state from {self.save_paths.npc_save_state(self.npc_name)}", Level.INFO)
        try:
            prior_state: NPCState = io_utils.load_yaml_into_dataclass(self.save_paths.npc_save_state(self.npc_name), NPCState)
            self.conversation_memory = ConversationMemory.from_state(prior_state.conversation_memory, summarization_prompt=self.template.summarization_prompt)
            self.user_prompt_wrapper = prior_state.user_prompt_wrapper
            self.template.summarization_prompt = prior_state.summarization_prompt
            self.brain_entities = prior_state.brain_entities
        except FileNotFoundError as e:
            Logger.log(f"NPC state file not found: {e}", Level.ERROR)
            raise e

    def _init_state(self) -> None:
        Logger.log(f"Initializing state for {self.npc_name}", Level.INFO)
        self.conversation_memory = ConversationMemory.from_new(summarization_prompt=self.template.summarization_prompt)
        self.load_entities_from_template(self.save_paths.npc_entities_template(self.npc_name))

    # ---------- Public API / Protocol ----------
    def maintain(self) -> None:
        """Perform periodic maintenance (e.g., summarization) and persist state."""
        self.conversation_memory.maintain()
        self._save_state()

    def inject_message(self, response: str, role: Role = Role.assistant, cot: Optional[str] = None, off_switch: bool = False) -> None:
        self.conversation_memory.append_chat(response, role=role, cot=cot, off_switch=off_switch)

    def chat(self, user_message: Optional[str] = None) -> ChatResponse:
        # Add the latest user prompt to the chat history. If none, skip this step
        if user_message is not None:
            self.conversation_memory.append_chat(user_message, role=Role.user, off_switch=False)

        self.response_agent.update_system_prompt(self._build_system_prompt())
        response_obj: ChatResponse = self.response_agent.chat_with_history(self.conversation_memory.chat_memory)
        self.conversation_memory.append_chat(
            response_obj.response,
            role=Role.assistant,
            off_switch=response_obj.off_switch,
            cot=response_obj.hidden_thought_process,
        )
        return response_obj
    
    def load_entities_from_template(self, template_path: Path) -> None:
        Logger.log(f"Loading entities from {template_path}", Level.INFO)
        entities_strs = io_utils.load_yaml_into_dataclass(template_path, List[str])
        self.brain_entities = [
            Entity(key=e, content=e, tags=["memories"], id=int(Utilities.generate_hash_int64(e))) for e in entities_strs
        ]

    def get_all_memories(self) -> List[Entity]:
        return self.brain_entities

    def clear_brain_memory(self) -> None:
        self.brain_entities = []
