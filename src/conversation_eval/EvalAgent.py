from typing import Optional
from src.core.Constants import AgentName, Role
from src.npcs.npc_protocol import NPCProtocol
from src.core.ResponseTypes import ChatResponse

class EvalAgent:
    name: AgentName
    rules: str
    npc_protocol: Optional[NPCProtocol] = None

    def __init__(self, name: AgentName, rules: str, npc_protocol: NPCProtocol = None):
        self.name = name
        self.rules = rules
        self.npc_protocol = npc_protocol

    def is_npc_backed(self) -> bool:
        """Check if this agent is backed by an NPC protocol"""
        return self.npc_protocol is not None

    def chat_with_npc(self, user_message: Optional[str]) -> ChatResponse:
        """Use NPC protocol to generate response"""
        if not self.is_npc_backed():
            raise ValueError(f"Agent {self.name} is not NPC-backed")
        return self.npc_protocol.chat(user_message)

    def inject_message_to_npc(self, message: str, role: Role = Role.user) -> None:
        """Inject a message into the NPC's conversation history"""
        if not self.is_npc_backed():
            raise ValueError(f"Agent {self.name} is not NPC-backed")
        self.npc_protocol.inject_message(message, role)

    def maintain_npc(self) -> None:
        """Call NPC maintenance if this is an NPC-backed agent"""
        if self.is_npc_backed():
            self.npc_protocol.maintain()

    def __str__(self):
        return f"{self.name.value}"