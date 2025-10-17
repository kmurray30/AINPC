from typing import Optional
from src.core.Constants import AgentName
from src.npcs.npc_protocol import NPCProtocol

class EvalAgent:
    name: AgentName
    rules: str
    npc_protocol: Optional[NPCProtocol] = None

    def __init__(self, name: AgentName, rules: str, npc_protocol: NPCProtocol = None):
        self.name = name
        self.rules = rules
        self.npc_protocol = npc_protocol

    def __str__(self):
        return f"{self.name.value}"