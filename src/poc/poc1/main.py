import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))) # Adjust the path to the project root
from src.utils import Logger
from src.poc.view import View
from presenter import Presenter
from src.poc import bootstrap

def main() -> None:
    # Read the args
    if len(sys.argv) == 2:
        save_name = sys.argv[1]
        npc_name = "companion"  # Default NPC
    elif len(sys.argv) == 3:
        save_name = sys.argv[1]
        npc_name = sys.argv[2]
    elif len(sys.argv) > 3:
        Logger.log("Too many arguments provided.")
        return
    else:
        Logger.log("No save name provided. Please provide a save name as an argument.")
        return
    
    # Init the settings and paths singletons
    bootstrap.init_app(save_name=save_name, project_path=Path(__file__).resolve().parent, npc_name=npc_name)

    view = View()
    presenter = Presenter(view)
    presenter.run()

# Take in one argument for the save name
if __name__ == "__main__":
    print("Starting the program...")
    main()