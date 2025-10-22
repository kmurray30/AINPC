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
    response_system_prompt: str
    preprocess_system_prompt: Optional[str] = None
    summarization_prompt: Optional[str] = None


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
            default_template = """response_system_prompt: "Default response prompt"
preprocess_system_prompt: "Default preprocess prompt"
summarization_prompt: "Default summary prompt"
"""
            (default_dir / "template_v2.0.yaml").write_text(default_template)
            
            # Create assistant template (overrides response_system_prompt only)
            assistant_template = """response_system_prompt: "Assistant-specific response prompt"
"""
            (assistant_dir / "template_v2.0.yaml").write_text(assistant_template)
            
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
        
        # Should have assistant-specific response prompt
        assert template.response_system_prompt == "Assistant-specific response prompt"
        
        # Should have default values for other fields
        assert template.preprocess_system_prompt == "Default preprocess prompt"
        assert template.summarization_prompt == "Default summary prompt"
    
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
        assert template.response_system_prompt == "Default response prompt"
        assert template.preprocess_system_prompt == "Default preprocess prompt"
        assert template.summarization_prompt == "Default summary prompt"
    
    def test_fallback_template_loading_npc_specific_only(self, temp_project_dir):
        """Test loading when only NPC-specific template exists (no default)"""
        save_paths = SavePaths(
            project_path=temp_project_dir,
            templates_dir_name="default",
            version="2.0",
            save_name="test"
        )
        
        # Remove default template
        (temp_project_dir / "templates" / "default" / "npcs" / "default" / "template_v2.0.yaml").unlink()
        
        # Load assistant template (should work without default)
        template = save_paths.load_npc_template_with_fallback("assistant", MockNPCTemplate)
        
        # Should have assistant-specific response prompt
        assert template.response_system_prompt == "Assistant-specific response prompt"
        
        # Other fields should be None (dataclass defaults)
        assert template.preprocess_system_prompt is None
        assert template.summarization_prompt is None
    
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
        expected_assistant = temp_project_dir / "templates" / "default" / "npcs" / "assistant" / "template_v2.0.yaml"
        assert assistant_path == expected_assistant
        assert assistant_path.exists()
        
        # For test_npc (no specific template, should fallback to default)
        test_npc_path = save_paths.npc_template("test_npc")
        expected_default = temp_project_dir / "templates" / "default" / "npcs" / "default" / "template_v2.0.yaml"
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
        
        partial_template = """response_system_prompt: "Partial response prompt"
# Missing preprocess_system_prompt and summarization_prompt
"""
        (partial_dir / "template_v2.0.yaml").write_text(partial_template)
        
        # Load template
        template = save_paths.load_npc_template_with_fallback("partial_npc", MockNPCTemplate)
        
        # Should have NPC-specific response prompt
        assert template.response_system_prompt == "Partial response prompt"
        
        # Should fall back to default for missing fields
        assert template.preprocess_system_prompt == "Default preprocess prompt"
        assert template.summarization_prompt == "Default summary prompt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
