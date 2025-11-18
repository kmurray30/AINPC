#!/usr/bin/env python3
"""
Test script to reproduce the NPC factory bug - settings not initialized
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.npcs.npc0.npc0 import NPC0
from src.npcs.npc1.npc1 import NPC1, NPCTemplate
from src.core import proj_paths
from src.core.schemas.CollectionSchemas import Entity
from src.utils import Utilities

# Setup paths (simulating what run_tests.py does)
eval_dir = Path(__file__).parent / "src/conversation_eval/evaluations/memory_wipe_tests"
templates_dir = eval_dir / "templates" / "default"

proj_paths.set_paths(
    project_path=eval_dir,
    templates_dir_name=templates_dir.name,
    version=0.1,
    save_name="test_repro"
)

print("✅ proj_paths initialized successfully")

# Test NPC0 (should work - doesn't need settings)
print("\n🧪 Testing NPC0...")
try:
    npc0 = NPC0(system_prompt="You are a test assistant")
    print("✅ NPC0 created successfully")
except Exception as e:
    print(f"❌ NPC0 failed: {e}")

# Test NPC1 (should fail - needs settings)
print("\n🧪 Testing NPC1...")
try:
    npc1 = NPC1(npc_name_for_template_and_save="assistant", save_enabled=False)
    print("✅ NPC1 created successfully")
except Exception as e:
    print(f"❌ NPC1 failed: {e}")

print("\n📋 Summary:")
print("Expected: NPC0 works, NPC1 fails with 'Settings have not been set'")

