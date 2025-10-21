from dataclasses import dataclass
import os
from pathlib import Path
from typing import List, Optional

from src.brain.brain_memory import BrainMemory
from src.core.schemas.CollectionSchemas import Entity
from src.utils import io_utils
from src.utils import Logger
from src.utils.Logger import Level
from src.core.ConversationMemory import ConversationMemory, ConversationMemoryState
from src.core.ResponseTypes import ChatResponse
from src.core.Constants import Role, Constants as constants
from src.core.Agent import Agent
from src.core import proj_paths
from dataclasses import dataclass, field

@dataclass
class NPCState:
    conversation_memory: ConversationMemoryState
    system_context: str
    user_prompt_wrapper: str


@dataclass
class NPCTemplate:
    response_system_prompt: str
    preprocess_system_prompt: str | None = None
    summarization_prompt: str | None = None


@dataclass
class PreprocessedUserInput:
    text: str = field(metadata={"desc": "The reworded user message. NEVER EMPTY. If you don't know what to say, just put the original message in here."})
    has_information: bool = field(metadata={"desc": "Whether the input contains information that the assistant should remember."})
    ambiguous_pronouns: str = field(metadata={"desc": "A list of pronouns that are ambiguous and need clarification.", "type": "strlist"})
    needs_clarification: bool = field(metadata={"desc": "Whether you need clarification on any of the pronouns."})


# NPC2 has the following features:
# - All of the features of poc1
# - A VDB that contains memories that can get queried on relevance
# - Can determine if user message has info and will store the info in the memory VDB
# - A weak pronoun resolver

