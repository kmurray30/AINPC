
import json
from typing import Dict, List
from src.utils import ChatBot, Utilities
from .Constants import Role, AgentName
from .Agent import Agent
from .ChatMessage import ChatMessage


class Conversation:

    # Store the message history with the agent name and the message content
    # This history cannot be passed directly to the chat agent, it needs to be formatted to replace the agent names with the roles
    message_history: List[ChatMessage] = []

    agents: Dict[AgentName, Agent] = {}

    def __init__(self):
        ...

    def add_agent(self, name: AgentName, rules_file_name: str) -> Agent:
        # Ensure the file name is in the correct format (e.g. "pat_rules.json", no path, with json extension)
        if not rules_file_name.endswith(".json") or "/" in rules_file_name or "\\" in rules_file_name or rules_file_name.count(".") != 1:
            raise ValueError(f"Invalid file name: {rules_file_name}. Must be a json file name without a path (file should be present in the resources folder).")

        pat_rules_path = Utilities.get_path_from_project_root(f"src/resources/{rules_file_name}")
        pat_prompts: Dict[str, List[str]] = json.load(open(pat_rules_path))

        # Extract the rules and concatenate them into a single string
        pat_rules = pat_prompts["Ruleset 1"]
        pat_rules = "\n".join(pat_rules)

        # Create the agent
        agent = Agent(name, pat_rules)
        self.agents[name] = agent

    # Convert all chats from the self agent to the assistant role and all chats from the other agent to the user role so that the LLM can understand its role in the conversation
    def convert_message_history(self, self_agent_name: AgentName, other_agent_name: AgentName) -> List[Dict[str, str]]:
        message_history_with_roles = []
        for message in self.message_history:
            if message.agent == self_agent_name:
                message_history_with_roles.append({"role": Role.assistant.value, "content": message.content})
            elif message.agent == other_agent_name:
                message_history_with_roles.append({"role": Role.user.value, "content": message.content})
            elif message.agent is None:
                raise ValueError(f"Agent name is None for message: {message.content}")
            else:
                raise ValueError(f"Agent {message.agent} not found in agents list.")
        return message_history_with_roles

    def call_agent(self, self_agent_name: AgentName, other_agent_name: AgentName):
        # Check if the agents have been added
        if self_agent_name not in self.agents:
            raise ValueError(f"Agent {self_agent_name} not found in agents list.")
        if other_agent_name not in self.agents:
            raise ValueError(f"Agent {other_agent_name} not found in agents list.")

        message_history_for_llm = self.convert_message_history(self_agent_name, other_agent_name)
        
        # Prepend the role rules to the message history
        self_agent = self.agents[self_agent_name]
        message_history_for_llm = [{"role": "system", "content": self_agent.rules}] + message_history_for_llm

        # Call the llm agent with the context
        response = ChatBot.call_chat_agent(message_history_for_llm)
        
        # Append the response to the message history
        self.message_history.append(ChatMessage(self_agent_name, response))

        # Print the response
        print(f"{self_agent_name.value}: {response}")

    def converse(self, first_agent: AgentName, second_agent: AgentName, iterations = 1):
        for i in range (iterations):
            # Call the first agent
            self.call_agent(first_agent, second_agent)

            # Call the second agent
            self.call_agent(second_agent, first_agent)

    def get_message_history_as_string(self):
        message_history_str = ""
        for message in self.message_history:
            print(f"{message.agent.value}: {message.content}")
            message_history_str += f"{message.agent.value}: {message.content}\n"