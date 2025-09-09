from dataclasses import dataclass
import os
from typing import List, Optional

from src.utils import VectorUtils, io_utils, Utilities
from src.utils import Logger
from src.utils.Logger import Level
from src.core.ConversationMemory import ConversationMemory, ConversationMemoryState
from src.core.ResponseTypes import ChatResponse
from src.core.Constants import Role, Constants as constants
from src.core.Agent import Agent
from src.core import proj_paths
from src.core.schemas.CollectionSchemas import Entity
from dataclasses import dataclass, field
from src.utils.QdrantCollection import QdrantCollection


@dataclass
class PreprocessedUserInput:
    text: str = field(metadata={"desc": "The reworded user message. NEVER EMPTY. If you don't know what to say, just put the original message in here."})
    has_information: bool = field(metadata={"desc": "Whether the input contains information that the assistant should remember."})
    ambiguous_pronouns: str = field(metadata={"desc": "A list of pronouns that are ambiguous and need clarification.", "type": "strlist"})
    needs_clarification: bool = field(metadata={"desc": "Whether you need clarification on any of the pronouns."})


@dataclass
class NPCState:
    conversation_memory: ConversationMemoryState
    system_context: str
    user_prompt_wrapper: str


@dataclass
class NPCTemplate:
    response_system_prompt: str
    preprocess_system_prompt: str | None = None


