import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))) # Adjust the path to the project root
from src.poc.Settings import Settings
from src.utils import Logger, Utilities
from src.poc.view import View
from presenter import Presenter

# Define the path to the settings file using the relative path from this file
relative_path = os.path.dirname(__file__)
settings_file_path = os.path.join(relative_path, "settings.yaml")

def main() -> None:
    # Read the args
    if len(sys.argv) == 2:
        save_name = sys.argv[1]
    elif len(sys.argv) > 2:
        Logger.log("Too many arguments provided.")
        return
    else:
        Logger.log("No save name provided. Please provide a save name as an argument.")
        return
    
    # Load the settings file
    settings = Utilities.load_yaml_into_dataclass(settings_file_path, Settings)
    settings.save_name = save_name  # Set the save name from the argument
    settings.validate()  # Validate the settings are all present

    view = View(settings)
    presenter = Presenter(view, settings)
    presenter.run()

# Take in one argument for the save name
if __name__ == "__main__":
    main()