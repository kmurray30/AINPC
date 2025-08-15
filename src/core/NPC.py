from dataclasses import dataclass
import os
from typing import Dict, List, Type, TypeVar, Optional
from src.core.Schemas import GameSettings
from src.utils import Logger
from src.utils.ChatBot import ChatBot
from src.utils.Logger import Level
from .Constants import Role
from .ResponseTypes import ChatResponse
from src.core.Constants import Constants as constants
from src.core.ConversationMemory import ConversationMemory, ConversationMemoryState
from src.utils import llm_utils, io_utils
from src.poc import proj_paths, proj_settings

DEBUG_LEVEL = ""
T = TypeVar('T')

@dataclass
class NPCTemplate:
    initial_system_context: str
    initial_response: Optional[str] = None

@dataclass
class NPCState:
    conversation_memory: ConversationMemoryState
    system_context: str
    user_prompt_wrapper: str

class NPC:
    # Store the message history with the agent name and the message content
    # This history cannot be passed directly to the chat agent, it needs to be formatted to replace the agent names with the roles
    chat_formatting_suffix: str

    # Part of the state
    conversation_memory: ConversationMemory
    system_context: str
    user_prompt_wrapper: str = constants.user_message_placeholder # TODO ignoring this for now

    # TODO Keep as class variable, move everything else to init if not already there
    is_new_game: bool

    game_settings: GameSettings
    save_paths: proj_paths.SavePaths

    def __init__(self, is_new_game: bool):
        self.game_settings = proj_settings.get_settings().game_settings
        self.save_paths = proj_paths.get_paths()

        self.is_new_game = is_new_game

        # Load the template once
        self.template = self._load_template()

        # Load the state and initialize the conversation memory
        if not is_new_game:
            self.load_state()
        else:
            self.init_state()

        self.chat_formatting_suffix = llm_utils.get_formatting_suffix(ChatResponse)
    
    def _get_full_system_prompt_for_chat(self) -> str:
        """Returns the full system prompt, including context, conversation summary, and response formatting."""
        complete_system_prompt = f"Context:\n{self.system_context}\n\n"
        conversation_summary = self.conversation_memory.get_chat_summary_as_string()
        if conversation_summary:
            complete_system_prompt += f"Conversation summary:\n{conversation_summary}\n\n"
        complete_system_prompt += f"Response formatting:\n{self.chat_formatting_suffix}\n\n"
        return complete_system_prompt
    
    def _prepend_system_prompt(self, chat_history_formatted: List[Dict[str, str]], system_prompt: str) -> List[Dict[str, str]]:
        """Prepends the system prompt to the chat history formatted for LLM."""
        return [{"role": Role.system.value, "content": system_prompt}] + chat_history_formatted
    
    def maintain(self):
        """Maintains the NPC state, including summarizing the conversation if necessary."""
        # Maintain the conversation memory
        self.conversation_memory.maintain()
        
        # Save the current state after maintenance
        Logger.log("Saving current NPC state", Level.INFO)
        self.save_state()

    def inject_message(self, response: str, role: Role = Role.assistant, cot: str = None, off_switch: bool = False):
        """Injects a response into the message history, typically used for initial messages."""
        self.conversation_memory.append_chat(response, role=role, cot=cot, off_switch=off_switch)

    def update_user_prompt_wrapper(self, user_prompt_wrapper: str):
        self.user_prompt_wrapper = user_prompt_wrapper

    # Call the LLM agent with the current message history and return a response.
    # If user_message is provided, it will be used to update the user prompt in the message history.
    # Responses must be structured as a ChatResponse object using prompt engineering
    def call_llm_for_chat(self, user_message: str = None, enable_printing: bool = False) -> ChatResponse:
        # Add the latest user prompt to the chat history. If none, skip this step
        if user_message is not None:
            self.conversation_memory.append_chat(user_message, role=Role.user, off_switch=False)

        # Get the chat history formatted for LLM
        chat_history_dict = self.conversation_memory.get_chat_memory_in_llm_format(include_hidden_details=True)

        # Prepend the system prompt to the chat history
        full_message_history_dict = self._prepend_system_prompt(chat_history_dict, self._get_full_system_prompt_for_chat())

        # Wrap the latest user message if requested
        if user_message is not None and self.user_prompt_wrapper:
            user_prompt_wrapped = self.user_prompt_wrapper.replace(constants.user_message_placeholder, user_message)
            full_message_history_dict[-1]["content"] = user_prompt_wrapped

        # Call the llm agent with the context, expecting a response of type ChatResponse
        Logger.log(f"Calling LLM with message history: {full_message_history_dict}", Level.DEBUG)
        response_obj: ChatResponse = ChatBot.call_llm(full_message_history_dict, ChatResponse)
        cot = response_obj.hidden_thought_process
        response = response_obj.response
        off_switch = response_obj.off_switch

        self.conversation_memory.append_chat(response, role=Role.assistant, off_switch=off_switch, cot=cot)

        return response_obj
    
    def _load_template(self) -> NPCTemplate:
        """Loads the NPC template from the template file."""
        try:
            template = io_utils.load_yaml_into_dataclass(self.save_paths.npc_template, NPCTemplate)
            return template
        except FileNotFoundError:
            Logger.log(f"NPC template file not found: {self.save_paths.npc_template}", Level.ERROR)
            raise FileNotFoundError(f"NPC template file not found: {self.save_paths.npc_template}")
        except Exception as e:
            Logger.log(f"Error loading NPC template: {e}", Level.ERROR)
            raise e
    
    def get_initial_response(self) -> str:
        """Gets the initial response from the NPC template."""
        return self.template.initial_response or ""
        
    def get_state(self) -> NPCState:
        """Returns the current state of the NPC."""
        return NPCState(
            conversation_memory=self.conversation_memory.get_state(),
            system_context=self.system_context,
            user_prompt_wrapper=self.user_prompt_wrapper
        )
    
    def init_state(self) -> None:
        """Initializes the NPC state for a new game."""
        self.conversation_memory = ConversationMemory.new_game()
        self.system_context = self.template.initial_system_context
    
    def load_state(self) -> None:
        try:
            prior_npc_state: NPCState = io_utils.load_yaml_into_dataclass(self.save_paths.npc_save_state, NPCState)
            self.conversation_memory = ConversationMemory.from_state(prior_npc_state.conversation_memory)
            self.system_context = prior_npc_state.system_context
            self.user_prompt_wrapper = prior_npc_state.user_prompt_wrapper
        except FileNotFoundError as e:
            Logger.log(f"NPC state file not found: {e}", Level.ERROR)
            Logger.log("Starting a new game.", Level.INFO)
            self.init_state()
        except Exception as e:
            Logger.log(f"Error loading NPC state: {e}", Level.ERROR)
            raise e

    def save_state(self) -> None:
        """Saves the message history and metadata to files."""

        # Ensure the directory exists
        os.makedirs(self.save_paths.npc_save_root, exist_ok=True)

        save_path = self.save_paths.npc_save_state

        # Create backup files in case the save fails
        backup_npc_state_path = save_path.with_suffix('.bak')
        if os.path.exists(save_path):
            os.replace(save_path, backup_npc_state_path)

        try:
            current_state = self.get_state()
            io_utils.save_to_yaml_file(current_state, save_path)

            # Remove backup files after successful save
            if os.path.exists(backup_npc_state_path):
                os.remove(backup_npc_state_path)

            Logger.log(f"Session saved successfully to {save_path}", Level.INFO)
        except Exception as e:
            Logger.log(f"Error saving session: {e}", Level.ERROR)
            # Restore from backup if save fails
            if os.path.exists(backup_npc_state_path):
                os.replace(backup_npc_state_path, save_path)
            raise e