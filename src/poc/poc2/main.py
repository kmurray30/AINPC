from ast import List
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))) # Adjust the path to the project root
from src.utils import Logger
from src.poc.poc2.view import View
from src.poc.poc2.presenter import Presenter
from src.poc import bootstrap

def main() -> None:
    # Read the args
    if len(sys.argv) == 2:
        save_name = sys.argv[1]
        force_new_game = False
    elif len(sys.argv) == 3:
        save_name = sys.argv[1]
        force_new_game = sys.argv[2]
        if force_new_game.lower() != "force-new":
            raise ValueError("Invalid argument provided. Please provide a save name and an optional boolean value 'force-new'.")
        if force_new_game.lower() == "force-new":
            force_new_game = True
    elif len(sys.argv) > 3:
        Logger.log("Too many arguments provided.")
        return
    else:
        Logger.log("No save name provided. Please provide a save name as an argument.")
        return
    
    # Init the settings and paths singletons
    bootstrap.init_app(save_name=save_name, project_path=Path(__file__).resolve().parent)

    view = View()
    presenter = Presenter(view, force_new_game=force_new_game)
    presenter.run()

# Take in one argument for the save name
if __name__ == "__main__":
    print("Starting the program...")
    main()