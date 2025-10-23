from ast import List
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))) # Adjust the path to the project root
from src.utils import Logger
from src.apps.companion_1.view import View
from src.apps.companion_1.presenter import Presenter
from src.core import proj_paths, proj_settings
from src.npcs.npc1.npc1 import NPC1
from src.npcs.npc2.npc2 import NPC2

# NPC options mapping
npc_options = {
    "npc1": (NPC1, 1.0),
    "npc2": (NPC2, 2.0)
}

def main() -> None:
    # Read the args
    if len(sys.argv) < 3 or len(sys.argv) > 5:
        Logger.log("Usage: python main.py <npc_type> <save_name> [templates_dir_name] [--no-save]")
        Logger.log("  npc_type: npc1 or npc2")
        Logger.log("  save_name: name for the save directory")
        Logger.log("  templates_dir_name: optional, defaults to 'default'")
        Logger.log("  --no-save: optional flag to disable saving")
        return

    npc_type_str = sys.argv[1].lower()
    if npc_type_str not in npc_options:
        Logger.log(f"Unknown NPC type: {npc_type_str}. Options: {list(npc_options.keys())}")
        return

    save_name = sys.argv[2]
    templates_dir_name = "default"
    save_enabled = True
    force_new_game = False

    # Parse remaining arguments
    remaining_args = sys.argv[3:]
    for arg in remaining_args:
        if arg == "--no-save":
            save_enabled = False
        elif arg == "force-new":
            force_new_game = True
        elif not arg.startswith("--"):
            templates_dir_name = arg
        else:
            Logger.log(f"Unknown argument: {arg}")
            return
    
    # Get NPC class and version
    npc_class, version = npc_options[npc_type_str]
    
    # Init the settings and paths singletons
    proj_paths.set_paths(
        project_path=Path(__file__).resolve().parent,
        templates_dir_name=templates_dir_name,
        version=version,
        save_name=save_name
    )
    proj_settings.init_settings(proj_paths.get_paths().app_settings)

    view = View()
    presenter = Presenter(view, npc_class=npc_class, save_enabled=save_enabled, force_new_game=force_new_game)
    presenter.run()

# Take in arguments for NPC type and save name
if __name__ == "__main__":
    print("Starting the companion_1 program...")
    main()
