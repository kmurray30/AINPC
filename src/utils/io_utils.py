from typing import Any
from typing import Type, TypeVar
from pathlib import Path
from dataclasses import asdict, is_dataclass

from src.utils import Logger, parsing_utils

import yaml

from typing import Any, Dict, List
import json
from typing import Dict, List, Type, TypeVar
from pathlib import Path
from dataclasses import asdict, is_dataclass

from src.utils import Utilities


import yaml

T = TypeVar('T')

class IndentDumper(yaml.SafeDumper):
    # force indented block sequences under mappings
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

def save_to_yaml_file(data: Any, file_path: Path) -> None:
    """Save a dataclass to a YAML file, casting Enums to their names."""
    data_dict = parsing_utils.obj_to_dict(data)

    # Write the dictionary to the YAML file
    with open(file_path, 'w') as file:
        yaml.dump(
            data_dict, 
            file, 
            Dumper=IndentDumper,
            default_flow_style=False, 
            sort_keys=False, 
            indent=2)

# File must be a list of objects
def append_to_yaml_file(data: Any, file_path: Path) -> None:
    """Append a dictionary to a YAML file."""
    if not is_dataclass(data):
        raise ValueError("Data must be a dataclass instance.")
    # Load existing data if the file exists
    if file_path.exists():
        try:
            with open(file_path, 'r') as file:
                existing_data = yaml.safe_load(file) or []
        except Exception:
            # If the file is partially written or corrupted, reset to empty list
            existing_data = []
    else:
        existing_data = []

    # Convert to dict and cast enums
    data_dict = asdict(data)
    data_dict = parsing_utils.cast_enums(data_dict)  # Recursively cast Enums to strings

    # Append the new data
    existing_data.append(data_dict)

    # Write back atomically to the file to avoid corruption under concurrency
    file_path.parent.mkdir(parents=True, exist_ok=True)
    import tempfile, os
    with tempfile.NamedTemporaryFile('w', delete=False, dir=file_path.parent, prefix=file_path.name + '.', suffix='.tmp') as tmp:
        yaml.dump(existing_data, tmp, default_flow_style=False, sort_keys=False)
        try:
            tmp.flush()
            os.fsync(tmp.fileno())
        except Exception:
            pass
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, file_path)

def load_yaml_into_dataclass(file_path: Path, return_type: Type[T]) -> T:
    """Load YAML into structure described by `return_type` (dataclass/list/dict/enum/primitive/Optional)."""
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    # Single entry point: run the same recursion at the top level
    return parsing_utils.convert_to_dataclass(data, return_type)

def load_json_into_dataclass(file_path: Path, return_type: Type[T]) -> T:
    """Load JSON into structure described by `return_type` (dataclass/list/dict/enum/primitive/Optional)."""
    with open(file_path, "r") as f:
        data = json.load(f)

    # Single entry point: run the same recursion at the top level
    return parsing_utils.convert_to_dataclass(data, return_type)

def load_rules_from_file(rules_file_name, ruleset_name) -> List[str]:
    # Ensure the file name is in the correct format (e.g. "pat_rules.json", no path, with json extension)
    if not rules_file_name.endswith(".json") or "/" in rules_file_name or "\\" in rules_file_name or rules_file_name.count(".") != 1:
        raise ValueError(f"Invalid file name: {rules_file_name}. Must be a json file name without a path (file should be present in the resources folder).")

    pat_rules_path = Utilities.get_path_from_project_root(f"src/resources/{rules_file_name}")
    pat_prompts: Dict[str, List[str]] = json.load(open(pat_rules_path))

    # Extract the rules and concatenate them into a single string
    pat_rules = pat_prompts[ruleset_name]
    return pat_rules

def load_json_from_file(file_path):
    conversation_path = Utilities.get_path_from_project_root(file_path)
    with open(conversation_path, "r") as file:
        conversation = json.load(file)

    # Return the conversation as a list of strings
    return conversation

def load_json_custom(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data

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