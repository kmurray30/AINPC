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
        return self.project_path / "saves" / f"v{self.version}" / self.save_name

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
        """Get NPC template path with fallback to default"""
        npc_specific_path = self.npcs_templates_dir / npc_name / "template.yaml"
        if npc_specific_path.exists():
            return npc_specific_path
        # Fallback to default template
        return self.npcs_templates_dir / "default" / "template.yaml"

    def npc_entities_template(self, npc_name: str) -> Path:
        """Get NPC entities template path with fallback to default"""
        npc_specific_path = self.npcs_templates_dir / npc_name / "entities.yaml"
        if npc_specific_path.exists():
            return npc_specific_path
        # Fallback to default entities
        return self.npcs_templates_dir / "default" / "entities.yaml"
    
    def load_npc_template_with_fallback(self, npc_name: str, template_class):
        """Load NPC template with field-level fallback to default template"""
        from src.utils import io_utils
        
        # Load default template first
        default_path = self.npcs_templates_dir / "default" / "template.yaml"
        default_template = None
        if default_path.exists():
            try:
                default_template = io_utils.load_yaml_into_dataclass(default_path, template_class)
            except Exception:
                pass  # If default fails, we'll just use NPC-specific
        
        # Load NPC-specific template
        npc_specific_path = self.npcs_templates_dir / npc_name / "template.yaml"
        if npc_specific_path.exists():
            npc_template = io_utils.load_yaml_into_dataclass(npc_specific_path, template_class)
            
            # If we have a default template, merge fields
            if default_template:
                # For each field in the template class, use NPC-specific if present, otherwise default
                merged_data = {}
                for field_name in template_class.__dataclass_fields__.keys():
                    npc_value = getattr(npc_template, field_name, None)
                    default_value = getattr(default_template, field_name, None)
                    
                    # Use NPC-specific value if it exists and is not None, otherwise use default
                    if npc_value is not None:
                        merged_data[field_name] = npc_value
                    elif default_value is not None:
                        merged_data[field_name] = default_value
                
                return template_class(**merged_data)
            else:
                return npc_template
        elif default_template:
            # Only default template exists
            return default_template
        else:
            # Neither exists, let the original method handle the error
            return io_utils.load_yaml_into_dataclass(npc_specific_path, template_class)

    @property
    def chat_log(self) -> Path:
        return self.save_dir / "chat_log.yaml"

    def npc_save_state(self, npc_name: str) -> Path:
        return self.npc_save_dir(npc_name) / f"npc_save_state_v{self.version}.yaml"

    def npc_entities_save(self, npc_name: str) -> Path:
        return self.npc_save_dir(npc_name) / "entities.yaml"

    @property
    def list_npc_names(self) -> List[str]:
        return [path.name for path in self.npcs_templates_dir.iterdir() if path.is_dir() and path.name != "default"]

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