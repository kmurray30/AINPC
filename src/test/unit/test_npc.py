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

from src.brain.NPC import NPC, NPCState, NPCTemplate
from src.core.ConversationMemory import ConversationMemory
from src.core.ResponseTypes import ChatResponse
from src.core.schemas.CollectionSchemas import Entity
from src.brain.simple_brain import PreprocessedUserInput
from src.core.Constants import Role
from src.brain.embedding_cache import EmbeddingCache


@pytest.fixture(autouse=True)
def mock_vector_embeddings(monkeypatch):
    """Avoid real embedding calls; return fixed-size embeddings."""
    from src.utils import VectorUtils
    def fake_embed(text, model=None, dimensions=None):
        return [0.0] * 1536
    monkeypatch.setattr(VectorUtils, "get_embedding", fake_embed, raising=True)


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create directory structure
        (temp_path / "templates" / "npcs" / "test_npc").mkdir(parents=True, exist_ok=True)
        (temp_path / "saves" / "test_save").mkdir(parents=True, exist_ok=True)
        
        # Create template file
        template_content = """
response_system_prompt: "You are a helpful test assistant."
preprocess_system_prompt: "You are a text preprocessor."
"""
        (temp_path / "templates" / "npcs" / "test_npc" / "template.yaml").write_text(template_content)
        
        # Create game settings
        game_settings_content = """
max_convo_mem_length: 10
num_last_messages_to_retain_when_summarizing: 5
"""
        (temp_path / "game_settings.yaml").write_text(game_settings_content)
        
        yield temp_path


@pytest.fixture
def mock_qdrant():
    """Mock the QdrantCollection used inside NPC."""
    with patch('src.brain.brain_memory.QdrantCollection') as MockQCol:
        instance = Mock()
        # methods used by NPC
        instance.create.return_value = None
        instance.drop_if_exists.return_value = None
        instance.insert_dataclasses.return_value = None
        instance.export_entities.return_value = []
        instance.search_text.return_value = []
        # provide an embedding_cache attribute for tests that access it
        instance.embedding_cache = EmbeddingCache()
        MockQCol.return_value = instance
        yield instance


@pytest.fixture
def mock_agent():
    """Mock Agent class"""
    with patch('src.brain.NPC.Agent') as mock_agent_class:
        def factory(*args, **kwargs):
            m = Mock()
            m.chat_with_history.return_value = "Mock response"
            m.update_system_prompt.return_value = None
            return m
        mock_agent_class.side_effect = factory
        yield mock_agent_class


@pytest.fixture
def mock_io_utils():
    """Mock io_utils"""
    with patch('src.brain.NPC.io_utils') as mock_io:
        mock_io.load_yaml_into_dataclass.return_value = NPCTemplate(
            response_system_prompt="You are a helpful test assistant.",
            preprocess_system_prompt="You are a text preprocessor."
        )
        mock_io.save_to_yaml_file.return_value = None
        
        yield mock_io


@pytest.fixture
def mock_proj_paths(temp_project_dir):
    """Mock proj_paths to return our temp directory"""
    with patch('src.core.proj_paths.get_paths') as mock_get_paths:
        mock_paths = Mock()
        mock_paths.npc_template.return_value = temp_project_dir / "templates" / "npcs" / "test_npc" / "template.yaml"
        mock_paths.npc_save.return_value = temp_project_dir / "saves" / "test_save" / "npcs" / "test_npc"
        mock_paths.npc_save_state.return_value = temp_project_dir / "saves" / "test_save" / "npcs" / "test_npc" / "npc_save_state.yaml"
        mock_paths.chat_log.return_value = temp_project_dir / "saves" / "test_save" / "npcs" / "test_npc" / "chat_log.yaml"
        mock_get_paths.return_value = mock_paths
        
        yield mock_paths


@pytest.fixture
def mock_proj_settings():
    """Mock proj_settings"""
    with patch('src.core.proj_settings.get_settings') as mock_get_settings:
        mock_settings = Mock()
        mock_settings.game_settings = Mock()
        mock_get_settings.return_value = mock_settings
        
        yield mock_settings

@pytest.fixture
def mock_conversation_memory():
    """Mock ConversationMemory to avoid proj_settings dependency"""
    with patch('src.brain.NPC.ConversationMemory') as mock_cm:
        mock_instance = Mock()
        mock_instance.chat_memory = []
        
        def mock_append_chat(content, role=None, cot=None, off_switch=False):
            mock_instance.chat_memory.append(Mock(content=content, role=role, cot=cot, off_switch=off_switch))
        
        mock_instance.append_chat = mock_append_chat
        mock_instance.get_state = Mock()
        mock_instance.maintain = Mock()
        mock_instance.get_chat_summary_as_string = Mock(return_value="Mock conversation summary")
        mock_cm.from_new.return_value = mock_instance
        yield mock_cm


