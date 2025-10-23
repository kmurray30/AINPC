import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List

# Ensure src/ is on sys.path
import sys
PROJ_ROOT = Path(__file__).resolve().parents[3]
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

from src.npcs.npc1.npc1 import NPC1, NPCTemplate
from src.core.ResponseTypes import ChatResponse
from src.core.schemas.CollectionSchemas import Entity
from src.core.Constants import Role


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create directory structure
        (temp_path / "templates" / "test_templates" / "npcs" / "test_npc").mkdir(parents=True, exist_ok=True)
        (temp_path / "templates" / "test_templates" / "npcs" / "test_npc2").mkdir(parents=True, exist_ok=True)
        (temp_path / "saves" / "test_save").mkdir(parents=True, exist_ok=True)
        
        # Create template file
        template_content = """
initial_system_context: "You are a helpful test assistant."
initial_response: "Hello! How can I help you?"
summarization_prompt: "Please summarize the conversation."
"""
        (temp_path / "templates" / "test_templates" / "npcs" / "test_npc" / "template_v1.0.yaml").write_text(template_content)
        (temp_path / "templates" / "test_templates" / "npcs" / "test_npc2" / "template_v1.0.yaml").write_text(template_content)
        
        # Create entities file
        entities_content = """
- "Test entity 1"
- "Test entity 2"
- "Test entity 3"
"""
        (temp_path / "templates" / "test_templates" / "npcs" / "test_npc" / "entities.yaml").write_text(entities_content)
        (temp_path / "templates" / "test_templates" / "npcs" / "test_npc2" / "entities.yaml").write_text(entities_content)
        
        # Create game settings
        game_settings_content = """
max_convo_mem_length: 10
num_last_messages_to_retain_when_summarizing: 5
log_level: DEBUG
model: gpt_4o_mini
game_title: "Test Game"
text_stream_speed: 0.05
closing_enabled: true
"""
        (temp_path / "templates" / "test_templates" / "game_settings.yaml").write_text(game_settings_content)
        
        yield temp_path


@pytest.fixture
def mock_agent():
    """Mock Agent class"""
    with patch('src.npcs.npc1.npc1.Agent') as mock_agent_class:
        def factory(*args, **kwargs):
            m = Mock()
            m.chat_with_history.return_value = ChatResponse(
                hidden_thought_process="test thoughts",
                response="test response",
                off_switch=False
            )
            m.update_system_prompt.return_value = None
            return m
        mock_agent_class.side_effect = factory
        yield mock_agent_class


@pytest.fixture
def mock_io_utils():
    """Mock io_utils"""
    with patch('src.npcs.npc1.npc1.io_utils') as mock_io:
        def mock_load_yaml(path, data_type):
            if "entities" in str(path):
                return ["Test entity 1", "Test entity 2", "Test entity 3"]
            elif "template" in str(path):
                return NPCTemplate(
                    system_prompt="You are a helpful test assistant.",
                    initial_response="Hello! How can I help you?"
                )
            elif "npc_save_state" in str(path):
                # Mock NPCState for loading saved state
                from src.npcs.npc1.npc1 import NPCState
                from src.core.schemas.CollectionSchemas import Entity
                mock_state = NPCState(
                    conversation_memory=Mock(),
                    user_prompt_wrapper="Test wrapper",
                    brain_entities=[Entity(key="test", content="test", tags=["test"], id=1)]
                )
                return mock_state
            else:
                return None
        
        mock_io.load_yaml_into_dataclass.side_effect = mock_load_yaml
        mock_io.save_to_yaml_file.return_value = None
        yield mock_io


@pytest.fixture
def mock_proj_paths(temp_project_dir):
    """Mock proj_paths to return our temp directory"""
    with patch('src.core.proj_paths.get_paths') as mock_get_paths:
        mock_paths = Mock()
        mock_paths.npc_template.return_value = temp_project_dir / "templates" / "test_templates" / "npcs" / "test_npc" / "template_v1.0.yaml"
        mock_paths.npc_entities_template.return_value = temp_project_dir / "templates" / "test_templates" / "npcs" / "test_npc" / "entities.yaml"
        mock_paths.save_dir = temp_project_dir / "saves" / "test_save"
        mock_paths.npc_save_dir.return_value = temp_project_dir / "saves" / "test_save" / "npcs" / "test_npc"
        mock_paths.npc_save_state.return_value = temp_project_dir / "saves" / "test_save" / "npcs" / "test_npc" / "npc_save_state_v1.0.yaml"
        
        # Mock the template loading method to return our test template
        def mock_load_template_with_fallback(npc_name, template_class):
            return NPCTemplate(
                system_prompt="You are a helpful test assistant.",
                initial_response="Hello! How can I help you?"
            )
        mock_paths.load_npc_template_with_fallback = mock_load_template_with_fallback
        
        mock_get_paths.return_value = mock_paths
        yield mock_paths


