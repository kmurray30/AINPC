from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

@dataclass (frozen=True)
class SavePaths:
    project_path: Path
    templates_dir_name: str
    version: float
    save_name: str

    @property
    def template_dir(self) -> Path:
        return self.project_path / "templates" / self.templates_dir_name

    @property
    def npcs_templates_dir(self) -> Path:
        return self.template_dir / "npcs"

    @property
    def save_dir(self) -> Path:
        return self.project_path / "saves" / self.save_name

    @property
    def audio_dir(self) -> Path:
        return self.save_dir / "audio"

    @property
    def npcs_saves_dir(self) -> Path:
        return self.save_dir / "npcs"

    def npc_save_dir(self, npc_name: str) -> Path:
        return self.save_dir / "npcs" / npc_name

    @property
    def app_settings(self) -> Path:
        return self.template_dir / "app_settings.yaml"

    def npc_template(self, npc_name: str) -> Path:
        return self.npcs_templates_dir / npc_name / f"template_v{self.version}.yaml"

    def npc_entities_template(self, npc_name: str) -> Path:
        return self.npcs_templates_dir / npc_name / "entities.yaml"

    @property
    def chat_log(self) -> Path:
        return self.save_dir / "chat_log.yaml"

    def npc_save_state(self, npc_name: str) -> Path:
        return self.npc_save_dir(npc_name) / f"npc_save_state_v{self.version}.yaml"

    def npc_entities_save(self, npc_name: str) -> Path:
        return self.npc_save_dir(npc_name) / "entities.yaml"

    @property
    def list_npc_names(self) -> List[str]:
        return [path.name for path in self.npcs_templates_dir.iterdir() if path.is_dir()]

# Singleton instance
_paths: Optional[SavePaths] = None
_frozen: bool = False

def set_paths(project_path: Path, templates_dir_name: str, version: str, save_name: str) -> None:
    global _paths, _frozen
    if _frozen:
        raise RuntimeError("Paths have already been initialized and cannot be modified.")
    _paths = SavePaths(project_path=project_path, templates_dir_name=templates_dir_name, version=version, save_name=save_name)
    _frozen = True

def get_paths() -> SavePaths:
    if _paths is None:
        raise ValueError("Paths have not been set. Call set_paths() first.")
    return _paths