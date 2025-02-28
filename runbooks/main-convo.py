import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.utils import ChatBot, Utilities
from src.utils import ChatBot

message_history = []

rules = Utilities.load_rules_from_file("pat_prompts.json", "Ruleset 1", as_one_string = False)

# Create the loop in the terminal
prompt = ""
while True:
    response = ChatBot.call_chat_agent_with_context(prompt = prompt, message_history = message_history, rules = rules, persist = True, debug = False)
    print(f"\nAI:\n{response}\n")
    prompt = input("You:\n")
    if prompt.lower() == "exit":
        break
    elif prompt.lower() == "reset":
        message_history = []
        # Clear the terminal screen
        print("\033[H\033[J")
    else:
        print(f"You: {prompt}")