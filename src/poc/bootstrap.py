# src/poc/bootstrap.py
from pathlib import Path
from src.core import proj_paths, proj_settings
from src.utils import Logger

def init_app(save_name: str, project_path: Path, templates_dir_name: str = "default", version: float = 1.0) -> None:
    # Init the paths singleton
    proj_paths.set_paths(project_path=project_path,
                    templates_dir_name=templates_dir_name,
                    version=version,
                    save_name=save_name)
    
    # Init the settings singleton
    game_settings_path = project_path / "templates" / templates_dir_name / "game_settings.yaml"
    proj_settings.init_settings(game_settings_path)

    # Set the log level
    Logger.set_level(proj_settings.get_settings().app_settings.log_level)
