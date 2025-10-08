from pathlib import Path
from typing import List, Protocol, Optional
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