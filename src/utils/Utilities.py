import os
import sys
from typing import Any, Dict, List, Union, get_args, get_origin
from dotenv import load_dotenv
import uuid
import json
import numpy as np
from typing import Dict, List, Type, TypeVar
from datetime import datetime
import unidecode
from pathlib import Path
from dataclasses import MISSING, asdict, is_dataclass, fields
import numpy as np

from src.core import Constants

from . import Logger
from dacite import from_dict, Config
from dacite.exceptions import MissingValueError
from enum import Enum, EnumType
import yaml

T = TypeVar('T')

def generate_uuid_int64() -> np.int64:
    return np.int64(int(uuid.uuid4().int) >> 64)

def add_to_entities(entity_df, id, vector):
    entity_df[0].append(id)
    entity_df[1].append(vector)

def add_to_hashtable(hashtable, id, content):
    hashtable[id] = hash(content)

def persist_hashtable_to_file(hashtable, filename):
    with open(filename, "w") as f:
        for k, v in hashtable.items():
            f.write(f"{k},{v}\n")

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

def _get_project_root():
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

# Example input: "generated/temp/temp.mp3"
# Example output: "/path/to/project/generated/temp/temp.mp3"
def get_path_from_project_root(relative_path):
    # Get the root directory of the project
    project_root = _get_project_root()

    # Get the absolute path of the file by joining the project root and the relative path
    file_path = os.path.join(project_root, relative_path)

    return file_path

def get_all_files_in_directory(directory) -> List[str]:
    # Get a list of all files in the directory
    directory_from_root = get_path_from_project_root(directory)
    file_names = os.listdir(directory_from_root)
    return file_names

# Get the current time as a string formatted as YYYYMMDD_HHMMSS.
def get_current_time_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def decode(input: str) -> str:
    return unidecode.unidecode(input)

def decode_list(input: List[str]) -> List[str]:
    return [decode(item) for item in input]