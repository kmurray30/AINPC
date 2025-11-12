import os
import sys
from pathlib import Path
from typing import Dict, Type, Tuple

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.npcs.npc0.npc0 import NPC0
from src.npcs.npc1.npc1 import NPC1
from src.npcs.npc2.npc2 import NPC2
from src.core import proj_paths, proj_settings
from src.conversation_eval.InitialState import InitialStateLoader
from src.core.schemas.CollectionSchemas import Entity
from src.utils import Utilities


class EvalRunner:
    """Helper class for running NPC-backed evaluations"""
    
    # NPC type mapping
    NPC_TYPES = {
        "npc0": (NPC0, 0.1),
        "npc1": (NPC1, 1.0),
        "npc2": (NPC2, 2.0)
    }
    
    @classmethod
    def parse_args_and_setup_npc(cls, eval_dir: Path, npc_name: str = "assistant", save_enabled: bool = False, initial_state_file: str = None):
        """Parse CLI arguments and set up NPC environment with optional initial state"""
        
        # Get NPC type from command line
        if len(sys.argv) != 2:
            print("Usage: python eval.py <npc_type>")
            print(f"Available NPC types: {list(cls.NPC_TYPES.keys())}")
            exit(1)

        npc_type = sys.argv[1].lower()
        if npc_type not in cls.NPC_TYPES:
            print(f"Unknown NPC type: {npc_type}. Available types: {list(cls.NPC_TYPES.keys())}")
            exit(1)

        npc_class, version = cls.NPC_TYPES[npc_type]
        
        # Setup paths - use robust path handling that works regardless of folder names
        templates_dir = cls._find_templates_dir(eval_dir)
        
        # Only set paths if not already initialized (for multi-test runs)
        try:
            proj_paths.get_paths()
            # Paths already initialized, skip set_paths
        except ValueError:
            # Paths not initialized yet, set them
            proj_paths.set_paths(
                project_path=eval_dir,
                templates_dir_name=templates_dir.name,
                version=version,
                save_name="eval_test"
            )
        
        # Initialize settings if game_settings.yaml exists (skip if already initialized)
        settings_path = templates_dir / "game_settings.yaml"
        if settings_path.exists():
            try:
                proj_settings.init_settings(settings_path)
            except RuntimeError:
                # Settings already initialized, skip
                pass
        
        # Create NPC instance
        if npc_type == "npc0":
            # NPC0 needs a system prompt from template
            template_path = templates_dir / "npcs" / npc_name / "template.yaml"
            if template_path.exists():
                from src.npcs.npc1.npc1 import NPCTemplate  # Reuse the template class
                template = proj_paths.get_paths().load_npc_template_with_fallback(npc_name, NPCTemplate)
                npc = npc_class(system_prompt=template.system_prompt)
                # Load entities from template if they exist
                if template.entities:
                    npc.brain_entities = [
                        Entity(key=e, content=e, tags=["memories"], id=int(Utilities.generate_hash_int64(e)))
                        for e in template.entities
                    ]
            else:
                npc = npc_class()
        else:
            npc = npc_class(npc_name_for_template_and_save=npc_name, save_enabled=save_enabled)
        
        # Apply initial state if specified
        if initial_state_file:
            initial_state_path = eval_dir / initial_state_file
            if initial_state_path.exists():
                InitialStateLoader.load_and_apply(initial_state_path, npc)
        
        return npc, npc_type
    
    @classmethod
    def _find_templates_dir(cls, eval_dir: Path) -> Path:
        """Find templates directory robustly regardless of naming"""
        templates_dir = eval_dir / "templates"
        if templates_dir.exists():
            # Look for subdirectories in templates
            subdirs = [d for d in templates_dir.iterdir() if d.is_dir()]
            if subdirs:
                return subdirs[0]  # Use first subdirectory found
            return templates_dir
        
        # Fallback: look for any directory with 'template' in the name
        for item in eval_dir.iterdir():
            if item.is_dir() and 'template' in item.name.lower():
                return item
        
        # Last resort: create default structure
        default_templates = eval_dir / "templates" / "default"
        default_templates.mkdir(parents=True, exist_ok=True)
        return default_templates
    
    @classmethod
    def get_npc_type_from_args(cls) -> str:
        """Get NPC type from command line arguments without full setup"""
        if len(sys.argv) != 2:
            return "unknown"
        return sys.argv[1].lower()
