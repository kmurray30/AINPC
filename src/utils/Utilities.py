import os
import sys
from typing import Dict, List, Optional, get_args, get_origin
from dotenv import load_dotenv
import uuid
import json
import numpy as np
from typing import Dict, List, Type, TypeVar
from datetime import datetime
import unidecode
from . import Logger
from dacite import from_dict, Config
from enum import Enum

T = TypeVar('T')

# Iterate over the fields of the dataclass and add them to the prompt suffix
# This will be used to instruct the LLM on how to format its response
def get_system_prompt_formatting_suffix(response_type: Type[T], prepend_override: str = None, append_override: str = None) -> str:
    """Returns the prompt suffix that specifies the formatting of the LLM response."""
    # Note: This assumes that the response_type is a dataclass with fields
    if not hasattr(response_type, '__dataclass_fields__'):
        raise ValueError(f"Response type {response_type} is not a dataclass with fields.")
    prompt_suffix = "Format your response as a JSON object with the following keys:\n" if prepend_override is None else prepend_override
    prompt_suffix += "{\n"
    for field_name, field_info in response_type.__dataclass_fields__.items():
        prompt_suffix += f"\t{field_name} <type {field_info.type.__name__}>: {field_info.metadata.get('desc', '')}\n"
    prompt_suffix += "}\n"
    prompt_suffix += "Make sure to include all keys, even if they are empty or null. If the type is str and the description specifies a list, make sure the field is a single string delimited by semicolons\n" if append_override is None else append_override
    return prompt_suffix

def extract_obj_from_llm_response(response_raw: str, response_type: Type[T]) -> T:
    # If type is primitive, we can directly parse it
    if response_type in [str, int, float, bool]:
        if response_raw.strip() == "":
            raise ValueError("Response is empty")
        return response_type(response_raw.strip())
    response_obj = extract_obj_from_json_str(response_raw, response_type, trim=True)
    return response_obj

def extract_obj_from_json_str(response_raw: str, response_type: Type[T], trim: bool = True) -> T:
        # Note: Sometimes the response starts with ```json, other times it starts with json
        # Trim everything before the first '{' and after the last '}'
        if trim:
            response_trimmed = response_raw[response_raw.find("{"):response_raw.rfind("}")+1]
        else:
            response_trimmed = response_raw
        json_dict = json.loads(response_trimmed)
        return extract_obj_from_dict(json_dict, response_type)

def extract_obj_from_dict(json_dict: Dict, response_type: Type[T]) -> T:
    if get_origin(response_type) is list:
        # If the response_type is a list, recurse
        # First check if the list is empty
        if not json_dict:
            return []
        entry_type = get_args(response_type)[0]  # Get the type of list entries
        # Recursively process each item in the list
        return [extract_obj_from_dict(item, entry_type) for item in json_dict]
    # If the response_type is a dataclass, use from_dict to convert
    else:
        # Use dacite's from_dict to convert the dict to the dataclass
        return from_dict(data_class=response_type, data=json_dict, config=Config(cast=[Enum], strict=True))

# def optional_str_hook(val):
#     if val is None or isinstance(val, str):
#         return val
#     raise TypeError(f"Expected Optional[str], got {type(val).__name__}")

# def extract_obj_from_json(json_dict: Dict, response_type: Type[T]) -> T:
#     # If type is a list of any type, we need to parse it as a list
#     if get_origin(response_type) is not list:
#         new_object = response_type(**json_dict)
#     else:
#         # If type is a list, we need to parse it accordingly
#         new_object = []
#         for item in json_dict:
#             entry_type = get_args(response_type)[0]  # Get ChatMessage from List[ChatMessage]
#             new_object.append(entry_type(**item))
#     return new_object

# def extract_obj_from_dict(json_dict: Any, response_type: Type[T]) -> T:
#     """
#     Recursively converts a JSON dict/list into a dataclass or list of dataclasses,
#     enforcing field types and handling nested structures.
#     """
#     origin = get_origin(response_type)
#     # If the response_type is a list (e.g., List[ChatMessage])
#     if origin is list:
#         entry_type = get_args(response_type)[0]  # Get the type of list entries
#         # Recursively process each item in the list
#         return [extract_obj_from_dict(item, entry_type) for item in json_dict]
#     # If the response_type is a dataclass
#     elif is_dataclass(response_type):
#         kwargs = {}  # Prepare arguments for the dataclass constructor
#         for f in fields(response_type):
#             expected_type = f.type  # Get the expected type for this field
#             value = json_dict.get(f.name)  # Get the value from the JSON dict
#             if value is None:
#                 kwargs[f.name] = None  # Allow missing/None values
#             else:
#                 sub_origin = get_origin(expected_type)
#                 # If the field is a list or another dataclass, recurse
#                 if sub_origin is list or is_dataclass(expected_type):
#                     kwargs[f.name] = extract_obj_from_dict(value, expected_type)
#                 else:
#                     # For primitive types, enforce type
#                     if not isinstance(value, expected_type):
#                         raise TypeError(f"Field '{f.name}' expected {expected_type}, got {type(value).__name__}")
#                     kwargs[f.name] = value
#         # Instantiate the dataclass with the processed fields
#         return response_type(**kwargs)
#     else:
#         # For primitive types, enforce type and return
#         if not isinstance(json_dict, response_type):
#             raise TypeError(f"Expected {response_type}, got {type(json_dict).__name__}")
#         return json_dict

