from enum import Enum

class Role(Enum):
    user = "user"
    assistant = "assistant"
    system = "system"

class AgentName(Enum):
    pat = "Pat"
    mock_user = "Mock User"

class Llm(Enum):
    gpt_3_5_turbo = "gpt-3.5-turbo"
    gpt_3_5_turbo_instruct = "gpt-3.5-turbo-instruct"
    gpt_4o_mini = "gpt-4o-mini"
    gpt_4o = "gpt-4o"
    o1 = "o1-preview"
    llama3 = "llama3"