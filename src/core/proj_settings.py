from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from src.core.schemas.Schemas import GameSettings
from src.core import proj_paths
from src.utils import io_utils

@dataclass (frozen=True)
class Settings:
    game_settings: GameSettings

# Singleton instance
_settings: Optional[Settings] = None
_frozen: bool = False

def init_settings() -> None:
    global _settings, _frozen
    if _frozen:
        raise RuntimeError("Settings have already been initialized and cannot be modified.")
    game_settings_path: Path = proj_paths.get_paths().game_settings
    game_settings = io_utils.load_yaml_into_dataclass(game_settings_path, GameSettings)
    _settings = Settings(game_settings=game_settings)
    _frozen = True

def get_settings() -> Settings:
    if _settings is None:
        raise ValueError("Settings have not been set. Call init_settings() first.")
    return _settings