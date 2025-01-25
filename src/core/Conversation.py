
import json
from typing import Dict, List
from src.utils import ChatBot, Utilities
from .Constants import Role, AgentName
from .Agent import Agent


class Conversation:

    message_history = []
    agents: Dict[AgentName, Agent] = {}

    def __init__(self):
        ...

    def add_agent(self, name: AgentName, role: Role, rules_file_name: str) -> Agent:
        # Ensure the file name is in the correct format (e.g. "pat_rules.json", no path, with json extension)
        if not rules_file_name.endswith(".json") or "/" in rules_file_name or "\\" in rules_file_name or rules_file_name.count(".") != 1:
            raise ValueError(f"Invalid file name: {rules_file_name}. Must be a json file name without a path (file should be present in the resources folder).")

        pat_rules_path = Utilities.get_path_from_project_root(f"src/resources/{rules_file_name}")
        pat_prompts: Dict[str, List[str]] = json.load(open(pat_rules_path))

        # Extract the rules and concatenate them into a single string
        pat_rules = pat_prompts["Ruleset 1"]
        pat_rules = "\n".join(pat_rules)

        # Create the agent
        agent = Agent(name, role, pat_rules)
        self.agents[name] = agent

    def call_agent(self, agent_name: AgentName):
        # Check if the role exists
        if agent_name not in self.agents:
            raise ValueError(f"Role {agent_name} not found in agents list.")
        
        agent = self.agents[agent_name]
        
        # Prepend the role rules to the message history
        self.message_history = [{"role": "system", "content": agent.rules}] + self.message_history

        # Call the llm agent with the context
        response = ChatBot.call_chat_agent(self.message_history)
        
        # Append the response to the message history
        self.message_history.append({"role": agent.role.value, "content": response})

        # Print the response
        print(f"{agent.name.value} as {agent.role.value}: {response}")

    def converse(self, first_agent: AgentName, second_agent: AgentName, iterations = 1):
        for i in range (iterations):
            # Call the first agent
            self.call_agent(first_agent)

            # Call the second agent
            self.call_agent(second_agent)