from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

@dataclass (frozen=True)
class SavePaths:
    project_path: Path
    save_name: str

    @property
    def game_settings(self) -> Path:
        return self.project_path / "game_settings.yaml"

    @property
    def templates_root(self) -> Path:
        return self.project_path / "templates"

    @property
    def npc_templates_root(self) -> Path:
        return self.templates_root / "npcs"

    def npc_template(self, npc_name: str) -> Path:
        return self.npc_templates_root / npc_name / "template.yaml"

    def npc_entities_template(self, npc_name: str) -> Path:
        return self.npc_templates_root / npc_name / "entities.yaml"

    @property
    def save_root(self) -> Path:
        return self.project_path / "saves" / self.save_name

    @property
    def npc_save_root(self) -> Path:
        return self.save_root / "npcs"

    def npc_save(self, npc_name: str) -> Path:
        return self.npc_save_root / npc_name

    def audio_dir(self, npc_name: str) -> Path:
        return self.npc_save(npc_name) / "audio"

    def npc_save_state(self, npc_name: str) -> Path:
        return self.npc_save(npc_name) / "npc_save_state.yaml"

    def chat_log(self, npc_name: str) -> Path:
        return self.npc_save(npc_name) / "chat_log.yaml"

    def npc_entities_save(self, npc_name: str) -> Path:
        return self.npc_save(npc_name) / "entities.yaml"

    @property
    def get_npc_names(self) -> List[str]:
        return [path.name for path in self.npc_templates_root.iterdir() if path.is_dir()]

# Singleton instance
_paths: Optional[SavePaths] = None
_frozen: bool = False

def set_paths(project_path: Path, save_name: str) -> None:
    global _paths, _frozen
    if _frozen:
        raise RuntimeError("Paths have already been initialized and cannot be modified.")
    _paths = SavePaths(project_path=project_path, save_name=save_name)
    _frozen = True

def get_paths() -> SavePaths:
    if _paths is None:
        raise ValueError("Paths have not been set. Call set_paths() first.")
    return _paths