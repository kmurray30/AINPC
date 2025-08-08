from dataclasses import asdict
import json
import os
from typing import Any, Dict, List, Type, TypeVar
from src.utils import Logger
from src.utils.ChatBot import ChatBot
from src.utils.Logger import Level
from .Constants import Role
from .ResponseTypes import ChatResponse, ChatSummary
from src.core.Constants import Llm, Constants as constants
from src.core.ChatHistory import ChatHistory
from src.utils import Utilities
from src.core import JsonUtils

DEBUG_LEVEL = ""
T = TypeVar('T')

class ChatSession:

    # Store the message history with the agent name and the message content
    # This history cannot be passed directly to the chat agent, it needs to be formatted to replace the agent names with the roles
    chat_history: ChatHistory
    chat_history_start_index: int
    system_prompt_context: str
    system_prompt_conversation_summary: Dict[str, str]
    system_prompt_chat_suffix: str
    system_prompt_summary_suffix: str
    user_prompt_wrapper: str
    chat_history_save_path: str
    metadata_save_path: str

    previous_session_found: bool = False  # Flag to indicate if a previous session was found

    chat_bot: ChatBot

    def __init__(self, system_prompt_context: str, chat_history_save_path: str, metadata_save_path: str, summarization_prompt: str, user_prompt_wrapper: str = None, model: Llm = Llm.gpt_4o_mini, load_old_session_flag: bool = False):

        self.chat_history_save_path = chat_history_save_path
        self.metadata_save_path = metadata_save_path
        self.summarization_prompt = summarization_prompt
        self.system_prompt_context = system_prompt_context
        self.system_prompt_chat_suffix = self._get_system_prompt_formatting_suffix(ChatResponse)
        self.system_prompt_summary_suffix = self._get_system_prompt_formatting_suffix(ChatSummary)
        self.user_prompt_wrapper = user_prompt_wrapper

        # Initialize the chat bot with the specified model
        self.chat_bot = ChatBot(model=model)

        # Load or initialize the metadata (conversation summary and chat window)
        prior_save_metadata = self._load_metadata(metadata_save_path)
        if prior_save_metadata:
            self.chat_history_start_index = prior_save_metadata.get("chat_history_window_start", 0)
            self.system_prompt_conversation_summary = prior_save_metadata.get("system_prompt_conversation_summary", "")
            self.previous_session_found = True
        else:
            self.chat_history_start_index = 0
            self.system_prompt_conversation_summary = ""
            self.previous_session_found = False

        # Load or initialize the chat history
        self.chat_history = ChatHistory(existing_load_path=chat_history_save_path if load_old_session_flag else None)
        if self.previous_session_found != self.chat_history.previous_chat_loaded:
            raise ValueError(f"Inconsistent session state: either the chat history or metadata was loaded, but not both. Please ensure the integrity of your session files at {self.save_path_prefix}{self.save_name}.")

    def _load_metadata(self, metadata_save_path: str) -> Dict[str, Any]:
        """Loads metadata from a JSON file."""
        try:
            with open(metadata_save_path, "r") as f:
                metadata = json.load(f)
            return metadata
        except FileNotFoundError:
            Logger.log(f"Metadata file {metadata_save_path} not found. Starting with empty metadata.", Level.WARNING)
            return {}
        except Exception as e:
            Logger.log(f"Error loading metadata: {e}", Level.ERROR)
            raise e

    def _save_metadata(self, metadata: Dict[str, Any], metadata_save_path: str) -> None:
        """Saves metadata to a JSON file."""
        try:
            with open(metadata_save_path, "w") as f:
                json.dump(metadata, f, indent=4, cls=JsonUtils.EnumEncoder)
        except Exception as e:
            Logger.log(f"Error saving metadata: {e}", Level.ERROR)
            raise e

    def _get_system_prompt_formatting_suffix(self, response_type: Type[T]) -> str:
        """Returns the prompt suffix that specifies the formatting of the LLM response."""
        return Utilities.get_system_prompt_formatting_suffix(response_type)
    
    def _get_full_system_prompt_for_chat(self) -> str:
        """Returns the full system prompt, including context, conversation summary, and response formatting."""
        complete_system_prompt = f"Context:\n{self.system_prompt_context}\n\n"
        if self.system_prompt_conversation_summary:
            complete_system_prompt += f"Conversation summary:\n{self.system_prompt_conversation_summary}\n\n"
        complete_system_prompt += f"Response formatting:\n{self.system_prompt_chat_suffix}\n\n"
        return complete_system_prompt
    
    def _prepend_system_prompt(self, chat_history_formatted: List[Dict[str, str]], system_prompt: str) -> List[Dict[str, str]]:
        """Prepends the system prompt to the chat history formatted for LLM."""
        return [{"role": Role.system.value, "content": system_prompt}] + chat_history_formatted
    
    def get_full_chat_history_length(self) -> int:
        """Returns the length of the chat history."""
        return self.chat_history.get_message_history_length()
    
    def get_current_chat_history_length(self) -> int:
        """Returns the length of the chat history from the start index."""
        return self.chat_history.get_message_history_length() - self.chat_history_start_index

    def get_whether_previous_session_found(self) -> bool:
        """Returns whether a previous session was found."""
        return self.previous_session_found

    def inject_message(self, response: str, role: Role = Role.assistant, off_switch: bool = False):
        """Injects a response into the message history, typically used for initial messages."""
        self.chat_history.append_message(response, role=role, off_switch=off_switch)

    def update_user_prompt_wrapper(self, user_prompt_wrapper: str):
        self.user_prompt_wrapper = user_prompt_wrapper

    # Call the LLM agent with the current message history and return a response.
    # If user_message is provided, it will be used to update the user prompt in the message history.
    # Responses must be structured as a ChatResponse object using prompt engineering
    def call_llm_for_chat(self, user_message: str = None, enable_printing: bool = False):
        # Add the latest user prompt to the chat history. If none, skip this step
        if user_message is not None:
            self.chat_history.append_message(user_message, role=Role.user, off_switch=False)

        # Get the chat history formatted for LLM
        chat_history_dict = self.chat_history.get_chat_history_as_dict_list(include_hidden_responses=True, start_index=self.chat_history_start_index)

        # Prepend the system prompt to the chat history
        full_message_history_dict = self._prepend_system_prompt(chat_history_dict, self._get_full_system_prompt_for_chat())

        # Wrap the latest user message if requested
        if user_message is not None and self.user_prompt_wrapper:
            user_prompt_wrapped = self.user_prompt_wrapper.replace(constants.user_message_placeholder, user_message)
            full_message_history_dict[-1]["content"] = user_prompt_wrapped

        # Call the llm agent with the context, expecting a response of type ChatResponse
        response_obj: ChatResponse = self.chat_bot.call_llm(full_message_history_dict, ChatResponse)
        cot = response_obj.hidden_thought_process
        response = response_obj.response
        off_switch = response_obj.off_switch

        # Print the explanation and the response
        if enable_printing:
            Logger.log(f"Assistant:", Level.VERBOSE)
            Logger.log(f"\tHidden Thought Process: {response_obj.hidden_thought_process}", Level.VERBOSE)
            Logger.log(f"\tResponse: {response}", Level.VERBOSE)
            Logger.log(f"\tOff Switch: {off_switch}", Level.VERBOSE)

        self.chat_history.append_message(response, role=Role.assistant, off_switch=off_switch, cot=cot)

        return (response, off_switch)
        
    def get_message_history_for_llm_summarization(self, include_cot: bool = False, num_last_messages_to_exclude: int = 0) -> List[Dict[str, str]]:
        # Initialize the message history for summarization
        summarization_message_history = []
        
        # First add the system prompt
        system_prompt = "You are a conversation summarizer."
        system_prompt += "\n\n" + self.system_prompt_summary_suffix
        summarization_message_history.append({"role": Role.system.value, "content": system_prompt})

        # Next, start constructing the user message
        user_message_content = ""
        # First add the instructions
        instructions = self.summarization_prompt
        user_message_content += "Instructions:\n" + instructions + "\n\n"
        # Second, add the previous conversation summary if it exists
        if self.system_prompt_conversation_summary:
            user_message_content += "Previous Conversation Summary:\n" + self.system_prompt_conversation_summary + "\n\n"
        # Third add the chat history as a string
        chat_history_str = self.chat_history.get_chat_history_as_string(include_cot, start_index=self.chat_history_start_index, end_offset=num_last_messages_to_exclude)
        user_message_content += "Chat History:\n" + chat_history_str + "\n\n\n"

        # Finally, add the user message
        summarization_message_history.append({"role": Role.user.value, "content": user_message_content})
        return summarization_message_history

    def summarize_message_history(self, include_cot, num_last_messages_to_retain = 0, enable_printing = False) -> str:
        """Summarizes the conversation history and updates the system prompt with the summary."""
        summarization_prompt_and_message_history = self.get_message_history_for_llm_summarization(include_cot, num_last_messages_to_exclude=num_last_messages_to_retain)

        print("Summarization prompt:\n")
        for message in summarization_prompt_and_message_history:
            print(f"{message['role']}: {message['content']}")

        # Call the llm agent with the context, expecting an untyped response
        responseObj: ChatSummary = self.chat_bot.call_llm(summarization_prompt_and_message_history, ChatSummary)
        # summary = f"conversation_overview: {responseObj.conversation_overview}\n"
        # summary += f"hidden_thought_processes: {responseObj.hidden_thought_processes}\n"
        # summary += f"chronology: {', '.join(responseObj.chronology)}\n"
        # summary += f"most_recent: {responseObj.most_recent}\n"
        summary: Dict[str, str] = json.dumps(asdict(responseObj), indent=4)

        if enable_printing:
            Logger.log(f"Summary: {summary}", Level.VERBOSE)

        self.system_prompt_conversation_summary = summary

        # Update the start index for the chat history window
        self.chat_history_start_index = self.chat_history.get_message_history_length() - num_last_messages_to_retain 
        return summary

    def save_session(self) -> None:
        """Saves the message history and metadata to files."""

        # Ensure the directories exist
        os.makedirs(os.path.dirname(self.chat_history_save_path), exist_ok=True)

        # Create backup files in case the save fails
        backup_chat_history_path = self.chat_history_save_path + ".bak"
        backup_metadata_path = self.metadata_save_path + ".bak"
        if os.path.exists(self.chat_history_save_path):
            os.replace(self.chat_history_save_path, backup_chat_history_path)
        if os.path.exists(self.metadata_save_path):
            os.replace(self.metadata_save_path, backup_metadata_path)

        try:
            self.chat_history.save_message_history(self.chat_history_save_path)
            self._save_metadata({
                "system_prompt_conversation_summary": self.system_prompt_conversation_summary,
                "chat_history_window_start": self.chat_history_start_index
            }, self.metadata_save_path)
            # Remove backup files after successful save
            if os.path.exists(backup_chat_history_path):
                os.remove(backup_chat_history_path)
            if os.path.exists(backup_metadata_path):
                os.remove(backup_metadata_path)

            Logger.log(f"Session saved successfully to {self.chat_history_save_path} and {self.metadata_save_path}", Level.INFO)
        except Exception as e:
            Logger.log(f"Error saving session: {e}", Level.ERROR)
            # Restore from backup if save fails
            if os.path.exists(backup_chat_history_path):
                os.replace(backup_chat_history_path, self.chat_history_save_path)
            if os.path.exists(backup_metadata_path):
                os.replace(backup_metadata_path, self.metadata_save_path)
            raise e