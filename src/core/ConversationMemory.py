from dataclasses import asdict, dataclass
import json
from typing import Dict, List, Optional
from src.core.schemas.Schemas import GameSettings
from src.utils import Utilities, Logger, llm_utils
from src.utils.ChatBot import ChatBot
from src.utils.Logger import Level
from .Constants import Role
from .ChatMessage import ChatMessage
from .ResponseTypes import ChatResponse, ChatSummary
from src.core import proj_settings

@dataclass
class ConversationMemoryState:
    chat_memory: List[ChatMessage]
    conversation_summary: Optional[ChatSummary]

class ConversationMemory:
    chat_memory: List[ChatMessage]
    conversation_summary: Optional[ChatSummary]

    summarization_prompt: str
    system_prompt_summary_suffix: str

    game_settings: GameSettings

    @classmethod
    def new_game(cls) -> 'ConversationMemory':
        """Creates a new instance of ConversationMemory for a new game."""
        return cls(None)

    @classmethod
    def from_state(cls, state: ConversationMemoryState) -> 'ConversationMemory':
        """Creates an instance of ConversationMemory from a given state."""
        return cls(state)

    def get_chat_memory_length(self) -> int:
        """Returns the length of the chat memory."""
        return len(self.chat_memory)

    def __init__(self, state: ConversationMemoryState):
        if state is None:
            self.chat_memory = []
            self.conversation_summary = None
        else:
            self.chat_memory = state.chat_memory
            self.conversation_summary = state.conversation_summary

        self.game_settings = proj_settings.get_settings().game_settings
        self.system_prompt_summary_suffix = llm_utils.get_formatting_suffix(ChatSummary)

    def get_state(self) -> ConversationMemoryState:
        """Returns the current state of the conversation memory."""
        return ConversationMemoryState(
            chat_memory=self.chat_memory,
            conversation_summary=self.conversation_summary
        )

    def maintain(self):
        """Maintains the conversation memory, including consolidation via summarization if necessary."""
        current_chat_length = self.get_chat_memory_length()
        if current_chat_length > self.game_settings.max_convo_mem_length:
            Logger.log(f"Chat history length exceeded {self.game_settings.max_convo_mem_length}. Summarizing chat history.", Level.INFO)
            num_last_messages_to_retain = self.game_settings.num_last_messages_to_retain_when_summarizing
            self.summarize_message_history(include_cot=True, num_last_messages_to_retain=num_last_messages_to_retain, enable_printing=True)

    def append_chat(self, response: str, role: Role = Role.assistant, cot: str = None, off_switch: bool = False):
        """Injects a response into the message history, typically used for initial messages."""
        self.chat_memory.append(ChatMessage(role=role, content=response, cot=cot, off_switch=off_switch))

    def get_chat_memory_as_string(self, include_cot = False) -> str:
        chat_history_str = ""
        chat_history_as_dict = llm_utils.convert_message_history_to_llm_format(self.chat_memory, include_cot)
        for message in chat_history_as_dict:
            chat_history_str += f"{message['role']}: {message['content']}\n"
        return chat_history_str
    
    def get_chat_summary_as_string(self) -> str:
        """Returns the conversation summary as a formatted string."""
        if not self.conversation_summary:
            return "(No summary available.)"
        return json.dumps(asdict(self.conversation_summary), indent=4)

    def get_message_history_for_llm_summarization(self, include_cot: bool = False, num_last_messages_to_exclude: int = 0) -> List[Dict[str, str]]:
        # Initialize the message history for summarization
        summarization_message_history = []
        
        # First add the system prompt
        # Start with the overview
        system_prompt = "You are a conversation summarizer."
        # Add the formatting prompt
        system_prompt += "\n\n" + self.system_prompt_summary_suffix
        summarization_message_history.append({"role": Role.system.value, "content": system_prompt})

        # Next, start constructing the user message
        user_message_content = ""
        # First add the instructions
        instructions = self.game_settings.summarization_prompt
        user_message_content += "Instructions:\n" + instructions + "\n\n"
        # Second, add the previous conversation summary if it exists
        if self.conversation_summary:
            user_message_content += "Previous Conversation Summary:\n" + str(self.conversation_summary) + "\n\n"
        # Third add the chat history as a string
        chat_history_str = self.get_chat_memory_as_string(include_cot)
        user_message_content += "Chat History:\n" + chat_history_str + "\n\n\n"

        # Finally, add this user message to the message history
        summarization_message_history.append({"role": Role.user.value, "content": user_message_content})
        return summarization_message_history

    def summarize_message_history(self, include_cot, num_last_messages_to_retain = 0, enable_printing = False) -> str:
        """Summarizes the conversation history and updates the system prompt with the summary."""
        summarization_prompt_and_message_history = self.get_message_history_for_llm_summarization(include_cot, num_last_messages_to_exclude=num_last_messages_to_retain)

        print("Summarization prompt:\n")
        for message in summarization_prompt_and_message_history:
            print(f"{message['role']}: {message['content']}")

        # Call the llm agent with the context, expecting an untyped response
        summary: ChatSummary = ChatBot.call_llm(summarization_prompt_and_message_history, ChatSummary)

        if enable_printing:
            Logger.log(f"Summary: {summary}", Level.VERBOSE)

        # Update the conversation summary and trim the chat memory
        self.conversation_summary = summary
        self.chat_memory = self.chat_memory[-num_last_messages_to_retain:] if num_last_messages_to_retain > 0 else self.chat_memory

        return summary

