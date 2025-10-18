from dataclasses import dataclass, field
from pathlib import Path
import sys
import os
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))) # Adjust the path to the project root

from src.npcs.npc_protocol import NPCProtocol
from src.npcs.NPC1 import NPC1
from src.npcs.NPC2 import NPC2
from src.core.schemas.CollectionSchemas import Entity
from src.utils import Logger
from src.utils.Logger import Level
from src.core import proj_paths, proj_settings

Logger.set_level(Level.DEBUG)

# # App configurations here
# npc_type: type[NPCProtocol] = NPC1
# templates_dir_name: str = "sample"
# save_name: str = "sample1"

npc_options = {
    "NPC1": (NPC1, 1.0),
    "NPC2": (NPC2, 2.0)
}

if __name__ == "__main__":
    # Simple chat loop
    try:
        # Get the CLI arguments
        args = sys.argv[1:]
        if len(args) != 3:
            Logger.error("Usage: python simple_ui.py <npc_type> <templates_dir_name> <save_name>")
            exit()
        npc_type_str = args[0].upper()
        if npc_type_str not in npc_options:
            Logger.error(f"Unknown NPC type: {npc_type_str}. Options: {list(npc_options.keys())}")
            exit()
        npc_type = npc_options[npc_type_str][0]
        version = npc_options[npc_type_str][1]
        templates_dir_name = args[1]
        if "/" in templates_dir_name:
            Logger.error("templates_dir_name is just the name of the templates directory under templates/, not a full path")
            exit()
        save_name = args[2]
        if "/" in save_name:
            Logger.error("save_name is just the name of the save directory under saves/, not a full path")
            exit()

        # Initialize project path to point to this directory
        proj_paths.set_paths(
            project_path=Path(__file__).resolve().parent,
            templates_dir_name=templates_dir_name,
            version=version,
            save_name=save_name
        )
        # Validate the template directory exists
        if not os.path.exists(proj_paths.get_paths().npcs_templates_dir):
            raise ValueError(f"Template directory does not exist: {proj_paths.get_paths().npcs_templates_dir}")

        proj_settings.init_settings(proj_paths.get_paths().app_settings)
        Logger.set_level(proj_settings.get_settings().app_settings.log_level)

        npc: NPCProtocol = npc_type(npc_name_for_template_and_save="john")
        
        while True:
            user_input_raw = input("You: ")
            if user_input_raw.lower() in ["/exit", "/quit", "/bye"]:
                exit()
            if user_input_raw.lower() == "/list":
                try:
                    all_memories = npc.get_all_memories()
                except NotImplementedError as e:
                    Logger.error(f"Error getting all memories: {e}")
                    continue
                for memory in all_memories:
                    Logger.verbose(f"Memory: {memory.content}")
                continue
            if user_input_raw.lower().startswith("/path"):
                # Print the current path of the runtime environment
                Logger.verbose(f"Project root path: {os.getcwd()}")
                Logger.verbose(f"Path to this file: {os.path.dirname(__file__)}")
                continue
            if user_input_raw.lower().startswith("/load"):
                args = user_input_raw.lower().split(" ")
                if len(args) != 2:
                    Logger.error("Usage: /load <npc_name>")
                    continue
                npc_name = args[1]
                try:
                    npc_template_path = proj_paths.get_paths().npc_entities_template(npc_name)
                    npc.load_entities_from_template(npc_template_path)
                except Exception as e:
                    Logger.error(f"Error loading template: {traceback.format_exc()}")
                    continue
                continue
            if user_input_raw.lower() == "/save":
                npc.maintain()
                continue
            if user_input_raw.lower() == "/clear":
                try:
                    npc.clear_brain_memory()
                except NotImplementedError as e:
                    Logger.error(f"Error clearing brain memory: {e}")
                    continue
                continue
            if user_input_raw.lower().startswith("/"):
                Logger.error(f"Unknown command: {user_input_raw}")
                continue
            response = npc.chat(user_input_raw)
            print(f"AI: {response.response}")
    except Exception as e:
        # Print the traceback
        Logger.error(f"Error: {traceback.format_exc()}")
        exit()