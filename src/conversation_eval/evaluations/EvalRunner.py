import os
import sys
from pathlib import Path
from typing import Dict, Type, Tuple

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.npcs.npc1.npc1 import NPC1
from src.npcs.npc2.npc2 import NPC2
from src.core import proj_paths, proj_settings


class EvalRunner:
    """Helper class for running NPC-backed evaluations"""
    
    # NPC type mapping
    NPC_TYPES = {
        "npc1": (NPC1, 1.0),
        "npc2": (NPC2, 2.0)
    }
    
    @classmethod
    def parse_args_and_setup_npc(cls, eval_dir: Path, npc_name: str = "assistant", save_enabled: bool = False):
        """Parse CLI arguments and set up NPC environment"""
        
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
        
        # Setup paths
        proj_paths.set_paths(
            project_path=eval_dir,
            templates_dir_name="default",
            version=version,
            save_name="eval_test"
        )
        
        proj_settings.init_settings(eval_dir / "templates" / "default" / "game_settings.yaml")
        
        # Create NPC instance
        npc = npc_class(npc_name_for_template_and_save=npc_name, save_enabled=save_enabled)
        
        return npc, npc_type
    
    @classmethod
    def get_npc_type_from_args(cls) -> str:
        """Get NPC type from command line arguments without full setup"""
        if len(sys.argv) != 2:
            return "unknown"
        return sys.argv[1].lower()