def load_rules_from_file(rules_file_name, ruleset_name) -> List[str]:
    # Ensure the file name is in the correct format (e.g. "pat_rules.json", no path, with json extension)
    if not rules_file_name.endswith(".json") or "/" in rules_file_name or "\\" in rules_file_name or rules_file_name.count(".") != 1:
        raise ValueError(f"Invalid file name: {rules_file_name}. Must be a json file name without a path (file should be present in the resources folder).")

    pat_rules_path = get_path_from_project_root(f"src/resources/{rules_file_name}")
    pat_prompts: Dict[str, List[str]] = json.load(open(pat_rules_path))

    # Extract the rules and concatenate them into a single string
    pat_rules = pat_prompts[ruleset_name]
    return pat_rules

def load_json_from_file(file_path):
    conversation_path = get_path_from_project_root(file_path)
    with open(conversation_path, "r") as file:
        conversation = json.load(file)

    # Return the conversation as a list of strings
    return conversation

def load_json_custom(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data

def add_to_entities(entity_df, id, vector):
    entity_df[0].append(id)
    entity_df[1].append(vector)

def add_to_hashtable(hashtable, id, content):
    hashtable[id] = hash(content)

def persist_hashtable_to_file(hashtable, filename):
    with open(filename, "w") as f:
        for k, v in hashtable.items():
            f.write(f"{k},{v}\n")

# Load the hashtable from a file, type given
def load_hashtable_from_file(filename, content_type=str):
    hashtable = {}
    # Read the hashtable from file. If the file does not exist, create an empty hashtable
    try:
        with open(filename, "r") as f:
            for line in f:
                k, v = line.strip().split(",")
                hashtable[k] = content_type(v)
    except FileNotFoundError:
        Logger.log(f"File {filename} not found. Creating empty hashtable...")
    return hashtable

def cosine_similarity(embedding1, embedding2):
    # Convert lists to numpy arrays
    embedding1 = np.array(embedding1)
    embedding2 = np.array(embedding2)
    
    # Compute the cosine similarity
    dot_product = np.dot(embedding1, embedding2)
    norm_embedding1 = np.linalg.norm(embedding1)
    norm_embedding2 = np.linalg.norm(embedding2)
    similarity = dot_product / (norm_embedding1 * norm_embedding2)
    
    return similarity

def generate_guid():
    return str(uuid.uuid4())

def init_dotenv():
    # Get the path of the .env file
    if getattr(sys, 'frozen', False):
        # The application is running in a PyInstaller bundle
        env_path = os.path.join(sys._MEIPASS, '.env')
    else:
        # The application is running in a normal Python environment
        env_path = get_path_from_project_root('.env')
    load_dotenv(dotenv_path=env_path)

def get_project_root():
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Get the root directory of the project by going up two levels from the script directory
    project_root = os.path.abspath(os.path.join(script_dir, '../..'))

    return project_root

def is_dir_empty(dir_path):
    """Return True if the directory is empty, False otherwise."""
    # Check if the dir exists
    if not os.path.exists(dir_path):
        return True
    
    # Check if the dir is empty
    return not bool(os.listdir(dir_path))

# Function to call the OpenAI API
def call_openai(prompt):
    completion = chatGptClient.chat.completions.create(
        model="gpt-3.5-turbo",
        # model="gpt-4-turbo-preview",
        # model="gpt-4-0125-preview",
        messages=chatGptMessages
    )
    response = completion.choices[0].message.content
    return response

# Function to call the OpenAI API
def call_openai_persistent(prompt):
    chatGptMessages.append({"role": "user", "content": prompt})
    response = call_openai(prompt)
    chatGptMessages.append({"role": "assistant", "content": response})
    return response

# Example input: "generated/temp/temp.mp3"
# Example output: "/path/to/project/generated/temp/temp.mp3"
def get_path_from_project_root(relative_path):
    # Get the root directory of the project
    project_root = get_project_root()

    # Get the absolute path of the file by joining the project root and the relative path
    file_path = os.path.join(project_root, relative_path)

    return file_path

def get_all_files_in_directory(directory) -> List[str]:
    # Get a list of all files in the directory
    directory_from_root = get_path_from_project_root(directory)
    file_names = os.listdir(directory_from_root)
    return file_names

def save_index_id(index_id):
    with open('index_id.txt', 'w') as f:
        f.write(str(index_id))

def load_index_id():
    try:
        with open('index_id.txt', 'r') as f:
            return int(f.read())
    except FileNotFoundError:
        Logger.log("No index_id found. A new one will be generated.")
        return None
    
# Get the current time as a string formatted as YYYYMMDD_HHMMSS.
def get_current_time_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def decode(input: str) -> str:
    return unidecode.unidecode(input)

def decode_list(input: List[str]) -> List[str]:
    return [decode(item) for item in input]