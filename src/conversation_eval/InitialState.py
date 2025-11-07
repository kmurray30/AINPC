from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
from src.utils import io_utils
from src.npcs.npc_protocol import NPCProtocol


@dataclass
class InitialState:
    """Schema for test initial state injection"""
    context: Optional[str] = None  # Additional system prompt context
    memories: List[str] = field(default_factory=list)  # Memory strings to inject
    conversation_history: List[Dict[str, str]] = field(default_factory=list)  # Chat history to inject


class InitialStateLoader:
    """Utility class for loading and applying initial state to NPCs"""
    
    @staticmethod
    def load_from_yaml(yaml_path: Path) -> InitialState:
        """
        Load initial state from YAML file
        
        Args:
            yaml_path: Path to YAML file containing initial state
            
        Returns:
            InitialState object
        """
        if not yaml_path.exists():
            return InitialState()
        
        return io_utils.load_yaml_into_dataclass(yaml_path, InitialState)
    
    @staticmethod
    def apply_to_npc(npc: NPCProtocol, initial_state: InitialState) -> None:
        """
        Apply initial state to an NPC
        
        Args:
            npc: NPC instance implementing NPCProtocol
            initial_state: InitialState to apply
        """
        # Inject memories if provided
        if initial_state.memories:
            npc.inject_memories(initial_state.memories)
        
        # Inject conversation history if provided
        if initial_state.conversation_history:
            npc.inject_conversation_history(initial_state.conversation_history)
        
        # Handle context injection (NPC-specific implementation)
        if initial_state.context:
            # For NPCs that support system prompt updates
            if hasattr(npc, 'update_system_prompt'):
                # Get current system prompt and append context
                if hasattr(npc, 'base_system_prompt'):
                    current_prompt = npc.base_system_prompt
                elif hasattr(npc, 'template') and hasattr(npc.template, 'system_prompt'):
                    current_prompt = npc.template.system_prompt
                else:
                    current_prompt = "You are a helpful assistant."
                
                enhanced_prompt = f"{current_prompt}\n\nAdditional context: {initial_state.context}"
                npc.update_system_prompt(enhanced_prompt)
    
    @staticmethod
    def load_and_apply(yaml_path: Path, npc: NPCProtocol) -> InitialState:
        """
        Load initial state from YAML and apply it to NPC
        
        Args:
            yaml_path: Path to YAML file containing initial state
            npc: NPC instance to apply state to
            
        Returns:
            The loaded InitialState object
        """
        initial_state = InitialStateLoader.load_from_yaml(yaml_path)
        InitialStateLoader.apply_to_npc(npc, initial_state)
        return initial_state
