# src/poc/bootstrap.py
from pathlib import Path
from src.core import proj_paths, proj_settings
from src.utils import Logger

def init_app(save_name: str, project_path: Path) -> None:
    # Init the paths singleton
    proj_paths.set_paths(project_path=project_path,
                    save_name=save_name)
    
    # Init the settings singleton
    proj_settings.init_settings()

    # Set the log level
    Logger.set_level(proj_settings.get_settings().game_settings.log_level)
