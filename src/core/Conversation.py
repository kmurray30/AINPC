
import json
from typing import Dict, List, Type, TypeVar
from src.utils import ChatBot, Utilities
from .Constants import Role, AgentName
from .Agent import Agent
from .ChatMessage import ChatMessage
from .ChatResponse import ChatResponse

DEBUG_LEVEL = "WARNING"
llm_formatting_retries = 3
T = TypeVar('T')

class Conversation:

    # Store the message history with the agent name and the message content
    # This history cannot be passed directly to the chat agent, it needs to be formatted to replace the agent names with the roles
    message_history: List[ChatMessage]

    agents: Dict[AgentName, Agent]

    def __init__(self):
        self.message_history = []
        self.agents = {}

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

    def add_rule(self, agent_name: AgentName, rule: str):
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not found in agents list.")
        self.agents[agent_name].rules += "\n" + rule

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
    
    def extract_response_obj(self, response_raw: str, response_type: Type[T]) -> T:
        # Debug check if the response starts with ```json or not
        if not response_raw.startswith("```json") and DEBUG_LEVEL == "DEBUG":
            print(f"debug: Response does NOT start with ```json")
        elif DEBUG_LEVEL == "DEBUG":
            print(f"debug: Response DOES start with ```json")

        # Trim everything before the first '{' and after the last '}'
        response_trimmed = response_raw[response_raw.find("{"):response_raw.rfind("}")+1]
        json_response = json.loads(response_trimmed)
        # Try to convert the response to the specified object
        response_obj = response_type(**json_response)
        return response_obj
    
    def call_llm(self, message_history_for_llm: List[Dict[str, str]], response_type: Type[T] = None):
        if response_type is None:
            return ChatBot.call_chat_agent(message_history_for_llm)
        
        for _ in range(llm_formatting_retries):
            response_raw = ChatBot.call_chat_agent(message_history_for_llm)
            try:
                response_obj = self.extract_response_obj(response_raw, response_type)
                return response_obj
            except Exception as e:
                print(f"Response from LLM agent is not in the correct format for {response_type.__name__}")
                print(f"Response: {response_raw}")
                print(f"Retrying...")

        raise ValueError(f"Failed to retrieve a valid response from the LLM agent after {llm_formatting_retries} retries.")

    def call_agent(self, self_agent_name: AgentName, other_agent_name: AgentName, response_is_typed: bool):
        # Check if the agents have been added
        if self_agent_name not in self.agents:
            raise ValueError(f"Agent {self_agent_name} not found in agents list.")
        if other_agent_name not in self.agents:
            raise ValueError(f"Agent {other_agent_name} not found in agents list.")

        message_history_for_llm = self.convert_message_history(self_agent_name, other_agent_name)
        
        # Prepend the role rules to the message history
        self_agent = self.agents[self_agent_name]
        message_history_for_llm = [{"role": "system", "content": self_agent.rules}] + message_history_for_llm

        if not response_is_typed:
            # Call the llm agent with the context, expecting a response of type str
            response: str = self.call_llm(message_history_for_llm)

            # Print the response
            print(f"{self_agent_name.value}: {response}")
        else:
            # Call the llm agent with the context, expecting a response of type ChatResponse
            response_obj: ChatResponse = self.call_llm(message_history_for_llm, ChatResponse)
            response = response_obj.response

            # Print the explanation and the response
            print(f"{self_agent_name.value}:")
            print(f"\tExplanation: {response_obj.explanation}")
            print(f"\tResponse: {response}")
        
        self.message_history.append(ChatMessage(self_agent_name, response))

    def converse(self, first_agent: AgentName, second_agent: AgentName, iterations = 1, response_is_typed = False):
        if DEBUG_LEVEL == "WARNING":
            print(f"Message history is of length {len(self.message_history)}")
        for i in range (iterations):
            # Call the first agent
            self.call_agent(first_agent, second_agent, response_is_typed)

            # Call the second agent
            self.call_agent(second_agent, first_agent, response_is_typed)

    def get_message_history_as_string(self):
        message_history_str = ""
        for message in self.message_history:
            print(f"{message.agent.value}: {message.content}")
            message_history_str += f"{message.agent.value}: {message.content}\n"