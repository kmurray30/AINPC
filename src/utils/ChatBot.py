import os
import sys
from typing import Dict, List, Type, TypeVar

import openai
from dotenv import load_dotenv
from openai import OpenAI
import ollama

from src.utils import Logger, Utilities
from src.utils.Logger import Level
from src.core.Constants import embedding_models, Llm, Platform

filename = os.path.splitext(os.path.basename(__file__))[0]
if __name__ == "__main__" or __name__ == filename: # If the script is being run directly
    from Utilities import init_dotenv
else: # If the script is being imported
    from .Utilities import init_dotenv

T = TypeVar('T')

class ChatBot:

    current_chat_model = Llm.gpt_4o_mini
    llm_formatting_retries = 3

    # Load the OpenAI API key from the .env file and initialize the OpenAI client
    init_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    chatGptClient = OpenAI()

    def __init__(self, model=None):
        if model:
            self.current_chat_model = model

    def set_chat_model(self, model):
        self.current_chat_model = model

    def get_platform_of_model(self, model):
        for platform, models in embedding_models.items():
            if model in models:
                return platform
        return None

    # Function to call the OpenAI API
    def call_chat_agent(self, chatGptMessages):
        platform = self.get_platform_of_model(self.current_chat_model)
        if platform == Platform.open_ai:
            completion = self.chatGptClient.chat.completions.create(
                model=self.current_chat_model.value,
                messages=chatGptMessages
            )
            response = completion.choices[0].message.content
            return response
        elif platform == Platform.ollama:
            response = ollama.chat(messages = chatGptMessages, model=self.current_chat_model)
            return response
        else:
            raise Exception(f"ChatGPT model {self.current_chat_model} not supported")

    def call_chat_agent_and_update_message_history(self, prompt, chat_messages):
        chat_messages.append({"role": "user", "content": prompt})
        response = self.call_chat_agent(chat_messages)
        chat_messages.append({"role": "assistant", "content": response})
        return response

    def call_chat_agent_with_custom_context(self, prompt, custom_system_context = "You are a helpful assistant."):
        chatGptMessages = [
            {"role": "system", "content": custom_system_context}
        ]
        return self.call_chat_agent_and_update_message_history(prompt, chatGptMessages)

    def call_chat_agent_with_context(self, prompt: str, message_history: List[Dict[str, str]], rules: List[str], debug: bool = False, persist = True):
        # Create the full context for the ChatGPT - this includes the rules, message history, and latest user prompt
        full_context_for_chatagent = [
            {"role": "system", "content": "".join(rules)}
        ]

        # Append the user prompt to the message history
        # message_history.append({"role": "user", "content": prompt})
        # Append the message history to the full context
        user_message = {"role": "user", "content": prompt}
        full_context_for_chatagent += message_history + [user_message]

        # # Try with system prompt closer to the end
        # full_context_for_chatagent = message_history + full_context_for_chatagent
        # Append the user prompt to the full context
        # full_context_for_chatagent.append({"role": "user", "content": prompt})

        # Call ChatGPT with the full context
        response = self.call_chat_agent(full_context_for_chatagent)

        # print("***DEBUG***")
        # for message in full_context_for_chatagent:
        #     print(message["role"] + ": " + message["content"])
        # print("***DEBUG***")

        # Append the response to the message history
        if (persist == True):
            llm_response = {"role": "assistant", "content": response}
            message_history += [user_message, llm_response]

        if (debug == True):
            print("DEBUG INFO: " + str(message_history))
        return response

    def call_llm(self, message_history_for_llm: List[Dict[str, str]], response_type: Type[T] = None):
        if response_type is None:
            return self.call_chat_agent(message_history_for_llm)
        
        for _ in range(self.llm_formatting_retries):
            response_raw = self.call_chat_agent(message_history_for_llm)
            try:
                response_obj = Utilities.extract_response_obj(response_raw, response_type)
                return response_obj
            except Exception as e:
                Logger.log(f"Response from LLM agent is not in the correct format for {response_type.__name__}", Level.WARNING)
                Logger.log(f"Response: {response_raw}", Level.WARNING)
                Logger.log(f"Retrying...", Level.WARNING)

        raise ValueError(f"Failed to retrieve a valid response from the LLM agent after {self.llm_formatting_retries} retries.")


def get_default_rules():
    return [
        "You are a helpful assistant.",
        "You will be a role playing master"] # TODO: will update more rules later -mugdha

set_context_prefix = "set-context: "
instructions = f"""
Key commands:
exit: Exit the ChatBot
reset: Reset the message history
{set_context_prefix}<context>: Set a new context
"""

customContext = "You are a helpful assistant."

# Take in the context as a parameter
def main():
    chat_bot = ChatBot()
    if len(sys.argv) > 1:
        inputContext = sys.argv[1]
        if inputContext == "custom":
            custom_context = customContext
        else:
            custom_context = inputContext
    else:
        custom_context = get_default_rules()
    print("Welcome to the ChatBot!")
    message_history = []
    print("Context set to: ", custom_context)
    print(instructions)
    while True:
        user_input = input("You:\n")
        if user_input.lower() == "exit":
            break
        elif user_input.startswith(set_context_prefix):
            custom_context = user_input[len(set_context_prefix):]
            print("Context set to: ", custom_context)
        elif user_input.lower() == "reset":
            message_history = []
            print("\nMessage history reset\n")
        elif user_input:
            response = chat_bot.call_chat_agent_with_context(user_input, message_history, custom_context, debug=False)
            print("\nChatGPT:\n", response, "\n")

if __name__ == "__main__":
    main()