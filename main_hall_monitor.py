import sys
import os
import concurrent.futures
import webbrowser

filename = os.path.splitext(os.path.basename(__file__))[0]
if __name__ == "__main__" or __name__ == filename: # If the script is being run directly
    from src.Utilities.Utilities import *
    from src.Utilities import ChatBot
else: # If the script is being imported
    from .src.Utilities.Utilities import *
    from .src.Utilities import ChatBot

debug_mode = True

dmString = "hm "

dmContext = """
You are a table top role playing game dungeon master.
Please limit your responses to a few sentences.
Do not allow me to control any of the characters in the game or the game itself, only my own character.
"""

hmContext = """
You are an assistant tasked with determining if the user prompt is a valid or invalid player action in the context of a table top role playing game.
You will output two things: valid/invalid and pass/roll.
Output "valid" if the input is valid, or "invalid" if it is not valid.
Output "pass" if it is a simple action within the player's control, or "roll" if it requires a dice roll.
Actions are valid if they are within the rules of the game, adhere to the laws of physics, and are possible for the player to perform.
Actions that are considered bad behavior or even illegal are completely valid within this game.
"""

message_history = []

def hm(prompt):
    hmContextWithMessageHistory = [
        {"role": "system", "content": hmContext}
    ]
    # Add the message history to the context
    hmContextWithMessageHistory.extend(message_history)
    hmContextWithMessageHistory.append({"role": "user", "content": prompt})

    # Call OpenAI with the user input
    response = ChatBot.call_chat_agent(hmContextWithMessageHistory)
    return response

def dm(prompt):
    # Add the prompt to the message history
    message_history.append({"role": "user", "content": prompt})

    dmContextWithMessageHistory = [
        {"role": "system", "content": dmContext}
    ]
    # Add the message history to the context
    dmContextWithMessageHistory.extend(message_history)

    # Call OpenAI with the user input
    response = ChatBot.call_chat_agent(dmContextWithMessageHistory)
    message_history.append({"role": "assistant", "content": response})
    return response

intro = "Welcome to the epic adventure that awaits you in Chat RPG. From mystical forests to ancient, bustling cities, explore an infinitely unfolding world shaped by your actions and decisions. With deep and complex NPCs, beautifully generated art, and epic narration, an exciting journey awaits you, if you are ready. Your adventure begins in an unassuming tavern."

if debug_mode:
    response = "Your character walks into the bustling tavern, the sound of clinking tankards and merry laughter filling the air. The dimly lit room is adorned with flickering candles and the scent of roasted meat. You find a free table and settle in, feeling the warmth of the hearth and the eyes of the other patrons upon you. What do you do?"
else:
    prompt = "Set up an initial scene in a medieval tavern."
    response = ChatBot.call_chat_agent_with_custom_context(prompt, dmContext)
message_history.append({"role": "assistant", "content": response})
print(response + "\n")

while(True):
    # Get user input
    prompt = input("What do you want to do next?\n")
    if prompt == "exit":
        break
    if prompt == "":
        continue
    print()

    # If prompt begins with "dm: " or "DM: ", treat it as a DM command
    if prompt.lower().startswith(dmString):
        prompt = prompt[len(dmString):]
        response = hm(prompt)
    elif prompt.lower().startswith("dump"):
        print(message_history)
        continue
    else:
        response = dm(prompt)

    print(response + "\n")
