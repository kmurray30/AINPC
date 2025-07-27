from typing import Optional
from .Constants import AgentName, Role
from dataclasses import dataclass

@dataclass
class ChatMessage:
    role: Role
    cot: Optional[str]
    content: Optional[str]
    off_switch: Optional[bool]

class ChatMessageAgnostic:
    agent: AgentName
    content: str

    def __init__(self, agent: AgentName, content: str):
        self.agent = agent
        self.content = content