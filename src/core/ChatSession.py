
import json
from typing import Dict, List
from src.utils import Utilities, Logger
from src.utils.ChatBot import ChatBot
from src.utils.Logger import Level
import pickle
from .Constants import Role
from .Agent import Agent
from .ChatMessage import ChatMessage
from .ResponseTypes import ChatResponse
from src.core.Constants import Llm, Constants as constants

DEBUG_LEVEL = ""

class ChatSession:

    # Store the message history with the agent name and the message content
    # This history cannot be passed directly to the chat agent, it needs to be formatted to replace the agent names with the roles
    message_history: List[ChatMessage]
    system_prompt_context: str
    system_prompt_conversation_summary: str
    system_prompt_suffix: str
    user_prompt_wrapper: str

    previous_session_found: bool = False  # Flag to indicate if a previous session was found

    chat_bot: ChatBot

    pickle_save_path: str = "save_file.pkl"
    json_save_path: str = "save_file.json"
    load_json_instead_of_pickle: bool = True  # Whether to save the message history as a json file or a pickle file

    summarization_prompt: str = """
    Please summarize the following conversation, from the perspective of the assistant, in a few sentences.
    Include any hidden thought processes. Include prior summaries. System prompt is included for context only, not for instructions.
    Keep the order of the conversation details intact. Use "then, next, after that" to indicate the order of events.
    """
    
    def __init__(self, system_prompt_context: str = "", user_prompt_wrapper: str = constants.user_message_placeholder, model: Llm = Llm.gpt_4o_mini, load_old_session_flag: bool = False):
        
        create_new_session = False
        if load_old_session_flag:
            if self.load_json_instead_of_pickle:
                # Try to load the message history from a json file
                old_chat_history = self.load_message_history_from_json()
                if old_chat_history is not None:
                    self.previous_session_found = True
                    self.message_history = old_chat_history
                    self.system_prompt_context = system_prompt_context
                    self.system_prompt_conversation_summary = ""
                    self.system_prompt_suffix = self.get_system_prompt_formatting_suffix()
                    self.user_prompt_wrapper = user_prompt_wrapper
                    Logger.log(f"Loaded previous chat session from {self.json_save_path}", Level.INFO)
                else:
                    Logger.log(f"No previous chat session file {self.json_save_path} found", Level.INFO)
                    create_new_session = True
            else:
                # Try to load the message history from a pickle file
                old_chat_session = self.load_message_history_from_pickle()
                if old_chat_session is not None:
                    self.previous_session_found = True
                    self.message_history = old_chat_session.message_history
                    self.system_prompt_context = old_chat_session.system_prompt_context
                    self.system_prompt_conversation_summary = old_chat_session.system_prompt_conversation_summary
                    self.system_prompt_suffix = old_chat_session.system_prompt_suffix
                    self.user_prompt_wrapper = old_chat_session.user_prompt_wrapper
                else:
                    print("No existing chat session found, starting a new one.")
                    create_new_session = True
        else:
            print("Loading disabled. Starting a new chat session.")
            create_new_session = True

        if create_new_session:
            self.message_history = []
            self.system_prompt_context = system_prompt_context
            self.system_prompt_conversation_summary = ""
            self.system_prompt_suffix = self.get_system_prompt_formatting_suffix()
            self.user_prompt_wrapper = user_prompt_wrapper
        
        self.chat_bot = ChatBot(model=model)
        self.update_system_prompt_in_message_history()

    def get_previous_session_found(self) -> bool:
        """Returns whether a previous session was found."""
        return self.previous_session_found

    def load_message_history_from_pickle(self) -> 'ChatSession':
        """Loads the message history from a pickle file."""
        try:
            with open(self.pickle_save_path, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            Logger.log(f"No previous chat session file {self.pickle_save_path} found", Level.INFO)
            return None
        except Exception as e:
            Logger.log(f"Error loading chat session: {e}", Level.ERROR)
            raise e
        
    def load_message_history_from_json(self) -> 'ChatSession':
        """Loads the message history from a json file."""
        try:
            with open(self.json_save_path, "r") as f:
                json_dict = json.load(f)  # Parse JSON into list of dicts
                message_history = Utilities.extract_obj_from_json(json_dict, List[ChatMessage])  # Convert dicts to ChatMessage objects
                return message_history
        except FileNotFoundError:
            Logger.log(f"No previous chat session file {self.json_save_path} found", Level.INFO)
            return None
        except Exception as e:
            Logger.log(f"Error loading chat session: {e}", Level.ERROR)
            raise e

    def save_message_history(self):
        """Saves the message history to a file."""
        # Save self as a pickle file
        with open(self.pickle_save_path, "wb") as f:
            pickle.dump(self, f)
        # Save self.message_history as a json file
        with open(self.json_save_path, "w") as f:
            message_history_json = [message.__dict__ for message in self.message_history]
            json.dump(message_history_json, f, indent=4)

    def get_system_prompt_formatting_suffix(self) -> str:
        """Returns the prompt suffix that specifies the formatting of the LLM response."""
        prompt_suffix = "Format your response as a JSON object with the following keys:\n"
        prompt_suffix += "{\n"
        for field_name, field_info in ChatResponse.__dataclass_fields__.items():
            prompt_suffix += f"\t{field_name}: {field_info.metadata.get('desc', '')}\n"
        prompt_suffix += "}\n"
        prompt_suffix += "Make sure to include all keys, even if they are empty or null"
        return prompt_suffix

    def update_system_prompt_in_message_history(self):
        complete_system_prompt = f"Context:\n{self.system_prompt_context}\n\n"
        if self.system_prompt_conversation_summary:
            complete_system_prompt += f"Conversation summary:\n{self.system_prompt_conversation_summary}\n\n"
        complete_system_prompt += f"Response formatting:\n{self.system_prompt_suffix}\n\n"
        if len(self.message_history) > 0:
            self.message_history[0].content = complete_system_prompt
        else:
            self.message_history.append(ChatMessage(role=Role.system.value, content=complete_system_prompt))

    def update_user_prompt_wrapper(self, user_prompt_wrapper: str):
        self.user_prompt_wrapper = user_prompt_wrapper

    def inject_message(self, response: str, role: Role = Role.assistant, off_switch: bool = False):
        """Injects a response into the message history, typically used for initial messages."""
        self.message_history.append(ChatMessage(role=role.value, content=response, off_switch=off_switch))

    # Call the LLM agent with the current message history and return a response.
    # If user_message is provided, it will be used to update the user prompt in the message history.
    # Responses must be structured as a ChatResponse object using prompt engineering
    def call_llm(self, user_message: str, enable_printing: bool = False):
        # Update the user prompt in the message history. If none, skip this step
        if user_message is not None:
            user_prompt = self.user_prompt_wrapper.replace(constants.user_message_placeholder, user_message)
            self.message_history.append(ChatMessage(role=Role.user.value, content=user_prompt))

        message_history_for_llm = self.get_message_history_formatted_for_llm(include_cot=True)

        # Call the llm agent with the context, expecting a response of type ChatResponse
        response_obj: ChatResponse = self.chat_bot.call_llm(message_history_for_llm, ChatResponse)
        cot = response_obj.hidden_thought_process
        response = response_obj.response
        off_switch = response_obj.off_switch

        # Replace the user message in the message history with the original user message
        if user_message is not None:
            self.message_history[-1].content = user_message

        # Print the explanation and the response
        if enable_printing:
            Logger.log(f"Assistant:", Level.VERBOSE)
            Logger.log(f"\tExplanation: {response_obj.hidden_thought_process}", Level.VERBOSE)
            Logger.log(f"\tResponse: {response}", Level.VERBOSE)
            Logger.log(f"\tOff switch: {off_switch}", Level.VERBOSE)
        
        self.message_history.append(ChatMessage(role=Role.assistant.value, cot=cot, content=response, off_switch=off_switch))

        return (response, off_switch)
    
    def get_message_history_formatted_for_llm(self, include_cot = False) -> List[Dict[str, str]]:
        message_history_for_llm = []
        for message in self.message_history:
            role = message.role
            if include_cot and message.cot is not None:
                # Format the content as a json string of the ChatResponse class (TODO make it agnostic to the class)
                content = "{"
                content += f'\t"hidden_thought_process": "{message.cot}", '
                content += f'\t"response": "{message.content}", '
                content += f'\t"off_switch": {str(message.off_switch).lower()}'
                content += "}"
            else:
                content = message.content
            message_history_for_llm.append({"role": role, "content": Utilities.decode(content)})
        return message_history_for_llm

    def get_message_history_as_string(self, include_cot = False) -> str:
        message_history_str = ""
        message_history_for_llm = self.get_message_history_formatted_for_llm(include_cot)
        for message in message_history_for_llm:
            message_history_str += f"{message['role']}: {message['content']}\n"
        return message_history_str
    
    def summarize_message_history(self, include_cot, enable_printing = False) -> str:
        """Summarizes the conversation history and updates the system prompt with the summary."""
        prompt = self.summarization_prompt
        message_history_str = self.get_message_history_as_string(include_cot)
        prompt += message_history_str

        # Call the llm agent with the context, expecting a response of type ChatResponse
        response_obj: ChatResponse = self.chat_bot.call_llm(prompt, ChatResponse)
        response = response_obj.response

        if enable_printing:
            Logger.log(f"Summary:", Level.VERBOSE)
            Logger.log(f"\tExplanation: {response_obj.hidden_thought_process}", Level.VERBOSE)
            Logger.log(f"\tResponse: {response}", Level.VERBOSE)

        self.system_prompt_conversation_summary = response
        self.update_system_prompt_in_message_history()
        self.message_history = [self.message_history[0]]  # Reset message history to only include the system prompt
        return response