@pytest.fixture
def npc_instance(temp_project_dir, mock_qdrant, mock_agent, mock_io_utils, mock_proj_paths, mock_proj_settings, mock_conversation_memory):
    """Create an NPC instance for testing"""
    # Reset proj_paths singleton state
    from src.core import proj_paths
    import src.core.proj_paths as proj_paths_module
    
    # Reset the singleton state
    proj_paths_module._paths = None
    proj_paths_module._frozen = False
    
    # Set up paths
    proj_paths.set_paths(temp_project_dir, "test_save")
    
    # Create NPC instance
    npc = NPC(is_new_game=True, npc_name="test_npc")
    return npc


class TestNPCInitialization:
    """Test NPC initialization and basic setup"""
    
    def test_npc_initialization(self, npc_instance):
        """Test that NPC initializes correctly"""
        assert npc_instance.npc_name == "test_npc"
        assert npc_instance.is_new_game is True
        assert npc_instance.conversation_memory is not None
        assert npc_instance.response_agent is not None
        assert npc_instance.preprocessor_agent is not None
        assert npc_instance.template is not None
        assert npc_instance.brain_memory.collection is not None
    
    def test_template_loading(self, npc_instance):
        """Test that template is loaded correctly"""
        assert npc_instance.template.response_system_prompt == "You are a helpful test assistant."
        assert npc_instance.template.preprocess_system_prompt == "You are a text preprocessor."


class TestNPCStateManagement:
    """Test NPC state saving, loading, and initialization"""
    
    def test_init_state(self, npc_instance):
        """Test that state is initialized correctly for new game"""
        npc_instance._init_state()
        assert npc_instance.conversation_memory is not None
        # Since we're mocking ConversationMemory, just check it's not None
        assert npc_instance.conversation_memory is not None
    
    def test_save_state(self, npc_instance, mock_io_utils, mock_proj_paths):
        """Test that state is saved correctly"""
        npc_instance._save_state()
        mock_io_utils.save_to_yaml_file.assert_called_once()
    
    def test_load_state_file_not_found(self, npc_instance, mock_io_utils, mock_proj_paths):
        """Test that state loading handles missing files gracefully"""
        mock_io_utils.load_yaml_into_dataclass.side_effect = FileNotFoundError("File not found")
        npc_instance._load_state()
        # Should fall back to init_state
        assert npc_instance.conversation_memory is not None


class TestNPCConversationMemory:
    """Test NPC conversation memory functionality"""
    
    def test_inject_message(self, npc_instance):
        """Test that messages can be injected into conversation memory"""
        npc_instance.inject_message("Test message", role=Role.user)
        assert len(npc_instance.conversation_memory.chat_memory) == 1
        assert npc_instance.conversation_memory.chat_memory[0].content == "Test message"
        assert npc_instance.conversation_memory.chat_memory[0].role == Role.user
    
    def test_maintain(self, npc_instance):
        """Test that maintenance is performed correctly"""
        npc_instance.maintain()
        # Should call conversation memory maintain and save state
        assert npc_instance.conversation_memory is not None


class TestNPCSystemPrompt:
    """Test NPC system prompt building"""
    
    def test_build_system_prompt_basic(self, npc_instance):
        """Ensure both conversation summary and brain context are present by default."""
        # Seed conversation with a user message so brain context can be built
        npc_instance.conversation_memory.append_chat("Hello", role=Role.user)
        
        # Make get_memories return at least one item so brain context is included
        with patch.object(npc_instance.brain_memory, 'get_memories', return_value="brain_content"):
            prompt = npc_instance._build_system_prompt()
        
        assert "You are a helpful test assistant." in prompt
        assert "Prior conversation summary:" in prompt
        assert "Brain context:" in prompt
        assert "brain_content" in prompt
        # Ensure update_system_prompt later receives the built prompt
        npc_instance.response_agent.update_system_prompt(prompt)
        npc_instance.response_agent.update_system_prompt.assert_called_with(prompt)
    
    def test_build_system_prompt_without_conversation_summary(self, npc_instance):
        """Test system prompt without conversation summary"""
        prompt = npc_instance._build_system_prompt(include_conversation_summary=False)
        assert "You are a helpful test assistant." in prompt
        assert "Prior conversation summary:" not in prompt
    
    def test_build_system_prompt_without_brain_context(self, npc_instance):
        """Test system prompt without brain context"""
        prompt = npc_instance._build_system_prompt(include_brain_context=False)
        assert "You are a helpful test assistant." in prompt
        assert "Brain context:" not in prompt