class NPC2:
    # Stateful properties common to all NPCs
    conversation_memory: ConversationMemory
    brain_memory: BrainMemory

    user_prompt_wrapper: str = constants.user_message_placeholder
    npc_name: str
    is_new_game: bool
    save_paths: proj_paths.SavePaths
    template: NPCTemplate

    response_agent: Agent
    preprocessor_agent: Agent

    # Settings
    last_messages_to_retain_for_preprocessor: int = 4

    def __init__(self, npc_name_for_template_and_save: str):
        self.save_paths = proj_paths.get_paths()
        self.npc_name = npc_name_for_template_and_save
        self.template = io_utils.load_yaml_into_dataclass(self.save_paths.npc_template(npc_name_for_template_and_save), NPCTemplate)
        
        # Init the agents
        self.response_agent = Agent(system_prompt=None, response_type=ChatResponse)
        self.preprocessor_agent = Agent(system_prompt=None, response_type=PreprocessedUserInput)

        # Initialize the brain memory (backed by a persistent collection so doesn't matter if new game or not)
        # For the collection name, include the version, save name and NPC name
        collection_name = f"{self.save_paths.save_name}_{self.npc_name}_v{self.save_paths.version}"
        self.brain_memory = BrainMemory(collection_name=collection_name)

        existing_save_found = self._check_for_existing_save()
        if existing_save_found:
            self._load_state()
        else:
            self._init_state()
    
    # ---------- Private API - Helpers ---------

    def _check_for_existing_save(self) -> bool:
        return os.path.exists(self.save_paths.save_dir)

    def _build_system_prompt(self, include_conversation_summary: bool = True, include_brain_context: bool = True) -> str:
        parts: List[str] = []
        parts.append("Context:\n" + self.template.response_system_prompt)
        
        if include_conversation_summary:
            parts.append("Prior conversation summary:\n" + self.conversation_memory.get_chat_summary_as_string())
        
        if include_brain_context:
            # Get brain context from recent user input
            recent_user_messages = [msg for msg in self.conversation_memory.chat_memory if msg.role == Role.user]
            if recent_user_messages:
                last_user_message = recent_user_messages[-1].content
                memories = self.brain_memory.get_memories(last_user_message, topk=5, as_str=True)
                if memories:
                    parts.append("Brain context:\n" + memories)
        
        return "\n\n".join(parts) + "\n\n"

    def _preprocess_input(self, user_message: str) -> PreprocessedUserInput:
        # Use only the template-provided preprocess prompt
        preprocess_agent_system_prompt = self.template.preprocess_system_prompt
        if not preprocess_agent_system_prompt:
            raise ValueError("preprocess_system_prompt is required in NPCTemplate")
        
        # Get brain memories to provide context for preprocessor, using the last user message
        if user_message:
            memories = self.brain_memory.get_memories(user_message, topk=3, as_str=True)
            if memories:
                preprocess_agent_system_prompt += f"""
                Context:
                {memories}
                """

        self.preprocessor_agent.update_system_prompt(preprocess_agent_system_prompt)
        message_history_truncated = self.conversation_memory.chat_memory[-self.last_messages_to_retain_for_preprocessor:]
        Logger.verbose(f"Full input to preprocessor LLM:\nContext:{preprocess_agent_system_prompt}\nMessage History:\n{message_history_truncated}")
        preprocessed_message: PreprocessedUserInput = self.preprocessor_agent.chat_with_history(message_history_truncated)
        if preprocessed_message.text == "":
            preprocessed_message.text = "<empty>"
        return preprocessed_message

    # ---------- Private API - State Management ----------

    def _save_state(self) -> None:
        os.makedirs(self.save_paths.npc_save_dir(self.npc_name), exist_ok=True)
        save_path = self.save_paths.npc_save_state(self.npc_name)
        current_state = NPCState(
            conversation_memory=self.conversation_memory.get_state(),
            system_context=self.template.response_system_prompt,
            user_prompt_wrapper=self.user_prompt_wrapper,
        )
        io_utils.save_to_yaml_file(current_state, save_path)
        Logger.log(f"Session saved successfully to {save_path}", Level.INFO)
        # Note that the vdb collection does not need to be saved.

    def _load_state(self) -> None:
        try:
            # Load the conversation memory and other metadata for the NPC
            prior: NPCState = io_utils.load_yaml_into_dataclass(self.save_paths.npc_save_state(self.npc_name), NPCState)
            self.conversation_memory = ConversationMemory.from_state(prior.conversation_memory, self.template.summarization_prompt)
            self.user_prompt_wrapper = prior.user_prompt_wrapper
        except FileNotFoundError as e:
            Logger.log(f"NPC state file not found: {e}", Level.ERROR)
            Logger.log("Starting a new game.", Level.INFO)
            self._init_state()

    def _init_state(self) -> None:
        # Create a fresh conversation memory
        self.conversation_memory = ConversationMemory.from_new(self.template.summarization_prompt)
        self.brain_memory.clear_all_memories()
        self.brain_memory.load_entities_from_template(self.save_paths.npc_entities_template(self.npc_name))


    # ---------- Public API / Protocol ----------
    def maintain(self) -> None:
        """Perform periodic maintenance (e.g., summarization) and persist state."""
        self.conversation_memory.maintain()
        self._save_state()
        self.brain_memory.maintain()

    def inject_message(self, response: str, role: Role = Role.assistant, cot: Optional[str] = None, off_switch: bool = False) -> None:
        self.conversation_memory.append_chat(response, role=role, cot=cot, off_switch=off_switch)

    def get_all_memories(self) -> List[Entity]:
        return self.brain_memory.get_all_memories()

    def load_entities_from_template(self, template_path: Path) -> None:
        self.brain_memory.load_entities_from_template(template_path)

    def clear_brain_memory(self) -> None:
        self.brain_memory.clear_all_memories()

    def chat(self, user_message: Optional[str]) -> ChatResponse:
        """Primary chat API: preprocess, update brain, build prompt, respond, persist. Returns ChatResponse."""
        if user_message is None:
            user_message = ""
        # Add user message to conversation history
        self.conversation_memory.append_chat(user_message, role=Role.user, off_switch=False)

        # Preprocess using brain context
        preprocessed_message: PreprocessedUserInput = self._preprocess_input(user_message)
        Logger.warning(f"Preprocessed message: {preprocessed_message}")

        if preprocessed_message.needs_clarification:
            clarification = (
                "I need clarification on one or more of the pronouns you used. Please rephrase your message."
            )
            self.conversation_memory.append_chat(clarification, role=Role.assistant, cot=None, off_switch=False)
            return ChatResponse(hidden_thought_process=None, response=clarification, off_switch=False)

        # Update brain memory if there's information
        if preprocessed_message.has_information:
            self.brain_memory.add_memory(preprocessed_user_text=preprocessed_message.text)

        # Build system prompt (includes convo summary and brain context)
        self.response_agent.update_system_prompt(self._build_system_prompt())

        # Call response agent with full conversation history
        response_obj: ChatResponse = self.response_agent.chat_with_history(self.conversation_memory.chat_memory)

        # Append response to conversation
        assistant_text = response_obj.response
        self.conversation_memory.append_chat(
            assistant_text,
            role=Role.assistant,
            off_switch=response_obj.off_switch,
            cot=response_obj.hidden_thought_process,
        )

        return response_obj