@pytest.fixture
def mock_proj_settings():
    """Mock proj_settings"""
    with patch('src.core.proj_settings.get_settings') as mock_get_settings:
        mock_settings = Mock()
        game_settings = Mock()
        game_settings.max_convo_mem_length = 10
        game_settings.num_last_messages_to_retain_when_summarizing = 5
        game_settings.log_level = "DEBUG"
        game_settings.model = "gpt_4o_mini"
        mock_settings.app_settings = game_settings
        mock_get_settings.return_value = mock_settings
        
        yield mock_settings


@pytest.fixture
def mock_global_config():
    """Mock global config loading"""
    def mock_load_global_config(self, config_filename):
        if "summarization_prompt" in config_filename:
            return {"summarization_prompt": "Please summarize the following conversation, focusing on key events and character development:"}
        return {}
    
    with patch.object(NPC1, '_load_global_config', mock_load_global_config):
        yield

@pytest.fixture
def mock_conversation_memory():
    """Mock ConversationMemory to avoid proj_settings dependency"""
    with patch('src.npcs.npc1.npc1.ConversationMemory') as mock_cm:
        mock_instance = Mock()
        mock_instance.chat_memory = []
        
        def mock_append_chat(content, role=None, cot=None, off_switch=False):
            mock_instance.chat_memory.append(Mock(content=content, role=role, cot=cot, off_switch=off_switch))
        
        mock_instance.append_chat = mock_append_chat
        mock_instance.maintain.return_value = None
        mock_instance.get_chat_summary_as_string.return_value = "Test summary"
        mock_instance.get_state.return_value = Mock()
        
        mock_cm.from_new.return_value = mock_instance
        mock_cm.from_state.return_value = mock_instance
        yield mock_cm


@pytest.fixture
def npc_instance(temp_project_dir, mock_agent, mock_io_utils, mock_proj_paths, mock_proj_settings, mock_conversation_memory):
    """Create an NPC instance for testing"""
    # Reset proj_paths singleton state
    from src.core import proj_paths
    import src.core.proj_paths as proj_paths_module
    
    # Reset the singleton state
    proj_paths_module._paths = None
    proj_paths_module._frozen = False
    
    # Set up paths
    proj_paths.set_paths(
        project_path=temp_project_dir,
        templates_dir_name="test_templates", 
        version=1.0,
        save_name="test_save"
    )
    
    # Create NPC instance with saving enabled by default
    npc = NPC1(npc_name_for_template_and_save="test_npc", save_enabled=True)
    return npc


class TestNPCInitialization:
    """Test NPC initialization and basic setup"""
    
    def test_npc_initialization(self, npc_instance):
        """Test that NPC initializes correctly"""
        assert npc_instance.npc_name == "test_npc"
        assert npc_instance.save_enabled is True  # Default for tests
        assert npc_instance.conversation_memory is not None
        assert npc_instance.response_agent is not None
        assert npc_instance.template is not None
        assert npc_instance.brain_entities is not None
    
    def test_template_loading(self, npc_instance):
        """Test that template is loaded correctly"""
        assert npc_instance.template.system_prompt == "You are a helpful test assistant."
        assert npc_instance.template.initial_response == "Hello! How can I help you?"
        # Note: summarization_prompt is now loaded from global config
        assert npc_instance.summarization_prompt is not None


class TestNPCStateManagement:
    """Test NPC state saving, loading, and initialization"""
    
    def test_init_state(self, npc_instance):
        """Test that state is initialized correctly for new game"""
        npc_instance._init_state()
        assert npc_instance.conversation_memory is not None
        assert npc_instance.brain_entities is not None
    
    def test_save_state(self, npc_instance, mock_io_utils, mock_proj_paths):
        """Test that state is saved correctly"""
        npc_instance._save_state()
        # Since save is enabled by default, should be called
        mock_io_utils.save_to_yaml_file.assert_called_once()
    
    def test_load_state_file_not_found(self, npc_instance, mock_io_utils, mock_proj_paths):
        """Test that state loading handles missing files gracefully"""
        mock_io_utils.load_yaml_into_dataclass.side_effect = FileNotFoundError("File not found")
        # This should not be called with save_enabled=False, but test the method directly
        try:
            npc_instance._load_state()
        except FileNotFoundError:
            pass  # Expected when file doesn't exist