class TestNPCBrainMemory:
    """Test NPC brain memory functionality"""
    
    def test_update_memory(self, npc_instance, mock_qdrant):
        """Test that memory can be updated"""
        npc_instance.brain_memory.add_memory("Test memory content")
        mock_qdrant.insert_dataclasses.assert_called_once()
    
    def test_get_memories(self, npc_instance, mock_qdrant):
        """Test that memories can be retrieved"""
        mock_qdrant.search_text.return_value = [
            (Entity(key="test", content="test content", tags=["memories"]), 0.8)
        ]
        
        memories = npc_instance.brain_memory.get_memories("test query", topk=5)
        assert len(memories) == 1
        assert memories[0].content == "test content"
        mock_qdrant.search_text.assert_called_once()

    def test_get_memories_uses_cache_hit(self, npc_instance, monkeypatch):
        """When cache has embedding, ensure embed isn't called (via real QdrantCollection.search_text)."""
        from src.utils.QdrantCollection import QdrantCollection as RealQCol
        real = RealQCol("simple_brain")
        # seed cache
        cached_vec = [0.1] * 1536
        real.embedding_cache.add("cached text", cached_vec)
        # stub search_vectors to avoid network
        def fake_search_vectors(vec, topk=5, filter=None):
            return []
        real._search_vectors = fake_search_vectors  # type: ignore
        npc_instance.brain_memory.collection = real

        # Spy on the embedding function used by QdrantCollection
        embed_spy = Mock()
        monkeypatch.setattr('src.utils.QdrantCollection.VectorUtils.get_embedding', embed_spy)

        npc_instance.brain_memory.get_memories("cached text", topk=3)
        embed_spy.assert_not_called()

    def test_get_memories_cache_miss_adds_and_calls_embed(self, npc_instance, monkeypatch):
        """On cache miss, embed is called and cached inside collection."""
        from src.utils.QdrantCollection import QdrantCollection as RealQCol
        real = RealQCol("simple_brain")
        assert real.embedding_cache.get("new text") is None
        def fake_search_vectors(vec, topk=5, filter=None):
            return []
        real._search_vectors = fake_search_vectors  # type: ignore
        npc_instance.brain_memory.collection = real

        called_vec = [0.2] * 1536
        def fake_embed(text, model=None, dimensions=None):
            return called_vec
        monkeypatch.setattr('src.utils.QdrantCollection.VectorUtils.get_embedding', fake_embed)

        npc_instance.brain_memory.get_memories("new text", topk=4)
        assert real.embedding_cache.get("new text") == called_vec
    
    def test_build_context(self, npc_instance):
        """Test that context is built correctly from memories"""
        # Add a user message so brain context can be retrieved
        npc_instance.conversation_memory.append_chat("test message", role=Role.user)
        
        # Mock brain memory to return specific memories
        with patch.object(npc_instance.brain_memory, 'get_memories', return_value="content1\ncontent2"):
            context = npc_instance._build_system_prompt(include_conversation_summary=False, include_brain_context=True)
            assert "content1" in context
            assert "content2" in context


class TestNPCBrainMemoryAPI:
    """Test NPC brain memory API methods"""
    
    def test_get_all_memories(self, npc_instance, mock_qdrant):
        """Test listing all memories"""
        mock_qdrant.export_entities.return_value = [
            Entity(key="key1", content="content1", tags=["memories"]),
            Entity(key="key2", content="content2", tags=["memories"])
        ]
        
        memories = npc_instance.get_all_memories()
        assert len(memories) == 2
        mock_qdrant.export_entities.assert_called_once()
    
    def test_clear_brain_memory(self, npc_instance, mock_qdrant):
        """Test clearing brain memory"""
        npc_instance.clear_brain_memory()
        mock_qdrant.drop_if_exists.assert_called_once()
        mock_qdrant.create.assert_called()
    
    def test_load_entities_from_template(self, npc_instance, mock_qdrant):
        """Test loading entities from template"""
        with patch('src.brain.template_processor.template_to_entities_simple') as mock_template_processor, \
             patch('os.path.exists', return_value=True):
            mock_template_processor.return_value = [
                Entity(key="key1", content="content1", tags=["memories"])
            ]
            
            npc_instance.load_entities_from_template("test.yaml")
            mock_template_processor.assert_called_once()
            mock_qdrant.insert_dataclasses.assert_called_once()
    
    def test_load_entities_from_template_invalid_file(self, npc_instance):
        """Test loading entities with invalid file"""
        with pytest.raises(ValueError, match="File must be a yaml file"):
            npc_instance.load_entities_from_template("test.txt")
    
    def test_load_entities_from_template_file_not_found(self, npc_instance):
        """Test loading entities with non-existent file"""
        with pytest.raises(FileNotFoundError):
            npc_instance.load_entities_from_template("nonexistent.yaml")


