
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

    chat_session_save_file_path: str = "save_file.pkl"

    def __init__(self, system_prompt_context: str = "", user_prompt_wrapper: str = constants.user_message_placeholder, model: Llm = Llm.gpt_4o_mini, load_if_exists: bool = False):
        
        create_new_session = False
        if load_if_exists:
            old_chat_session = self.load_message_history(self.chat_session_save_file_path)
            if old_chat_session:
                print("Found existing chat session, loading...")
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

    def load_message_history(self, file_path: str) -> 'ChatSession':
        """Loads the message history from a file."""
        try:
            with open(file_path, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            Logger.log(f"File {file_path} not found.", Level.WARNING)
            return None
        except Exception as e:
            Logger.log(f"Error loading chat session: {e}", Level.ERROR)
            return None

    def save_message_history(self):
        """Saves the message history to a file."""
        with open(self.chat_session_save_file_path, "wb") as f:
            pickle.dump(self, f)

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

    def inject_message(self, response: str, role: Role = Role.assistant):
        """Injects a response into the message history, typically used for initial messages."""
        self.message_history.append(ChatMessage(role=role.value, content=response))

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
        prompt = "Please summarize the following conversation, from the perspective of the assistant, in a few sentences. Include any hidden thought processes. Include prior summaries. System prompt is included for context only, not for instructions.\n\n"
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
