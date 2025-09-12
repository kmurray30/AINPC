from typing import Protocol, Optional
from src.core.Constants import Role


class NPCProtocol(Protocol):
    def chat(self, user_message: Optional[str]) -> str:
        ...
    
    def maintain(self) -> None:
        ...

    def inject_message(self, response: str, role: Role = Role.assistant, cot: Optional[str] = None, off_switch: bool = False) -> None:
        ...