class TestNPCConversationMemory:
    """Test NPC conversation memory functionality"""
    
    def test_inject_message(self, npc_instance):
        """Test that messages can be injected into conversation memory"""
        npc_instance.inject_message("Test message", role=Role.user)
        assert len(npc_instance.conversation_memory.chat_memory) == 1
        assert npc_instance.conversation_memory.chat_memory[0].content == "Test message"
    
    def test_maintain(self, npc_instance, mock_io_utils):
        """Test that maintain works correctly"""
        npc_instance.maintain()
        # Should call conversation memory maintain and save state (save enabled)
        npc_instance.conversation_memory.maintain.assert_called_once()
        mock_io_utils.save_to_yaml_file.assert_called_once()


class TestNPCSystemPrompt:
    """Test NPC system prompt building"""
    
    def test_build_system_prompt_basic(self, npc_instance):
        """Test basic system prompt building"""
        # Set up some test entities
        npc_instance.brain_entities = [
            Entity(key="test1", content="Test entity 1", tags=["test"], id=1),
            Entity(key="test2", content="Test entity 2", tags=["test"], id=2)
        ]
        
        prompt = npc_instance._build_system_prompt()
        assert "You are a helpful test assistant." in prompt
        assert "Test entity 1" in prompt
        assert "Test entity 2" in prompt
        assert "Test summary" in prompt  # From mocked conversation memory


class TestNPCBrainMemory:
    """Test NPC brain memory (entity) functionality"""
    
    def test_get_all_memories(self, npc_instance):
        """Test getting all memories"""
        # Set up test entities
        test_entities = [
            Entity(key="test1", content="Test entity 1", tags=["test"], id=1),
            Entity(key="test2", content="Test entity 2", tags=["test"], id=2)
        ]
        npc_instance.brain_entities = test_entities
        
        memories = npc_instance.get_all_memories()
        assert len(memories) == 2
        assert all(isinstance(memory, Entity) for memory in memories)
        assert memories[0].content == "Test entity 1"
        assert memories[1].content == "Test entity 2"
    
    def test_clear_brain_memory(self, npc_instance):
        """Test clearing brain memory"""
        # Set up test entities
        npc_instance.brain_entities = [Entity(key="test", content="Test", tags=["test"], id=1)]
        
        npc_instance.clear_brain_memory()
        assert len(npc_instance.brain_entities) == 0


class TestNPCChatFunctionality:
    """Test NPC chat functionality"""
    
    def test_chat_flow(self, npc_instance, mock_agent):
        """Test basic chat flow"""
        result = npc_instance.chat("Hello")
        
        assert isinstance(result, ChatResponse)
        assert result.response == "test response"
        assert len(npc_instance.conversation_memory.chat_memory) == 2  # user + assistant
        npc_instance.response_agent.update_system_prompt.assert_called_once()
    
    def test_chat_flow_no_user_message(self, npc_instance, mock_agent):
        """Test chat flow without user message"""
        result = npc_instance.chat(None)
        assert isinstance(result, ChatResponse)
        assert result.response == "test response"
        # Should only have assistant message since no user message was provided
        assert len(npc_instance.conversation_memory.chat_memory) == 1


