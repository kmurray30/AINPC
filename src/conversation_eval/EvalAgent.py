from typing import Optional
from src.core.Constants import AgentName, Role
from src.npcs.npc_protocol import NPCProtocol
from src.core.ResponseTypes import ChatResponse
from src.npcs.npc0.npc0 import NPC0

class EvalAgent:
    name: AgentName
    rules: str
    npc_protocol: NPCProtocol

    def __init__(self, name: AgentName, rules: str, npc_protocol: Optional[NPCProtocol] = None):
        self.name = name
        self.rules = rules
        # If no NPC protocol provided, create a simple NPC0 with the rules as system prompt
        if npc_protocol is None:
            self.npc_protocol = NPC0(system_prompt=rules)
        else:
            self.npc_protocol = npc_protocol


    def chat_with_npc(self, user_message: Optional[str]) -> ChatResponse:
        """Use NPC protocol to generate response"""
        return self.npc_protocol.chat(user_message)

    def inject_message_to_npc(self, message: str, role: Role = Role.user) -> None:
        """Inject a message into the NPC's conversation history"""
        self.npc_protocol.inject_message(message, role)

    def maintain_npc(self) -> None:
        """Call NPC maintenance"""
        self.npc_protocol.maintain()

    def __str__(self):
        return f"{self.name.value}"