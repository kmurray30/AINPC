from pathlib import Path
from typing import List, Optional, Dict
from src.core.Constants import Role
from src.core.schemas.CollectionSchemas import Entity
from src.core.ResponseTypes import ChatResponse
from src.utils.ChatBot import ChatBot
from src.npcs.npc_protocol import NPCProtocol


class NPC0:
    """
    NPC0 - The simplest NPC implementation
    
    Features:
    - Stores message history in LLM format (List[Dict[str, str]])
    - Uses ChatBot.call_llm directly for responses
    - Minimal state management (no brain memory, no preprocessing)
    - Implements NPCProtocol interface
    """
    
    def __init__(self, system_prompt: str = "You are a helpful assistant."):
        """
        Initialize NPC0 with a system prompt
        
        Args:
            system_prompt: The system prompt to use for this NPC
        """
        self.system_prompt = system_prompt
        self.message_history: List[Dict[str, str]] = []
    
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
            self.message_history.append({"role": Role.user.value, "content": user_message})
        
        # Build the full message history for LLM with system prompt
        message_history_for_llm = [{"role": Role.system.value, "content": self.system_prompt}] + self.message_history
        
        # Call LLM with typed response
        response_obj: ChatResponse = ChatBot.call_llm(message_history_for_llm, ChatResponse)
        
        # Add assistant response to history
        self.message_history.append({"role": Role.assistant.value, "content": response_obj.response})
        
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
            cot: Chain of thought (ignored in NPC0)
            off_switch: Off switch flag (ignored in NPC0)
        """
        self.message_history.append({"role": role.value, "content": response})
    
    def get_all_memories(self) -> List[Entity]:
        """
        Get all memories (NPC0 has no memory system)
        
        Returns:
            Empty list
        """
        return []
    
    def load_entities_from_template(self, template_path: Path) -> None:
        """
        Load entities from template (NPC0 has no memory system)
        
        Args:
            template_path: Path to template file (ignored)
        """
        pass
    
    def clear_brain_memory(self) -> None:
        """
        Clear brain memory (NPC0 has no memory system)
        """
        pass
    
    def update_system_prompt(self, new_prompt: str) -> None:
        """
        Update the system prompt
        
        Args:
            new_prompt: The new system prompt to use
        """
        self.system_prompt = new_prompt
    
    def get_message_history(self) -> List[Dict[str, str]]:
        """
        Get the current message history
        
        Returns:
            List of message dictionaries in LLM format
        """
        return self.message_history.copy()
    
    def clear_message_history(self) -> None:
        """
        Clear the message history
        """
        self.message_history = []
