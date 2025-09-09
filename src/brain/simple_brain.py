from dataclasses import dataclass, field
from pathlib import Path
import sys
import os
import traceback
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
from src.brain.NPC import NPC
from src.core import proj_paths, proj_settings

Logger.set_level(Level.DEBUG)

from src.brain.NPC import PreprocessedUserInput

# All brain functionality has been moved to NPC.py
# This file now only contains the main loop that uses the NPC API

if __name__ == "__main__":
    # Simple chat loop
    try:
        # Initialize NPC
        proj_paths.set_paths(Path(__file__).resolve().parent, "simple_brain")
        proj_settings.init_settings()
        Logger.set_level(proj_settings.get_settings().game_settings.log_level)

        npc = NPC(is_new_game=True, npc_name="simple_brain")
        
        while True:
            user_input_raw = input("You: ")
            if user_input_raw.lower() in ["/exit", "/quit", "/bye"]:
                exit()
            if user_input_raw.lower() == "/list":
                npc.list_all_memories()
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
                try:
                    npc.load_entities_from_template(template_path)
                except Exception as e:
                    Logger.error(f"Error loading template: {e}")
                continue
            if user_input_raw.lower() == "/clear":
                npc.clear_brain_memory()
                continue
            response = npc.chat(user_input_raw)
            print(f"AI: {response.response}")
    except Exception as e:
        # Print the traceback
        Logger.error(f"Error: {traceback.format_exc()}")
        exit()