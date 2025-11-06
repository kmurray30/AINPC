
from typing import Dict, List
from src.utils import Utilities, Logger
from src.utils.Logger import Level
from src.core.Constants import AgentName
from src.conversation_eval.EvalAgent import EvalAgent
from src.core.ChatMessage import ChatMessageAgnostic
from src.core.ResponseTypes import ChatResponse
from src.npcs.npc_protocol import NPCProtocol

DEBUG_LEVEL = ""

class EvalConversation:

    # Store the message history with the agent name and the message content
    # This history cannot be passed directly to the chat agent, it needs to be formatted to replace the agent names with the roles
    message_history: List[ChatMessageAgnostic]

    agents: Dict[AgentName, EvalAgent]

    def __init__(self):
        self.message_history = []
        self.agents = {}

    def add_agent_simple(self, name: AgentName, agent_rules: List[str]) -> EvalAgent:
        agent = EvalAgent(name, "\n".join(agent_rules))
        self.agents[name] = agent

    def add_agent_with_npc_protocol(self, name: AgentName, agent_rules: List[str], npc_protocol: NPCProtocol) -> EvalAgent:
        """Add an agent backed by an NPC protocol"""
        agent = EvalAgent(name, "\n".join(agent_rules), npc_protocol)
        self.agents[name] = agent
        return agent

    def add_rule(self, agent_name: AgentName, rule: str):
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not found in agents list.")
        self.agents[agent_name].rules += "\n" + rule


    def call_agent(self, self_agent_name: AgentName, other_agent_name: AgentName, response_is_typed: bool, isPrinting = False):
        # Check if the agents have been added
        if self_agent_name not in self.agents:
            raise ValueError(f"Agent {self_agent_name} not found in agents list.")

        self_agent = self.agents[self_agent_name]
        
        # All agents are now NPC-backed
        # Get the last message from the other agent as user input
        last_message = None
        if self.message_history:
            # Find the most recent message from the other agent
            for msg in reversed(self.message_history):
                if msg.agent == other_agent_name:
                    last_message = msg.content
                    break
        
        # Call the NPC to generate response
        response_obj: ChatResponse = self_agent.chat_with_npc(last_message)
        response = response_obj.response

        # Print the response
        if isPrinting:
            if response_is_typed and hasattr(response_obj, 'hidden_thought_process'):
                Logger.log(f"{self_agent_name.value}:", Level.VERBOSE)
                Logger.log(f"\tExplanation: {response_obj.hidden_thought_process}", Level.VERBOSE)
                Logger.log(f"\tResponse: {response}", Level.VERBOSE)
            else:
                Logger.log(f"{self_agent_name.value}: {response}", Level.VERBOSE)
        
        # Add to conversation history
        self.message_history.append(ChatMessageAgnostic(self_agent_name, response))

    def converse(self, first_agent: AgentName, second_agent: AgentName, iterations = 1, response_is_typed = False, isPrinting = False):
        if DEBUG_LEVEL == "WARNING":
            Logger.log(f"Message history is of length {len(self.message_history)}")
        for i in range (iterations):
            # Call the first agent
            self.call_agent(first_agent, second_agent, response_is_typed, isPrinting = isPrinting)
            # Call the second agent
            self.call_agent(second_agent, first_agent, response_is_typed, isPrinting = isPrinting)

    def get_message_history_as_list(self, timestamped = False) -> List[ChatMessageAgnostic]:
        message_history_list = []
        timestamp = 1
        for message in self.message_history:
            timestamp_str = f"(Time {timestamp}) " if timestamped else ""
            message_history_list += [f"{timestamp_str}{message.agent.value}: {Utilities.decode(message.content)}"]
            timestamp += 1
        return message_history_list

    def get_message_history_as_string(self) -> str:
        message_history_str = ""
        for message in self.message_history:
            message_history_str += f"{message.agent.value}: {message.content}\n"
        return message_history_str