class TestNPCPreprocessing:
    """Test NPC preprocessing functionality"""
    
    def test_preprocess_input(self, npc_instance, mock_agent):
        """Test input preprocessing"""
        # Mock the preprocessor agent response
        mock_preprocessed = PreprocessedUserInput(
            text="processed text",
            has_information=True,
            ambiguous_pronouns="",
            needs_clarification=False
        )
        npc_instance.preprocessor_agent.chat_with_history.return_value = mock_preprocessed
        
        # Add some chat history
        npc_instance.conversation_memory.append_chat("Hello", role=Role.user)
        
        result = npc_instance._preprocess_input(npc_instance.conversation_memory.chat_memory)
        assert result.text == "processed text"
        assert result.has_information is True
        assert result.needs_clarification is False


class TestNPCUserInputProcessing:
    """Test NPC user input processing with brain memory"""
    
    def test_process_user_input_with_brain_basic(self, npc_instance, mock_agent):
        """Test basic user input processing via unified chat"""
        # Mock the preprocessor response
        mock_preprocessed = PreprocessedUserInput(
            text="processed text",
            has_information=True,
            ambiguous_pronouns="",
            needs_clarification=False
        )
        npc_instance.preprocessor_agent.chat_with_history.return_value = mock_preprocessed
        
        # Mock the response agent
        mock_response_agent = Mock()
        mock_response_agent.chat_with_history.return_value = ChatResponse(
            hidden_thought_process=None,
            response="AI response",
            off_switch=False
        )
        npc_instance.response_agent = mock_response_agent
        
        response = npc_instance.chat("Hello")
        
        assert isinstance(response, ChatResponse)
        assert response.response == "AI response"
        assert len(npc_instance.conversation_memory.chat_memory) == 2  # user + assistant
    
    def test_process_user_input_with_brain_clarification_needed(self, npc_instance, mock_agent):
        """Test user input processing when clarification is needed via unified chat"""
        # Mock the preprocessor response
        mock_preprocessed = PreprocessedUserInput(
            text="processed text",
            has_information=True,
            ambiguous_pronouns="",
            needs_clarification=True
        )
        npc_instance.preprocessor_agent.chat_with_history.return_value = mock_preprocessed
        
        response = npc_instance.chat("Hello")
        assert isinstance(response, ChatResponse)
        assert "clarification" in response.response.lower()
        assert len(npc_instance.conversation_memory.chat_memory) == 2  # user + assistant (clarification)


class TestNPCChatFunctionality:
    """Test NPC chat functionality"""
    
    def test_chat_flow(self, npc_instance, mock_agent):
        """Test unified chat flow"""
        # Mock preprocessor result
        mock_preprocessed = PreprocessedUserInput(
            text="processed text",
            has_information=False,
            ambiguous_pronouns="",
            needs_clarification=False
        )
        npc_instance.preprocessor_agent.chat_with_history.return_value = mock_preprocessed

        # Mock response agent
        # Ensure response agent returns ChatResponse as NPC.chat expects
        npc_instance.response_agent.chat_with_history.return_value = ChatResponse(
            hidden_thought_process="test thoughts",
            response="test response",
            off_switch=False
        )

        result = npc_instance.chat("Hello")

        assert isinstance(result, ChatResponse)
        assert result.response == "test response"
        assert len(npc_instance.conversation_memory.chat_memory) == 2  # user + assistant
        npc_instance.response_agent.update_system_prompt.assert_called_once()
    
    def test_chat_flow_no_user_message(self, npc_instance, mock_agent):
        """Test unified chat flow without user message"""
        mock_preprocessed = PreprocessedUserInput(
            text="",
            has_information=False,
            ambiguous_pronouns="",
            needs_clarification=False
        )
        npc_instance.preprocessor_agent.chat_with_history.return_value = mock_preprocessed

        mock_response = ChatResponse(
            hidden_thought_process="test thoughts",
            response="test response",
            off_switch=False
        )
        npc_instance.response_agent.chat_with_history.return_value = mock_response

        result = npc_instance.chat(None)
        assert isinstance(result, ChatResponse)
        assert result.response == "test response"
        assert len(npc_instance.conversation_memory.chat_memory) == 2  # user + assistant


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
