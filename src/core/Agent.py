from src.core.Constants import Role, AgentName

class Agent:
    name: AgentName
    role: Role
    rules: str

    def __init__(self, name: AgentName, role: Role, rules: str):
        self.name = name
        self.role = role
        self.rules = rules

    def __str__(self):
        return f"{self.name.value}"