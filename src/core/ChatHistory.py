from enum import Enum
import json
import os
from typing import Dict, List
from src.utils import Utilities, Logger
from src.utils.ChatBot import ChatBot
from src.utils.Logger import Level
from .Constants import Role
from .ChatMessage import ChatMessage
from .ResponseTypes import ChatResponse
from src.core.Constants import Llm, Constants as constants
from src.core import JsonUtils

class ChatHistory:
    chat_history: List[ChatMessage]
    previous_chat_loaded: bool

    def __init__(self, existing_load_path: str = None):
        if existing_load_path:
            try:
                self.load_message_history(existing_load_path)
                self.previous_chat_loaded = True
                Logger.log(f"Chat history loaded from {existing_load_path}", Level.INFO)
            except FileNotFoundError:
                Logger.log(f"File {existing_load_path} not found. Starting with an empty chat history.", Level.WARNING)
                self.chat_history = []
                self.previous_chat_loaded = False
            except Exception as e:
                Logger.log(f"Error loading chat session: {e}", Level.ERROR)
                raise e
        else:
            Logger.log("No existing chat history provided. Starting with an empty chat history.", Level.INFO)
            self.chat_history = []
            self.previous_chat_loaded = False

    def load_message_history(self, json_save_path: str) -> True:
        """Loads the message history from a json file."""
        try:
            with open(json_save_path, "r") as f:
                json_dict = json.load(f)  # Parse JSON into list of dicts
                message_history = Utilities.extract_obj_from_dict(json_dict, List[ChatMessage])  # Convert dicts to ChatMessage objects
                self.chat_history = message_history
                Logger.log(f"Loaded message history from {json_save_path}", Level.INFO)
                return True
        except FileNotFoundError:
            raise FileNotFoundError(f"File {json_save_path} not found. Please check the path.")
        except Exception as e:
            Logger.log(f"Error loading chat session: {e}", Level.ERROR)
            raise e
        
    def save_message_history(self, json_save_path: str) -> None:
        """Saves the message history to a file."""
        # Save self.message_history as a json file
        with open(json_save_path, "w") as f:
            message_history_json = [message.__dict__ for message in self.chat_history]
            json.dump(message_history_json, f, indent=4, cls=JsonUtils.EnumEncoder)

    def get_message_history_length(self) -> int:
        """Returns the length of the chat history."""
        return len(self.chat_history)

    def append_message(self, response: str, role: Role = Role.assistant, cot: str = None, off_switch: bool = False):
        """Injects a response into the message history, typically used for initial messages."""
        self.chat_history.append(ChatMessage(role=role, content=response, cot=cot, off_switch=off_switch))

    # Start index offset should be the number of messages from the end of the chat history to include.
    # End offset should be the number of messages from the end of the chat history to exclude.
    def get_chat_history_as_dict_list(self, include_hidden_responses: bool = True, start_index: int = None, end_offset: int = None) -> List[Dict[str, str]]:

        start_index = start_index if start_index is not None else 0
        end_index = len(self.chat_history) - end_offset - 1 if end_offset is not None else len(self.chat_history) - 1

        # Error checks
        if start_index < 0 or start_index > len(self.chat_history):
            raise ValueError("start_index is out of bounds for the chat history.")
        if end_index < 0 or end_index > len(self.chat_history):
            raise ValueError("end_index is out of bounds for the chat history.")
        if end_index < start_index:
            raise ValueError("end_index results in end before start.")
        if start_index == end_index:
            Logger.log("Warning: start_index and end_index are the same, resulting in an empty chat history.", Level.WARNING)
            return []

        # Trim the chat history based on the start and end indices
        chat_history_trimmed = self.chat_history[start_index:end_index + 1]

        message_history_dict_list = []
        for message in chat_history_trimmed:
            role = message.role
            if include_hidden_responses and message.cot is not None:
                # Format the content as a json string of the ChatResponse class (TODO make it agnostic to the class)
                content = "{"
                content += f'\t"hidden_thought_process": "{message.cot}", '
                content += f'\t"response": "{message.content}", '
                content += f'\t"off_switch": {str(message.off_switch).lower()}'
                content += "}"
            else:
                content = message.content # User responses will fall here
            message_history_dict_list.append({"role": role.name, "content": Utilities.decode(content)})
        return message_history_dict_list

    def get_chat_history_as_string(self, include_cot = False, start_index: int = None, end_offset: int = None) -> str:
        chat_history_str = ""
        chat_history_as_dict = self.get_chat_history_as_dict_list(include_cot, start_index=start_index, end_offset=end_offset)
        for message in chat_history_as_dict:
            chat_history_str += f"{message['role']}: {message['content']}\n"
        return chat_history_str


