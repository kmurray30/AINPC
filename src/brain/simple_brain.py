from dataclasses import dataclass, field
import sys
import os
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))) # Adjust the path to the project root
from src.brain import template_processor
from src.core.Constants import Role
from src.core.ChatMessage import ChatMessage
from src.utils import MilvusUtil, Utilities
from src.core.schemas.CollectionSchemas import Entity
from src.core.Agent import Agent
from src.utils import Logger
from src.utils.Logger import Level

TEST_DIMENSION = 1536

Logger.set_level(Level.DEBUG)

MilvusUtil.initialize_server()
collection_name = "simple_brain"
collection = MilvusUtil.load_or_create_collection(collection_name, dim=TEST_DIMENSION, model_cls=Entity)

chat_history: List[ChatMessage] = []

@dataclass
class PreprocessedUserInput:
    text: str = field(metadata={"desc": "The reworded user message. NEVER EMPTY. If you don't know what to say, just put the original message in here."})
    has_information: bool = field(metadata={"desc": "Whether the input contains information that the assistant should remember."})
    ambiguous_pronouns: str = field(metadata={"desc": "A list of pronouns that are ambiguous and need clarification.", "type": "strlist"})
    needs_clarification: bool = field(metadata={"desc": "Whether you need clarification on any of the pronouns."})

def preprocess_input(message_history: List[ChatMessage], last_messages_to_retain: int = 4) -> PreprocessedUserInput:
    preprocess_agent_system_prompt = f"""
    You are a text preprocessor. You will be given a user's input and must perform the following:
    - Summarize the information presented in the last message by the user.
    - Replace first person pronouns in the last user message with 'user' since the user is the one speaking
    - Replace second person pronouns in the last user message with 'assistant (me/I)' since you are the assistant
    - Replace third person pronouns in the last user message with the best guess of who the user is referring to. It should NOT be the user or the assistant. If you are not sure, set the clarification flag in your response. Err on the side of false unless it is absolutely necessary to clarify who the pronoun is referring to.
    - Note whether the input contains any kind of information. true for any declarations, false for questions.
    """
    if last_context:
        preprocess_agent_system_prompt += f"""
        Context:
        {last_context}
        """

    preprocess_agent = Agent(
        system_prompt=preprocess_agent_system_prompt,
        response_type=PreprocessedUserInput,
    )

    message_history_truncated = message_history[-last_messages_to_retain:]
    Logger.verbose(f"Full input to preprocessor LLM:\nContext:{preprocess_agent_system_prompt}\nMessage History:\n{message_history_truncated}")
    preprocessed_message = preprocess_agent.chat_with_history(message_history_truncated)
    if preprocessed_message.text == "":
        preprocessed_message.text = "<empty>"
    return preprocessed_message

def update_memory(preprocessed_user_text: str):
    rows = [
        Entity(key=preprocessed_user_text, content=preprocessed_user_text, tags=["memories"]),
    ]
    Logger.verbose(f"Updating memory with {preprocessed_user_text}")
    MilvusUtil.insert_dataclasses(collection, rows)
    collection.flush()
    Logger.verbose(f"Collection now has {collection.num_entities} entities")

def get_memories(preprocessed_user_text: str, topk: int = 5) -> List[Entity]:
    query = MilvusUtil.get_embedding(preprocessed_user_text, model=MilvusUtil.text_embedding_3_small)
    hits = MilvusUtil.search_relevant_records(collection, query, model_cls=Entity, topk=topk)
    Logger.verbose(f"Found {len(hits)} memories for {preprocessed_user_text}")
    # Print the memories with their similarity scores
    for hit in hits:
        Logger.verbose(f"Similarity: {hit[1]}, Content: {hit[0].content}")
    return [hit[0] for hit in hits]

def build_context(memories: List[Entity]):
    context = "\n".join([f"{memory.content}" for memory in memories])
    return context

last_context = ""

def process_user_input(user_input: str):
    global chat_history
    chat_history.append(ChatMessage(role=Role.user, content=user_input, cot=None, off_switch=False))
    preprocessed_message: PreprocessedUserInput = preprocess_input(chat_history, last_messages_to_retain=4)
    Logger.warning(f"Preprocessed message: {preprocessed_message}")
    if preprocessed_message.needs_clarification:
        return "I need clarification on one or more of the pronouns you used. Please rephrase your message."
    
    if preprocessed_message.has_information:
        update_memory(preprocessed_message.text)
    
    memories = get_memories(preprocessed_message.text, topk=5)
    context = build_context(memories)
    global last_context
    last_context = context
    response_agent_system_prompt = f"""
    You are a helpful assistant. You will be given some context and the user input and must respond to the user's message.
    
    Context:
    {context}
    """

    response_agent = Agent(
        system_prompt=response_agent_system_prompt,
        response_type=str,
    )

    message_history = [
        ChatMessage(role=Role.user, content=user_input, cot=None, off_switch=False),
    ]
    Logger.verbose(f"Full input to response LLM:\nContext:{response_agent_system_prompt}\nMessage History:\n{message_history}")
    response = response_agent.chat_with_history(message_history)
    chat_history.append(ChatMessage(role=Role.assistant, content=response, cot=None, off_switch=False))
    return response

if __name__ == "__main__":
    # Simple chat loop
    try:
        while True:
            user_input_raw = input("You: ")
            if user_input_raw.lower() in ["/exit", "/quit", "/bye"]:
                exit()
            if user_input_raw.lower() == "/list":
                all_memories = MilvusUtil.export_dataclasses(collection, Entity)
                # Print all the memories (without the embedding field)
                Logger.verbose(f"All memories:")
                for memory in all_memories:
                    Logger.verbose(f"{memory.key}")
                continue
            if user_input_raw.lower().startswith("/path"):
                # Print the current path of the runtime environment
                Logger.verbose(f"Project root path: {os.getcwd()}")
                Logger.verbose(f"Path to this file: {os.path.dirname(__file__)}")
                continue
            if user_input_raw.lower().startswith("/load"):
                args = user_input_raw.lower().split(" ")
                if len(args) != 2:
                    Logger.error("Usage: /load <template_path>")
                    continue
                template_path = args[1]
                if not template_path.endswith(".yaml"):
                    Logger.error("File must be a yaml file")
                    continue

                template_path = os.path.join(os.path.dirname(__file__), template_path)
                if not os.path.exists(template_path):
                    Logger.error(f"File {template_path} does not exist")
                    continue
                # Prepend the path to the filename
                template_path = os.path.join(os.path.dirname(__file__), template_path)
                entities = template_processor.template_to_entities_simple(template_path)
                MilvusUtil.insert_dataclasses(collection, entities)
                Logger.verbose(f"Loaded {len(entities)} entities from {template_path}")
                continue
            if user_input_raw.lower() == "/clear":
                MilvusUtil.drop_collection_if_exists(collection_name)
                collection = MilvusUtil.load_or_create_collection(collection_name, dim=TEST_DIMENSION, model_cls=Entity)
                continue
            response = process_user_input(user_input_raw)
            print(f"AI: {response}")
    except Exception as e:
        Logger.error(f"Error: {e}")
        exit()
    finally:
        MilvusUtil.disconnect_server()