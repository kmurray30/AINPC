import sys
from enum import Enum
from typing import List

sys.path.insert(0, "../..")
from src.core.Constants import Llm
from src.utils.ChatBot import ChatBot
from src.utils import parsing_utils

# Create the response object class Response:
class Response:
    def __init__(self, relevant_traits: str, possible_angles: str, response: str):
        self.relevant_traits = relevant_traits
        self.possible_angles = possible_angles
        self.response = response

# Initialize the chatbot
chatbot = ChatBot(model=Llm.gpt_4o)

messages = []
system_prompt = """
You are a character writer.
"""
messages.append({"role": "system", "content": system_prompt})

what_i_say_title = "What I say"
raj_info_title = "Raj info"


prompt_shell = f"""
Given the following things about Raj, please generate character responses from Raj to the subsequent '{what_i_say_title}' and using the prior conversation as context.

Context:
I am a man and fellow coworker of Raj having a conversation with him.

{raj_info_title}:
$$$RAJINFO$$$

{what_i_say_title}:
$$$PLAYERMESSAGE$$$

Response format (json):
{"{"}
    "relevant_traits": <str> [Choose a subset of the traits from Raj's info that are relevant to the question. Use brief summaries for them]
    "possible_angles": <str> [Describe what angles Raj could take in his response]
    "response": <str> [Keep it very short (1-2 sentences MAX) and in character. Try to use most or all of the angles. Use Raj's voice and mannerisms. Use stage directions. Make the character feel organic and human. Do not rely on cliches.]
{"}"}
"""

class Trait(Enum):
    # Base
    cool = "Tries to act cool and stylish—shortens words to glam them up, avoids clichés."
    chill = "Maintains a chill, low-energy demeanor unless showing off helps his image."
    innovative = "Overinvests in seeming innovative or trendy, with a try-hard cargo-cult approach to coolness."
    pop_culture = "Into swag and pop culture in a wannabe way."
    decent = "Fundamentally decent and non-threatening, but clueless and self-centered."
    humility = "Will crack the facade and show genuine vulnerable side if anyone calls him out."
    selfishness = "Self-centered and self-serving. Will usually try to make things about himself."

    # yoga
    objectifies_women = "Objectifies women — sees them as individuals, but also as a way to impress. Has a harmless puppy-dog facade."
    impress_women = "Seeks situations where he can impress women. Likes to talk about them like a pick up artist."
    fashion = "Into fashion and wearing expensive outfits tailored to occasions"
    scrawny = "Physically scrawny; avoids situations that might emasculate him or involve overexertion. Acts mildly prima donna about his body, but not flamboyantly."
    anti_lame = "Judges and avoids anything stereotypically “lame” or nerdy."
    
    # gov
    gossip = "Enjoys gossiping about people"
    networking = "Likes to network and make connections. Wants to position himself as someone who knows important people, but acknowledges that he currently doesn't."
    gov_lame = "Thinks most day to day government work is lame, and has given up on trying to make it cool."
    # opportunism = "Likes to make things about himself and angle it so he can personally gain from opportunities."
    # opportunism = "If someone else has an opportunity or good fortue, he will insert himself and try to personally gain from it."
    opportunism = "If someone else has an opportunity or good fortune, he will eagerly and untactfully insert himself and try to personally gain from it, if not take it for himself."

    # job
    job_hopes = "Had hoped that working in the government could get him connections and clout, but all it is is a boring desk job."
    job_coping = "Tries to cope with the letdown of his government job by trying to make it seem cool and impressive."

    # thousand
    impulsive = "Likes to spend money impulsively on lavish things"
    entrepeneur = "As a part of his creative spritit and desire to make a name for himself, he has a desire to start businesses that seem cool and innovative. Usually in trendy spaces."

    # tired
    sadness = "Has a sadness underneath his persona. When leveled with on a human level, he will drop his swag persona and show a more vulnerable side."
    neuroticism = "He can be neurotic and manic with his schemes, sometimes overextending himself."

    # star trek
    bully = "Will sometimes bully people who are nerdy or into things he thinks are lame. He is a little bit of a bully, but not in a mean way. He is just trying to be cool."

    # vulnerable
    coping = "In times of stress, sadness, and dissapointment, when there are things in his life he's deeply unhappy about or just aren't going his way, he will lean more into his persona and scheme-y nature. It can be a negative feedback loop."
    investments = "He is currently invested in aesthetic and lifestly choices that would make him seem cool. He is also invested in a local night club."
    disappointment = "He is currently disappointed with his life and career. Also lately his schemes haven't been paying off and impulse purchases have not been living up to his expectations."

    # sports
    sports = "He is not into traditionally masculine things like sports, nor is athletic. He would try to pivot at the topic into something related but more trendy or cool."

