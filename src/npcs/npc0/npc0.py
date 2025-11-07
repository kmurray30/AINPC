from pathlib import Path
from typing import List, Optional, Dict
from src.core.Constants import Role
from src.core.schemas.CollectionSchemas import Entity
from src.core.ResponseTypes import ChatResponse
from src.core.Agent import Agent
from src.core.ChatMessage import ChatMessage
from src.utils import Utilities, io_utils
from src.npcs.npc_protocol import NPCProtocol


class NPC0:
    """
    NPC0 - The simplest NPC implementation
    
    Features:
    - Uses Agent class for LLM interactions (consistent with NPC1/NPC2)
    - Stores message history in ChatMessage format
    - Minimal state management (no brain memory, no preprocessing)
    - Implements NPCProtocol interface
    """
    
    def __init__(self, system_prompt: str = "You are a helpful assistant."):
        """
        Initialize NPC0 with a system prompt
        
        Args:
            system_prompt: The system prompt to use for this NPC
        """
        self.base_system_prompt = system_prompt
        self.message_history: List[ChatMessage] = []
        self.brain_entities: List[Entity] = []
        self.injected_memories: List[str] = []
        
        # Initialize Agent for LLM interactions (like NPC1/NPC2)
        self.response_agent = Agent(system_prompt=None, response_type=ChatResponse)
    
    def _build_system_prompt(self) -> str:
        """Build the full system prompt including base prompt, memories, and entities"""
        parts = [self.base_system_prompt]
        
        # Add injected memories as background knowledge
        if self.injected_memories:
            memory_text = "Background knowledge:\n" + "\n".join(f"- {memory}" for memory in self.injected_memories)
            parts.append(memory_text)
        
        # Add brain entities as background knowledge
        if self.brain_entities:
            entity_text = "Additional context:\n" + "\n".join(f"- {entity.content}" for entity in self.brain_entities)
            parts.append(entity_text)
        
        return "\n\n".join(parts)
    
    def chat(self, user_message: Optional[str]) -> ChatResponse:
        """
        Primary chat API: add user message, call LLM, return response
        
        Args:
            user_message: The user's message (can be None for initial response)
            
        Returns:
            ChatResponse object with the LLM's response
        """
        # Add user message to history if provided
        if user_message is not None and user_message.strip():
            self.message_history.append(ChatMessage(
                role=Role.user, 
                content=user_message, 
                cot=None, 
                off_switch=False
            ))
        
        # Update agent's system prompt and call it (Agent handles formatting automatically)
        self.response_agent.update_system_prompt(self._build_system_prompt())
        response_obj: ChatResponse = self.response_agent.chat_with_history(self.message_history)
        
        # Add assistant response to history
        self.message_history.append(ChatMessage(
            role=Role.assistant,
            content=response_obj.response,
            cot=response_obj.hidden_thought_process,
            off_switch=response_obj.off_switch
        ))
        
        return response_obj
    
    def maintain(self) -> None:
        """
        Perform periodic maintenance
        NPC0 has no maintenance requirements
        """
        pass
    
    def inject_message(self, response: str, role: Role = Role.assistant, cot: Optional[str] = None, off_switch: bool = False) -> None:
        """
        Inject a message into the conversation history
        
        Args:
            response: The message content
            role: The role (user or assistant)
            cot: Chain of thought
            off_switch: Off switch flag
        """
        self.message_history.append(ChatMessage(
            role=role,
            content=response,
            cot=cot,
            off_switch=off_switch
        ))
    
    def get_all_memories(self) -> List[Entity]:
        """
        Get all memories (brain entities + injected memories as entities)
        
        Returns:
            List of Entity objects
        """
        memories = self.brain_entities.copy()
        # Convert injected memories to entities
        for memory in self.injected_memories:
            memories.append(Entity(
                key=memory, 
                content=memory, 
                tags=["injected_memory"], 
                id=int(Utilities.generate_hash_int64(memory))
            ))
        return memories
    
    def load_entities_from_template(self, template_path: Path) -> None:
        """
        Load entities from template file (copied from NPC1 abstraction)
        
        Args:
            template_path: Path to template file containing list of strings
        """
        if template_path.exists():
            entities_strs = io_utils.load_yaml_into_dataclass(template_path, List[str])
            self.brain_entities = [
                Entity(key=e, content=e, tags=["memories"], id=int(Utilities.generate_hash_int64(e))) 
                for e in entities_strs
            ]
    
    def clear_brain_memory(self) -> None:
        """
        Clear brain memory (entities and injected memories)
        """
        self.brain_entities = []
        self.injected_memories = []
    
    def update_system_prompt(self, new_prompt: str) -> None:
        """
        Update the base system prompt
        
        Args:
            new_prompt: The new base system prompt to use
        """
        self.base_system_prompt = new_prompt
    
    def get_message_history(self) -> List[ChatMessage]:
        """
        Get the current message history
        
        Returns:
            List of ChatMessage objects
        """
        return self.message_history.copy()
    
    def clear_message_history(self) -> None:
        """
        Clear the message history
        """
        self.message_history = []
    
    def inject_memories(self, memories: List[str]) -> None:
        """
        Inject a list of memory strings into the NPC's memory system
        For NPC0, these are stored as injected memories and added to system prompt
        
        Args:
            memories: List of memory strings to inject
        """
        self.injected_memories.extend(memories)
    
    def inject_conversation_history(self, history: List[Dict[str, str]]) -> None:
        """
        Inject conversation history where each dict has 'role' and 'content' keys
        
        Args:
            history: List of message dictionaries with 'role' and 'content' keys
        """
        for message in history:
            if 'role' in message and 'content' in message:
                role = Role.user if message['role'] == 'user' else Role.assistant
                self.message_history.append(ChatMessage(
                    role=role,
                    content=message['content'],
                    cot=None,
                    off_switch=False
                ))
