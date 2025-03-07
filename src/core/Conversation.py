
import json
from typing import Dict, List, Type, TypeVar
from src.utils import ChatBot, Utilities, Logger
from src.utils.Logger import Level
from .Constants import Role, AgentName, Constants
from .Agent import Agent
from .ChatMessage import ChatMessage
from .ChatResponse import ChatResponse

DEBUG_LEVEL = ""
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

    def add_agent(self, name: AgentName, rules_file_name: str, ruleset_name: str) -> Agent:
        agent_rules = Utilities.load_rules_from_file(rules_file_name, ruleset_name)

        # Create the agent
        self.add_agent(name, agent_rules)

    def add_agent(self, name: AgentName, agent_rules: List[str]) -> Agent:
        agent = Agent(name, "\n".join(agent_rules))
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
    
    def call_llm(self, message_history_for_llm: List[Dict[str, str]], response_type: Type[T] = None):
        if response_type is None:
            return ChatBot.call_chat_agent(message_history_for_llm)
        
        for _ in range(llm_formatting_retries):
            response_raw = ChatBot.call_chat_agent(message_history_for_llm)
            try:
                response_obj = Utilities.extract_response_obj(response_raw, response_type)
                return response_obj
            except Exception as e:
                Logger.log(f"Response from LLM agent is not in the correct format for {response_type.__name__}", Level.WARNING)
                Logger.log(f"Response: {response_raw}", Level.WARNING)
                Logger.log(f"Retrying...", Level.WARNING)

        raise ValueError(f"Failed to retrieve a valid response from the LLM agent after {llm_formatting_retries} retries.")

    def call_agent(self, self_agent_name: AgentName, other_agent_name: AgentName, response_is_typed: bool, isPrinting = False):
        # Check if the agents have been added
        if self_agent_name not in self.agents:
            raise ValueError(f"Agent {self_agent_name} not found in agents list.")

        message_history_for_llm = self.convert_message_history(self_agent_name, other_agent_name)
        
        # Prepend the role rules to the message history
        self_agent = self.agents[self_agent_name]
        message_history_for_llm = [{"role": Role.system.value, "content": self_agent.rules}] + message_history_for_llm

        if not response_is_typed:
            # Call the llm agent with the context, expecting a response of type str
            response: str = self.call_llm(message_history_for_llm)

            # Print the response
            if isPrinting:
                Logger.log(f"{self_agent_name.value}: {response}", Level.VERBOSE)
        else:
            # Call the llm agent with the context, expecting a response of type ChatResponse
            response_obj: ChatResponse = self.call_llm(message_history_for_llm, ChatResponse)
            response = response_obj.response

            # Print the explanation and the response
            if isPrinting:
                Logger.log(f"{self_agent_name.value}:", Level.VERBOSE)
                Logger.log(f"\tExplanation: {response_obj.explanation}", Level.VERBOSE)
                Logger.log(f"\tResponse: {response}", Level.VERBOSE)
        
        self.message_history.append(ChatMessage(self_agent_name, response))

    def converse(self, first_agent: AgentName, second_agent: AgentName, iterations = 1, response_is_typed = False, isPrinting = False):
        if DEBUG_LEVEL == "WARNING":
            Logger.log(f"Message history is of length {len(self.message_history)}")
        for i in range (iterations):
            # Call the first agent
            self.call_agent(first_agent, second_agent, response_is_typed, isPrinting = isPrinting)
            # Call the second agent
            self.call_agent(second_agent, first_agent, response_is_typed, isPrinting = isPrinting)

    def get_message_history_as_list(self) -> List[ChatMessage]:
        message_history_list = []
        for message in self.message_history:
            message_history_list += [f"{message.agent.value}: {Utilities.decode(message.content)}"]
        return message_history_list

    def get_message_history_as_string(self) -> str:
        message_history_str = ""
        for message in self.message_history:
            message_history_str += f"{message.agent.value}: {message.content}\n"
        return message_history_str

    def evaluate_conversation(self, pass_fail_condition) -> ChatResponse:
        conversation_message_history_str = self.get_message_history_as_string()

        evaluation_system_prompt = f"""You are a conversation evaluator. You will be given a conversation and a pass/fail condition. You will evaluate the conversation and return whether it passed or failed. If the conversation does not provide sufficient events to evaluate the condition, consider it undetermined. If the antecdent of the condition does not occur, consider it undetermined. If the antecedent of the condition occurs, but the consequent does not occur afterwards, consider it a fail. If the antecedent of the condition occurs and the consequent does occur afterwards, consider it a pass. The consequent must occur after the antecent for it to be considered a pass. If the antecent occurs only in the very last message of the conversation, consider it undetermined.
        Respond in a json with the following fields:
            explanation: A brief explanation on whether the condition was met
            response: '{Constants.pass_name}', '{Constants.fail_name}', or '{Constants.undetermined_name}'
        """

        evaluation_user_prompt = f"""Evaluate whether the following condition is met in the given conversation.
        Condition:
        {pass_fail_condition}

        Conversation:
        {conversation_message_history_str}
        """

        evaluation_message_history = [
            {"role": Role.system.value, "content": evaluation_system_prompt},
            {"role": Role.user.value, "content": evaluation_user_prompt},
        ]

        response = self.call_llm(evaluation_message_history)
        responseObj = Utilities.extract_response_obj(response, ChatResponse)

        # return the responseObj as a json string formatted with newlines
        return responseObj

