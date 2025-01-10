import os
import sys
from dotenv import load_dotenv
import uuid
import psutil
import json
import numpy as np

def load_json_custom(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data

def add_to_entities(entity_df, id, content, vector):
    entity_df[0].append(id)
    entity_df[1].append(content)
    entity_df[2].append(vector)

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
        print(f"File {filename} not found. Creating empty hashtable...")
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

def save_index_id(index_id):
    with open('index_id.txt', 'w') as f:
        f.write(str(index_id))

def load_index_id():
    try:
        with open('index_id.txt', 'r') as f:
            return int(f.read())
    except FileNotFoundError:
        print("No index_id found. A new one will be generated.")
        return None