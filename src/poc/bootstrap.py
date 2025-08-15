# src/poc/bootstrap.py
from pathlib import Path
from src.poc import proj_paths, proj_settings
from src.utils import Logger

def init_app(save_name: str, project_path: Path, npc_name: str = "companion") -> None:
    # Init the paths singleton
    proj_paths.set_paths(project_path=project_path,
                    save_name=save_name,
                    npc_name=npc_name)
    
    # Init the settings singleton
    proj_settings.init_settings()

    # Set the log level
    Logger.set_log_level(proj_settings.get_settings().game_settings.log_level)
