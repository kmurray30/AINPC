from src.core.Constants import Role, AgentName

class Agent:
    name: AgentName
    rules: str

    def __init__(self, name: AgentName, rules: str):
        self.name = name
        self.rules = rules

    def __str__(self):
        return f"{self.name.value}"