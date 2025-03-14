import os
import sys
from typing import Dict, List
from dotenv import load_dotenv
import uuid
import json
import numpy as np
from typing import Dict, List, Type, TypeVar
from datetime import datetime
import unidecode
from . import Logger

T = TypeVar('T')

def extract_response_obj(response_raw: str, response_type: Type[T]) -> T:
        # Note: Sometimes the response starts with ```json, other times it starts with json
        # Trim everything before the first '{' and after the last '}'
        response_trimmed = response_raw[response_raw.find("{"):response_raw.rfind("}")+1]
        json_response = json.loads(response_trimmed)
        # Try to convert the response to the specified object
        response_obj = response_type(**json_response)
        return response_obj

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

def add_to_entities(entity_df, id, content, from_field, to_field, vector):
    entity_df[0].append(id)
    entity_df[1].append(content)
    entity_df[2].append(from_field)
    entity_df[3].append(to_field)
    entity_df[4].append(vector)

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