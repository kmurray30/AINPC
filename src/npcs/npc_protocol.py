from pathlib import Path
from typing import List, Protocol, Optional, Dict
from src.core.Constants import Role
from src.core.schemas.CollectionSchemas import Entity
from src.core.ResponseTypes import ChatResponse


class NPCProtocol(Protocol):
    def chat(self, user_message: Optional[str]) -> ChatResponse:
        ...
    
    def maintain(self) -> None:
        ...

    def inject_message(self, response: str, role: Role = Role.assistant, cot: Optional[str] = None, off_switch: bool = False) -> None:
        ...

    def get_all_memories(self) -> List[Entity]:
        ...

    def load_entities_from_template(self, template_path: Path) -> None:
        ...

    def clear_brain_memory(self) -> None:
        ...
    
    def inject_memories(self, memories: List[str]) -> None:
        """Inject a list of memory strings into the NPC's memory system"""
        ...
    
    def inject_conversation_history(self, history: List[Dict[str, str]]) -> None:
        """Inject conversation history where each dict has 'role' and 'content' keys"""
        ...