from enum import Enum

class Role(Enum):
    user = "user"
    assistant = "assistant"
    system = "system"

class AgentName(Enum):
    pat = "Pat"
    mock_user = "Mock User"