questions_and_info = {
    "base": {
        "raj_question": None,
        "raj_info": [Trait.cool, Trait.chill, Trait.innovative, Trait.pop_culture, Trait.decent, Trait.humility, Trait.selfishness]
    },
    "yoga": {
        "raj_question": "Hey, wanna go to a yoga class with me tomorrow morning?",
        "raj_info": [Trait.objectifies_women, Trait.impress_women, Trait.fashion, Trait.scrawny, Trait.anti_lame],
    },
    "gov": {
        "raj_question": "Did you hear councilman Roberts is losing his seat? One too many affairs, I guess. I think I might run for his position.",
        "raj_info": [Trait.gossip, Trait.networking, Trait.gov_lame, Trait.opportunism]
    },
    "job": {
        "raj_question": "I'm surprised you work in the government of all places. What made you choose that?",
        "raj_info": [Trait.job_hopes, Trait.job_coping]
    },
    "thousand": {
        "raj_question": "Yo Raj, I just got a thousand bucks from my parents. What should I do with it?",
        "raj_info": [Trait.impulsive, Trait.entrepeneur, Trait.networking, Trait.opportunism]
    },
    "tired": {
        "raj_question": "Yo man, you're looking a little tired today. Up late last night?",
        "raj_info": [Trait.sadness, Trait.neuroticism, Trait.investments]
    },
    "star trek": {
        "raj_question": "Dude I don't know what kind of TV you're into but I just started watching Star Trek. It's so good!",
        "raj_info": [Trait.anti_lame, Trait.bully]
    },
    "vulnerable": {
        "raj_question": "Hey man, I've noticed you've seemed a bit more on edge lately. Everything okay?",
        "raj_info": [Trait.sadness, Trait.coping, Trait.investments, Trait.disappointment]
    },
    "sports": {
        "raj_question": "Hey, did you catch the game last night? What a finish!",
        "raj_info": [Trait.sports, Trait.scrawny]
    },
    "all": {
        "raj_question": None,
        "raj_info": [
            Trait.objectifies_women, Trait.impress_women, Trait.fashion, Trait.scrawny, Trait.anti_lame,
            Trait.gossip, Trait.networking, Trait.gov_lame, Trait.opportunism,
            Trait.job_hopes, Trait.job_coping,
            Trait.impulsive, Trait.entrepeneur,
            Trait.sadness, Trait.neuroticism,
            Trait.bully,
            Trait.coping, Trait.investments, Trait.disappointment,
            Trait.sports
        ]
    }
}

question_category = "all"
player_message = None # If set to none, the message history will be cleared and the initial question will be asked

def converse(player_message: str) -> str:
    prompt = prompt_shell.replace("$$$RAJINFO$$$", raj_info).replace("$$$PLAYERMESSAGE$$$", player_message)
    messages.append({"role": "user", "content": prompt})
    response = chatbot.call_chat_agent(messages)
    messages.append({"role": "assistant", "content": response})
    print("Player: " + player_message)
    print("\nRaj: " + response)

# Start
question_category = "all"
if question_category not in questions_and_info:
    raise ValueError(f"Invalid question category: {question_category}")

# Get the info traits for the current question category
raj_info_list_enum: List[Trait] = questions_and_info["base"]["raj_info"] + questions_and_info[question_category]["raj_info"]
raj_info_list_str = [trait.value for trait in raj_info_list_enum]
raj_info = "\n".join(raj_info_list_str)
prompt_shell = prompt_shell.replace("$$$RAJINFO$$$", raj_info)

while True:
    player_message = input("You:\n")
    if player_message.lower() in ["/exit", "/quit", "/q"]:
        print("Exiting the conversation.")
        break
    if player_message.lower() in ["/clear", "/reset", "/c"]:
        print("Clearing the conversation history.\n")
        messages = [{"role": "system", "content": system_prompt}]
        continue
    if player_message.lower() == "/help":
        print("Available commands:")
        print("/exit, /quit, /q - Exit the conversation")
        print("/clear, /reset, /c - Clear the conversation history")
        print("/help - Show this help message")
        continue

    prompt = prompt_shell.replace("$$$PLAYERMESSAGE$$$", player_message)
    messages.append({"role": "user", "content": prompt})
    response_raw = chatbot.call_chat_agent(messages)
    messages.pop() # Replace the longform user prompt with just the player message
    messages.append({"role": "user", "content": player_message})
    messages.append({"role": "assistant", "content": response_raw})

    response_obj: Response = parsing_utils.extract_obj_from_json_str(response_raw, Response, trim=True)
    response_message = response_obj.response
    print("\nRaj: " + response_message + "\n")

# Replace placeholders in the prompt with actual values
messages = messages if player_message is not None else [{"role": "system", "content": "You are a character writer."}]
raj_info_list_enum: List[Trait] = questions_and_info["base"]["raj_info"] + questions_and_info[question_category]["raj_info"]
raj_info_list_str = [trait.value for trait in raj_info_list_enum]
raj_info = "\n".join(raj_info_list_str)
player_message = player_message if player_message is not None else questions_and_info[question_category]["raj_question"]

prompt = prompt_shell.replace("$$$RAJINFO$$$", raj_info).replace("$$$PLAYERMESSAGE$$$", player_message)

# Call 4o-mini to generate the response
messages.append({"role": "user", "content": prompt})
response = chatbot.call_chat_agent(messages)
# messages.pop()
messages.append({"role": "assistant", "content": response})
print("Player: " + player_message)
print("\nRaj: " + response)


# TODO base demo
# hide prompt shell from history
# TODO replace raj with darwish
# hide precog from output