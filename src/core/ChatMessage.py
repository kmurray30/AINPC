
from .Constants import AgentName, Role

class ChatMessage:
    role: Role
    cot: str
    content: str
    off_switch: bool

    def __init__(self, role: Role, cot: str = None, content: str = None, off_switch: bool = False):
        self.role = role
        self.cot = cot
        self.content = content
        self.off_switch = off_switch

class ChatMessageAgnostic:
    agent: AgentName
    content: str

    def __init__(self, agent: AgentName, content: str):
        self.agent = agent
        self.content = content