class TestNPCSaveFeature:
    """Test NPC save feature with save_enabled flag"""
    
    def test_npc1_with_save_enabled_true(self, temp_project_dir, mock_agent, mock_io_utils, mock_proj_paths, mock_proj_settings, mock_conversation_memory, mock_global_config):
        """Test NPC1 with save_enabled=True"""
        from src.core import proj_paths
        import src.core.proj_paths as proj_paths_module
        
        # Reset proj_paths singleton state
        proj_paths_module._paths = None
        proj_paths_module._frozen = False
        proj_paths.set_paths(
            project_path=temp_project_dir,
            templates_dir_name="test_templates", 
            version=1.0,
            save_name="test_save"
        )
        
        # Create NPC with saving enabled
        npc = NPC1(npc_name_for_template_and_save="test_npc", save_enabled=True)
        
        assert npc.save_enabled is True
        
        # Test that _save_state actually calls save operations
        npc._save_state()
        mock_io_utils.save_to_yaml_file.assert_called_once()
        
        # Test that maintain calls save operations
        mock_io_utils.save_to_yaml_file.reset_mock()
        npc.maintain()
        mock_io_utils.save_to_yaml_file.assert_called_once()
    
    def test_npc1_with_save_enabled_false(self, temp_project_dir, mock_agent, mock_io_utils, mock_proj_paths, mock_proj_settings, mock_conversation_memory, mock_global_config):
        """Test NPC1 with save_enabled=False"""
        from src.core import proj_paths
        import src.core.proj_paths as proj_paths_module
        
        # Reset proj_paths singleton state
        proj_paths_module._paths = None
        proj_paths_module._frozen = False
        proj_paths.set_paths(
            project_path=temp_project_dir,
            templates_dir_name="test_templates", 
            version=1.0,
            save_name="test_save"
        )
        
        # Create NPC with saving disabled
        npc = NPC1(npc_name_for_template_and_save="test_npc", save_enabled=False)
        
        assert npc.save_enabled is False
        
        # Test that _save_state does NOT call save operations
        npc._save_state()
        mock_io_utils.save_to_yaml_file.assert_not_called()
        
        # Test that maintain does NOT call save operations
        npc.maintain()
        mock_io_utils.save_to_yaml_file.assert_not_called()
    
    def test_npc1_save_state_file_operations(self, temp_project_dir):
        """Test actual file operations with real temp directory"""
        from src.core import proj_paths, proj_settings
        import src.core.proj_paths as proj_paths_module
        
        # Reset proj_paths singleton state
        proj_paths_module._paths = None
        proj_paths_module._frozen = False
        
        # Create necessary template files
        templates_dir = temp_project_dir / "templates" / "test_templates"
        npcs_dir = templates_dir / "npcs" / "test_npc"
        npcs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default template directory
        default_npcs_dir = templates_dir / "npcs" / "default"
        default_npcs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create template file
        template_content = """system_prompt: "You are a helpful test assistant."
initial_response: "Hello! How can I help you?"
"""
        (npcs_dir / "template.yaml").write_text(template_content)
        (default_npcs_dir / "template.yaml").write_text(template_content)  # Default fallback
        
        # Create entities file
        entities_content = """- "Test entity 1"
- "Test entity 2"
"""
        (npcs_dir / "entities.yaml").write_text(entities_content)
        (default_npcs_dir / "entities.yaml").write_text(entities_content)  # Default fallback
        
        # Create game settings file
        game_settings_content = """max_convo_mem_length: 10
num_last_messages_to_retain_when_summarizing: 5
log_level: DEBUG
model: gpt_4o_mini
game_title: "Test Game"
text_stream_speed: 0.05
closing_enabled: true
"""
        (templates_dir / "game_settings.yaml").write_text(game_settings_content)
        
        # Set up real paths
        proj_paths.set_paths(
            project_path=temp_project_dir,
            templates_dir_name="test_templates",
            version=1.0,
            save_name="test_save"
        )
        
        # Initialize settings
        proj_settings.init_settings(temp_project_dir / "templates" / "test_templates" / "game_settings.yaml")
        
        # Mock global config loading for this test
        def mock_load_global_config(self, config_filename):
            if "summarization_prompt" in config_filename:
                return {"summarization_prompt": "Please summarize the following conversation, focusing on key events and character development:"}
            return {}
        
        with patch.object(NPC1, '_load_global_config', mock_load_global_config):
            # Test with save_enabled=True - should create files
            npc_save_enabled = NPC1(npc_name_for_template_and_save="test_npc", save_enabled=True)
            npc_save_enabled._save_state()
            
            # Check that save file was created
            save_file_path = temp_project_dir / "saves" / "v1.0" / "test_save" / "npcs" / "test_npc" / "npc_save_state_v1.0.yaml"
            assert save_file_path.exists(), f"Save file should exist at {save_file_path}"
            
            # Test with save_enabled=False - should NOT create files
            npc_save_disabled = NPC1(npc_name_for_template_and_save="test_npc2", save_enabled=False)
            npc_save_disabled._save_state()
            
            # Check that save file was NOT created
            save_file_path_disabled = temp_project_dir / "saves" / "v1.0" / "test_save" / "npcs" / "test_npc2" / "npc_save_state_v1.0.yaml"
            assert not save_file_path_disabled.exists(), f"Save file should NOT exist at {save_file_path_disabled}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
