from dataclasses import dataclass
from typing import Optional
from pathlib import Path

@dataclass (frozen=True)
class SavePaths:
    project_path: Path
    save_name: str
    npc_name: str

    @property
    def game_settings(self) -> Path:
        return self.project_path / "game_settings.yaml"

    @property
    def save_root(self) -> Path:
        return self.project_path / "saves" / self.save_name

    @property
    def npc_save_root(self) -> Path:
        return self.save_root / "npcs" / self.npc_name

    @property
    def audio_dir(self) -> Path:
        return self.npc_save_root / "audio"

    @property
    def npc_save_state(self) -> Path:
        return self.npc_save_root / "npc_save_state.yaml"

    @property
    def chat_log(self) -> Path:
        return self.npc_save_root / "chat_log.yaml"

    @property
    def npc_template(self) -> Path:
        return self.project_path / "npcs" / self.npc_name / "template.yaml"

# Singleton instance
_paths: Optional[SavePaths] = None
_frozen: bool = False

def set_paths(project_path: Path, save_name: str, npc_name: str) -> None:
    global _paths, _frozen
    if _frozen:
        raise RuntimeError("Paths have already been initialized and cannot be modified.")
    _paths = SavePaths(project_path=project_path, save_name=save_name, npc_name=npc_name)
    _frozen = True

def get_paths() -> SavePaths:
    if _paths is None:
        raise ValueError("Paths have not been set. Call set_paths() first.")
    return _paths