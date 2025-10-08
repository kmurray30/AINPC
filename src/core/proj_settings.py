from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from src.core.schemas.Schemas import AppSettings
from src.utils import io_utils

@dataclass (frozen=True)
class Settings:
    app_settings: AppSettings

# Singleton instance
_settings: Optional[Settings] = None
_frozen: bool = False

def init_settings(app_settings_path: Path) -> None:
    global _settings, _frozen
    if _frozen:
        raise RuntimeError("Settings have already been initialized and cannot be modified.")
    app_settings = io_utils.load_yaml_into_dataclass(app_settings_path, AppSettings)
    _settings = Settings(app_settings=app_settings)
    _frozen = True

def get_settings() -> Settings:
    if _settings is None:
        raise ValueError("Settings have not been set. Call init_settings() first.")
    return _settings