class NPC:
    # Stateful properties common to all NPCs
    conversation_memory: ConversationMemory
    user_prompt_wrapper: str = constants.user_message_placeholder
    response_agent: Agent
    preprocessor_agent: Agent
    npc_name: str
    is_new_game: bool
    save_paths: proj_paths.SavePaths
    template: NPCTemplate
    
    # Brain memory properties
    collection: QdrantCollection
    collection_name: str = "simple_brain"
    TEST_DIMENSION: int = 1536

    def __init__(self, is_new_game: bool, npc_name: str):
        self.save_paths = proj_paths.get_paths()
        self.npc_name = npc_name
        self.is_new_game = is_new_game
        self.response_agent = Agent(system_prompt=None, response_type=ChatResponse)
        self.preprocessor_agent = Agent(system_prompt=None, response_type=PreprocessedUserInput)
        self.template = io_utils.load_yaml_into_dataclass(self.save_paths.npc_template(npc_name), NPCTemplate)
        # Bind Qdrant collection wrapper to this NPC's brain collection
        self.collection = QdrantCollection(self.collection_name)

        # Initialize or load the brain memory and conversation memory
        if not is_new_game:
            self._load_state()
        else:
            self._init_state()
    
    # ---------- Private API - Helpers ---------

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
                memories = self._get_memories(last_user_message, topk=5)
                brain_context = self._build_memory_context(memories)
                if brain_context:
                    parts.append("Brain context:\n" + brain_context)
        
        return "\n\n".join(parts) + "\n\n"

    # ---------- Private API - State Management ----------

    def _save_state(self) -> None:
        os.makedirs(self.save_paths.npc_save(self.npc_name), exist_ok=True)
        save_path = self.save_paths.npc_save_state(self.npc_name)
        current_state = NPCState(
            conversation_memory=self.conversation_memory.get_state(),
            system_context=self.template.response_system_prompt,
            user_prompt_wrapper=self.user_prompt_wrapper,
        )
        io_utils.save_to_yaml_file(current_state, save_path)
        Logger.log(f"Session saved successfully to {save_path}", Level.INFO)
        # Note that the milvus collection does not need to be saved. TODO save it once using docker?

    def _load_state(self) -> None:
        try:
            # Ensure the Qdrant collection exists and track by name
            self.collection.create(dim=self.TEST_DIMENSION)
            
            # Load the conversation memory and other metadata for the NPC
            prior: NPCState = io_utils.load_yaml_into_dataclass(self.save_paths.npc_save_state(self.npc_name), NPCState)
            self.conversation_memory = ConversationMemory.from_state(prior.conversation_memory)
            self.user_prompt_wrapper = prior.user_prompt_wrapper
        except FileNotFoundError as e:
            Logger.log(f"NPC state file not found: {e}", Level.ERROR)
            Logger.log("Starting a new game.", Level.INFO)
            self._init_state()

    def _init_state(self) -> None:
        # Create a fresh Qdrant collection which holds the brain memory
        self.collection.create(dim=self.TEST_DIMENSION)

        # Create a fresh conversation memory
        self.conversation_memory = ConversationMemory.from_new()

    # ---------- Private API - Brain Memory Management ----------

    def _preprocess_input(self, message_history: List, last_messages_to_retain: int = 4) -> PreprocessedUserInput:
        # Use only the template-provided preprocess prompt
        preprocess_agent_system_prompt = self.template.preprocess_system_prompt
        if not preprocess_agent_system_prompt:
            raise ValueError("preprocess_system_prompt is required in NPCTemplate")
        
        # Get brain context for preprocessor
        recent_user_messages = [msg for msg in message_history if msg.role == Role.user]
        if recent_user_messages:
            last_user_message = recent_user_messages[-1].content
            memories = self._get_memories(last_user_message, topk=3)
            brain_context = self._build_memory_context(memories)
            if brain_context:
                preprocess_agent_system_prompt += f"""
                Context:
                {brain_context}
                """

        self.preprocessor_agent.update_system_prompt(preprocess_agent_system_prompt)
        message_history_truncated = message_history[-last_messages_to_retain:]
        Logger.verbose(f"Full input to preprocessor LLM:\nContext:{preprocess_agent_system_prompt}\nMessage History:\n{message_history_truncated}")
        preprocessed_message = self.preprocessor_agent.chat_with_history(message_history_truncated)
        if preprocessed_message.text == "":
            preprocessed_message.text = "<empty>"
        return preprocessed_message

    def _update_brain_memory(self, preprocessed_user_text: str):
        rows = [
            Entity(
                key=preprocessed_user_text,
                content=preprocessed_user_text,
                tags=["memories"],
                id=int(Utilities.generate_uuid_int64()),
            ),
        ]
        Logger.verbose(f"Updating memory with {preprocessed_user_text}")
        self.collection.insert_dataclasses(rows)

    def _get_memories(self, preprocessed_user_text: str, topk: int = 5) -> List[Entity]:
        hits = self.collection.search_text(preprocessed_user_text, topk=topk)
        Logger.verbose(f"Found {len(hits)} memories for {preprocessed_user_text}")
        # Print the memories with their similarity scores
        for hit in hits:
            Logger.verbose(f"Similarity: {hit[1]}, Content: {hit[0].content}")
        return [hit[0] for hit in hits]

    def _build_memory_context(self, memories: List[Entity]):
        context = "\n".join([f"{memory.content}" for memory in memories])
        return context

    # ---------- Public API ----------
    def maintain(self) -> None:
        """Perform periodic maintenance (e.g., summarization) and persist state."""
        self.conversation_memory.maintain()
        self._save_state()
        # Persist embedding cache associated with the collection
        self.collection.embedding_cache.save()

    def inject_message(self, response: str, role: Role = Role.assistant, cot: Optional[str] = None, off_switch: bool = False) -> None:
        self.conversation_memory.append_chat(response, role=role, cot=cot, off_switch=off_switch)

    def get_all_memories(self) -> List[Entity]:
        """API method for /list command"""
        all_memories = self.collection.export_entities()
        Logger.verbose(f"All memories:")
        return all_memories

    def load_entities_from_template(self, template_path: str) -> None:
        """API method for /load command"""
        if not template_path.endswith(".yaml"):
            raise ValueError("File must be a yaml file")

        template_path = os.path.join(os.path.dirname(__file__), template_path)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"File {template_path} does not exist")

        from src.brain import template_processor
        entities = template_processor.template_to_entities_simple(template_path)
        # Ensure each entity has an id for Qdrant
        for e in entities:
            if getattr(e, "id", None) is None:
                e.id = int(Utilities.generate_uuid_int64())
        self.collection.insert_dataclasses(entities)
        Logger.verbose(f"Loaded {len(entities)} entities from {template_path}")

    def clear_brain_memory(self) -> None:
        """API method for /clear command"""
        self.collection.drop_if_exists()
        self.collection.create(dim=self.TEST_DIMENSION)

    def chat(self, user_message: Optional[str]) -> ChatResponse:
        """Primary chat API: preprocess, update brain, build prompt, respond, persist. Returns ChatResponse."""
        if user_message is None:
            user_message = ""
        # Add user message to conversation history
        self.conversation_memory.append_chat(user_message, role=Role.user, off_switch=False)

        # Preprocess using brain context
        preprocessed_message: PreprocessedUserInput = self._preprocess_input(
            self.conversation_memory.chat_memory,
            last_messages_to_retain=4,
        )
        Logger.warning(f"Preprocessed message: {preprocessed_message}")

        if preprocessed_message.needs_clarification:
            clarification = (
                "I need clarification on one or more of the pronouns you used. Please rephrase your message."
            )
            self.conversation_memory.append_chat(clarification, role=Role.assistant, cot=None, off_switch=False)
            return ChatResponse(hidden_thought_process=None, response=clarification, off_switch=False)

        # Update brain memory if there's information
        if preprocessed_message.has_information:
            self._update_brain_memory(preprocessed_user_text=preprocessed_message.text)

        # Build system prompt (includes convo summary and brain context)
        self.response_agent.update_system_prompt(self._build_system_prompt())

        # Call response agent with full conversation history
        response_obj: ChatResponse | str = self.response_agent.chat_with_history(self.conversation_memory.chat_memory)

        # Normalize to ChatResponse
        if not isinstance(response_obj, ChatResponse):
            response_obj = ChatResponse(hidden_thought_process=None, response=str(response_obj), off_switch=False)

        # Append response to conversation
        assistant_text = response_obj.response
        self.conversation_memory.append_chat(
            assistant_text,
            role=Role.assistant,
            off_switch=response_obj.off_switch,
            cot=response_obj.hidden_thought_process,
        )
        return response_obj


