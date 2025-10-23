import pytest
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.core.proj_paths import SavePaths


@dataclass
class MockNPCTemplate:
    """Mock template class for fallback testing"""
    system_prompt: str
    initial_response: Optional[str] = None


class TestProjPathsFallback:
    """Test the NPC template fallback system"""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory with test templates"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create directory structure
            default_dir = temp_path / "templates" / "default" / "npcs" / "default"
            assistant_dir = temp_path / "templates" / "default" / "npcs" / "assistant"
            test_npc_dir = temp_path / "templates" / "default" / "npcs" / "test_npc"
            
            default_dir.mkdir(parents=True, exist_ok=True)
            assistant_dir.mkdir(parents=True, exist_ok=True)
            test_npc_dir.mkdir(parents=True, exist_ok=True)
            
            # Create default template (has all fields)
            default_template = """system_prompt: "Default system prompt"
initial_response: "Default initial response"
"""
            (default_dir / "template.yaml").write_text(default_template)
            
            # Create assistant template (overrides system_prompt only)
            assistant_template = """system_prompt: "Assistant-specific system prompt"
"""
            (assistant_dir / "template.yaml").write_text(assistant_template)
            
            # Create entities files
            default_entities = """- "Default entity 1"
- "Default entity 2"
"""
            assistant_entities = """- "Assistant entity 1"
- "Assistant entity 2"
"""
            
            (default_dir / "entities.yaml").write_text(default_entities)
            (assistant_dir / "entities.yaml").write_text(assistant_entities)
            
            # Create game settings
            game_settings = """max_convo_mem_length: 10
log_level: INFO
model: gpt_4o_mini
"""
            (temp_path / "templates" / "default" / "game_settings.yaml").write_text(game_settings)
            
            yield temp_path
    
    def test_fallback_template_loading_with_override(self, temp_project_dir):
        """Test that NPC-specific fields override default fields"""
        save_paths = SavePaths(
            project_path=temp_project_dir,
            templates_dir_name="default",
            version="2.0",
            save_name="test"
        )
        
        # Load assistant template (should merge with default)
        template = save_paths.load_npc_template_with_fallback("assistant", MockNPCTemplate)
        
        # Should have assistant-specific system prompt
        assert template.system_prompt == "Assistant-specific system prompt"
        
        # Should have default value for initial_response
        assert template.initial_response == "Default initial response"
    
    def test_fallback_template_loading_default_only(self, temp_project_dir):
        """Test loading when only default template exists"""
        save_paths = SavePaths(
            project_path=temp_project_dir,
            templates_dir_name="default",
            version="2.0",
            save_name="test"
        )
        
        # Load template for NPC that doesn't have specific template
        template = save_paths.load_npc_template_with_fallback("test_npc", MockNPCTemplate)
        
        # Should have all default values
        assert template.system_prompt == "Default system prompt"
        assert template.initial_response == "Default initial response"
    
    def test_fallback_template_loading_npc_specific_only(self, temp_project_dir):
        """Test loading when only NPC-specific template exists (no default)"""
        save_paths = SavePaths(
            project_path=temp_project_dir,
            templates_dir_name="default",
            version="2.0",
            save_name="test"
        )
        
        # Remove default template
        (temp_project_dir / "templates" / "default" / "npcs" / "default" / "template.yaml").unlink()
        
        # Load assistant template (should work without default)
        template = save_paths.load_npc_template_with_fallback("assistant", MockNPCTemplate)
        
        # Should have assistant-specific system prompt
        assert template.system_prompt == "Assistant-specific system prompt"
        
        # Other fields should be None (dataclass defaults)
        assert template.initial_response is None
    
    def test_npc_template_path_fallback(self, temp_project_dir):
        """Test that npc_template() method falls back to default"""
        save_paths = SavePaths(
            project_path=temp_project_dir,
            templates_dir_name="default",
            version="2.0",
            save_name="test"
        )
        
        # For assistant (has specific template)
        assistant_path = save_paths.npc_template("assistant")
        expected_assistant = temp_project_dir / "templates" / "default" / "npcs" / "assistant" / "template.yaml"
        assert assistant_path == expected_assistant
        assert assistant_path.exists()
        
        # For test_npc (no specific template, should fallback to default)
        test_npc_path = save_paths.npc_template("test_npc")
        expected_default = temp_project_dir / "templates" / "default" / "npcs" / "default" / "template.yaml"
        assert test_npc_path == expected_default
        assert test_npc_path.exists()
    
    def test_npc_entities_template_fallback(self, temp_project_dir):
        """Test that npc_entities_template() method falls back to default"""
        save_paths = SavePaths(
            project_path=temp_project_dir,
            templates_dir_name="default",
            version="2.0",
            save_name="test"
        )
        
        # For assistant (has specific entities)
        assistant_entities = save_paths.npc_entities_template("assistant")
        expected_assistant = temp_project_dir / "templates" / "default" / "npcs" / "assistant" / "entities.yaml"
        assert assistant_entities == expected_assistant
        assert assistant_entities.exists()
        
        # For test_npc (no specific entities, should fallback to default)
        test_npc_entities = save_paths.npc_entities_template("test_npc")
        expected_default = temp_project_dir / "templates" / "default" / "npcs" / "default" / "entities.yaml"
        assert test_npc_entities == expected_default
        assert test_npc_entities.exists()
    
    def test_fallback_with_missing_fields_in_npc_template(self, temp_project_dir):
        """Test fallback when NPC template has some fields missing"""
        save_paths = SavePaths(
            project_path=temp_project_dir,
            templates_dir_name="default",
            version="2.0",
            save_name="test"
        )
        
        # Create a partial NPC template
        partial_dir = temp_project_dir / "templates" / "default" / "npcs" / "partial_npc"
        partial_dir.mkdir(parents=True, exist_ok=True)
        
        partial_template = """system_prompt: "Partial system prompt"
# Missing initial_response
"""
        (partial_dir / "template.yaml").write_text(partial_template)
        
        # Load template
        template = save_paths.load_npc_template_with_fallback("partial_npc", MockNPCTemplate)
        
        # Should have NPC-specific system prompt
        assert template.system_prompt == "Partial system prompt"
        
        # Should fall back to default for missing fields
        assert template.initial_response == "Default initial response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
