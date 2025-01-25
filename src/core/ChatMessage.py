
from .Constants import AgentName

class ChatMessage:
    agent: AgentName
    content: str

    def __init__(self, agent: AgentName, content: str):
        self.agent = agent
        self.content = content