import os
import sys
import uuid
import pytest

from dataclasses import fields as dc_fields

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.utils.QdrantCollection import QdrantCollection, initialize_server
from src.utils import VectorUtils, Utilities
from src.core.schemas.CollectionSchemas import Entity


# Global test dimension - can be changed to test with different dimensions
TEST_DIMENSION = 8


@pytest.fixture(autouse=True)
def ensure_server():
    initialize_server()
    yield


@pytest.fixture()
def mock_embeddings(monkeypatch):
    def fake_dim(model):
        return TEST_DIMENSION

    def fake_embed(text, model=VectorUtils.text_embedding_3_small, dimensions=None):
        arr = [0.0] * TEST_DIMENSION
        for i, ch in enumerate(text.encode("utf-8")):
            arr[i % TEST_DIMENSION] += (ch % 31) / 31.0
        return arr

    monkeypatch.setattr(VectorUtils, "get_dimensions_of_model", fake_dim)
    monkeypatch.setattr(VectorUtils, "get_embedding", fake_embed)
    yield


@pytest.fixture()
def unique_collection_name():
    return f"test_q_{uuid.uuid4().hex[:12]}"


def test_dataclass_collection_creation_and_schema(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    col = QdrantCollection(name)
    col.drop_if_exists()

    col.create(dim=TEST_DIMENSION)
    # Creation should be idempotent
    col.create(dim=TEST_DIMENSION)


def test_insert_and_export_entities(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    col = QdrantCollection(name)
    col.drop_if_exists()

    col.create(dim=TEST_DIMENSION)

    rows = [
        Entity(key="alpha", content="first", tags=["t1", "t2"], id=int(Utilities.generate_uuid_int64())),
        Entity(key="beta", content="second", tags=["t2"], id=int(Utilities.generate_uuid_int64())),
        Entity(key="gamma", content="third", tags=[], id=int(Utilities.generate_uuid_int64())),
    ]
    col.insert_dataclasses(rows)

    exported = col.export_entities()
    keys = {e.key for e in exported}
    assert {"alpha", "beta", "gamma"}.issubset(keys)
    for e in exported:
        if e.key in {"alpha", "beta", "gamma"}:
            assert e.id is not None


def test_insert_and_export_entities_with_auto_id(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    col = QdrantCollection(name)
    col.drop_if_exists()

    col.create(dim=TEST_DIMENSION)

    rows = [
        Entity(key="alpha", content="first", tags=["t1", "t2"], id=int(Utilities.generate_uuid_int64())),
        Entity(key="beta", content="second", tags=["t2"], id=int(Utilities.generate_uuid_int64())),
        Entity(key="gamma", content="third", tags=[], id=int(Utilities.generate_uuid_int64())),
    ]
    col.insert_dataclasses(rows)

    exported = col.export_entities()
    keys = {e.key for e in exported}
    assert {"alpha", "beta", "gamma"}.issubset(keys)
    for e in exported:
        if e.key in {"alpha", "beta", "gamma"}:
            assert e.id is not None


def test_search_relevant_entities(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    col = QdrantCollection(name)
    col.drop_if_exists()
    col.create(dim=TEST_DIMENSION)

    rows = [
        Entity(key="close app", content="prefers to end session if annoyed", tags=["goals"], id=int(Utilities.generate_uuid_int64())),
        Entity(key="be concise", content="keep responses brief", tags=["traits"], id=int(Utilities.generate_uuid_int64())),
    ]
    col.insert_dataclasses(rows)

    q = VectorUtils.get_embedding("please be brief", model=VectorUtils.text_embedding_3_small)
    hits = col._search_vectors(q, topk=2)
    assert any("be concise" == h[0].key for h in hits)


def test_init_npc_collection_seeding_from_template_and_saved(tmp_path, mock_embeddings):
    name1 = f"test_q_{uuid.uuid4().hex[:12]}"
    col1 = QdrantCollection(name1)
    col1.drop_if_exists()
    template_path = tmp_path / "template.yaml"
    saved_path = tmp_path / "saved.yaml"
    template_rows = [
        {"id": int(Utilities.generate_uuid_int64()), "key": "trait one", "content": "c1", "tags": ["traits"]},
        {"id": int(Utilities.generate_uuid_int64()), "key": "goal one", "content": "c2", "tags": ["goals"]},
    ]
    template_path.write_text(__import__("yaml").safe_dump(template_rows))

    col1.create(dim=TEST_DIMENSION)
    col1.init_from_file(
        saved_entities_path=str(template_path),
    )
    exported1 = col1.export_entities()
    assert len(exported1) == 2

    name2 = f"test_q_{uuid.uuid4().hex[:12]}"
    col2 = QdrantCollection(name2)
    col2.drop_if_exists()
    saved_rows = [Entity(key="from saved", content="sv", tags=[], id=int(Utilities.generate_uuid_int64()))]
    saved_path2 = tmp_path / "saved2.yaml"
    template_path2 = tmp_path / "template2.yaml"
    saved_path2.write_text(__import__("yaml").safe_dump([e.__dict__ for e in saved_rows]))

    col2.create(dim=TEST_DIMENSION)
    col2.init_from_file(
        saved_entities_path=str(saved_path2),
    )
    exported2 = col2.export_entities()
    assert any(e.key == "from saved" for e in exported2)


def test_idempotent_collection_creation(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    col = QdrantCollection(name)
    col.drop_if_exists()
    col.create(dim=1536)
    col.create(dim=1536)


def test_insert_missing_tags_field(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    col = QdrantCollection(name)
    col.drop_if_exists()
    col.create(dim=TEST_DIMENSION)
    rows = [
        Entity(key="no tags 1", content="c1", tags=[], id=int(Utilities.generate_uuid_int64())),
        Entity(key="no tags 2", content="c2", tags=[], id=int(Utilities.generate_uuid_int64())),
    ]
    col.insert_dataclasses(rows)
    exported = col.export_entities()
    keys = {e.key for e in exported}
    assert {"no tags 1", "no tags 2"}.issubset(keys)


def test_flexible_dimension_handling(unique_collection_name, monkeypatch):
    for test_dim in [8, 16, 128, 1536]:
        def fake_dim(model):
            return test_dim

        def fake_embed(text, model=VectorUtils.text_embedding_3_small, dimensions=None):
            arr = [0.0] * test_dim
            for i, ch in enumerate(text.encode("utf-8")):
                arr[i % test_dim] += (ch % 31) / 31.0
            return arr

        monkeypatch.setattr(VectorUtils, "get_dimensions_of_model", fake_dim)
        monkeypatch.setattr(VectorUtils, "get_embedding", fake_embed)

        name = f"test_q_{uuid.uuid4().hex[:12]}"
        col = QdrantCollection(name)
        col.drop_if_exists()

        col.create(dim=test_dim)

        rows = [
            Entity(key="test1", content="content1", tags=["tag1"], id=int(Utilities.generate_uuid_int64())),
            Entity(key="test2", content="content2", tags=["tag2"], id=int(Utilities.generate_uuid_int64())),
        ]
        col.insert_dataclasses(rows)

        exported = col.export_entities()
        keys = {e.key for e in exported}
        assert {"test1", "test2"}.issubset(keys)

        embedding = VectorUtils.get_embedding("test", model=VectorUtils.text_embedding_3_small)
        assert len(embedding) == test_dim


def test_optional_fields_dataclass(unique_collection_name, mock_embeddings):
    from dataclasses import dataclass
    from typing import Optional, List

    @dataclass
    class Alt:
        id: Optional[int]
        key: str
        content: str
        tags: List[str]
        embedding: Optional[List[float]]

    name = unique_collection_name
    col = QdrantCollection(name)
    col.drop_if_exists()
    col.create(dim=TEST_DIMENSION)


def test_embedding_cache_binary_encoding():
    """Test that embedding cache can encode/decode vectors to/from base64 binary format"""
    from src.utils.embedding_cache import EmbeddingCache
    import tempfile
    from pathlib import Path
    
    # Test with realistic embedding dimensions and values
    test_cases = [
        # Standard OpenAI embedding dimension
        ("short text", [0.1, -0.2, 0.3, -0.4] * 384),  # 1536 dimensions
        # Different values to test precision
        ("another text", [0.123456789, -0.987654321, 0.0, 1.0, -1.0] * 307 + [0.5]),  # 1536 dimensions
        # Edge cases
        ("edge case", [0.0] * 1536),  # All zeros
        ("max values", [1.0, -1.0] * 768),  # Max/min values
    ]
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache_path = Path(tmp_dir) / "test_cache.json"
        cache = EmbeddingCache(cache_path)
        
        # Add test vectors
        for text, vector in test_cases:
            assert len(vector) == 1536, f"Test vector for '{text}' should be 1536 dimensions"
            cache.add(text, vector)
        
        # Save to disk (uses binary encoding)
        cache.save()
        
        # Verify file was created
        assert cache_path.exists(), "Cache file should be created"
        
        # Load from disk (should decode binary format)
        cache2 = EmbeddingCache(cache_path)
        
        # Verify all vectors are loaded correctly
        for text, original_vector in test_cases:
            loaded_vector = cache2.get(text)
            assert loaded_vector is not None, f"Should load vector for '{text}'"
            assert len(loaded_vector) == len(original_vector), f"Vector length mismatch for '{text}'"
            
            # Check precision (should be very close due to float32 encoding)
            for i, (orig, loaded) in enumerate(zip(original_vector, loaded_vector)):
                diff = abs(orig - loaded)
                assert diff < 1e-6, f"Vector precision error at index {i} for '{text}': {orig} vs {loaded}"
        
        # Test direct encoding/decoding methods
        test_vector = [0.1, -0.2, 0.3, -0.4, 0.5]
        encoded = cache._encode_vector(test_vector)
        decoded = cache._decode_vector(encoded)
        
        assert isinstance(encoded, str), "Encoded vector should be a string"
        assert len(decoded) == len(test_vector), "Decoded vector should have same length"
        
        for orig, dec in zip(test_vector, decoded):
            assert abs(orig - dec) < 1e-6, f"Direct encoding/decoding precision error: {orig} vs {dec}"


def test_search_with_tag_filters(unique_collection_name, mock_embeddings):
    """Test that search_text and _search_vectors work with Qdrant filters for tags"""
    from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
    from src.core.schemas.CollectionSchemas import Entity
    from src.utils import Utilities
    
    name = unique_collection_name
    col = QdrantCollection(name)
    col.drop_if_exists()
    col.create(dim=TEST_DIMENSION)
    
    # Insert test data with different tags
    test_entities = [
        Entity(
            id=int(Utilities.generate_uuid_int64()),
            key="memory1",
            content="This is about cats and animals",
            tags=["animals", "pets"]
        ),
        Entity(
            id=int(Utilities.generate_uuid_int64()),
            key="memory2", 
            content="This is about dogs and animals",
            tags=["animals", "pets"]
        ),
        Entity(
            id=int(Utilities.generate_uuid_int64()),
            key="memory3",
            content="This is about work and coding",
            tags=["work", "programming"]
        ),
        Entity(
            id=int(Utilities.generate_uuid_int64()),
            key="memory4",
            content="This is about cats and work",
            tags=["animals", "work"]
        )
    ]
    
    col.insert_dataclasses(test_entities)
    
    # Test 1: Filter for single tag match
    animals_filter = Filter(
        must=[
            FieldCondition(
                key="tags",
                match=MatchValue(value="animals")
            )
        ]
    )
    
    # Search using search_text with filter
    results = col.search_text("test query", topk=10, filter=animals_filter)
    result_keys = {entity.key for entity, score in results}
    
    # Should return entities with "animals" tag
    expected_keys = {"memory1", "memory2", "memory4"}
    assert result_keys == expected_keys, f"Expected {expected_keys}, got {result_keys}"
    
    # Test 2: Filter for multiple possible tags using MatchAny
    pets_or_work_filter = Filter(
        must=[
            FieldCondition(
                key="tags",
                match=MatchAny(any=["pets", "programming"])
            )
        ]
    )
    
    results = col.search_text("test query", topk=10, filter=pets_or_work_filter)
    result_keys = {entity.key for entity, score in results}
    
    # Should return entities with either "pets" or "programming" tags
    expected_keys = {"memory1", "memory2", "memory3"}
    assert result_keys == expected_keys, f"Expected {expected_keys}, got {result_keys}"
    
    # Test 3: Test _search_vectors directly with filter
    query_embedding = VectorUtils.get_embedding("test query")
    results = col._search_vectors(query_embedding, topk=10, filter=animals_filter)
    result_keys = {entity.key for entity, score in results}
    
    # Should return same results as search_text with same filter
    expected_keys = {"memory1", "memory2", "memory4"}
    assert result_keys == expected_keys, f"Expected {expected_keys}, got {result_keys}"
    
    # Test 4: No filter should return all results
    results = col.search_text("test query", topk=10, filter=None)
    result_keys = {entity.key for entity, score in results}
    
    # Should return all entities
    expected_keys = {"memory1", "memory2", "memory3", "memory4"}
    assert result_keys == expected_keys, f"Expected {expected_keys}, got {result_keys}"
    
    # Test 5: Filter that matches no entities
    nonexistent_filter = Filter(
        must=[
            FieldCondition(
                key="tags",
                match=MatchValue(value="nonexistent_tag")
            )
        ]
    )
    
    results = col.search_text("test query", topk=10, filter=nonexistent_filter)
    assert len(results) == 0, "Filter with nonexistent tag should return no results"


def test_string_filter_expressions(unique_collection_name, mock_embeddings):
    """Test that string filter expressions work with search methods"""
    from src.core.schemas.CollectionSchemas import Entity
    from src.utils import Utilities
    
    name = unique_collection_name
    col = QdrantCollection(name)
    col.drop_if_exists()
    col.create(dim=TEST_DIMENSION)
    
    # Insert test data with different tags
    test_entities = [
        Entity(
            id=int(Utilities.generate_uuid_int64()),
            key="memory1",
            content="This is about cats and animals",
            tags=["animals", "pets"]
        ),
        Entity(
            id=int(Utilities.generate_uuid_int64()),
            key="memory2", 
            content="This is about dogs and animals",
            tags=["animals", "pets"]
        ),
        Entity(
            id=int(Utilities.generate_uuid_int64()),
            key="memory3",
            content="This is about work and coding",
            tags=["work", "programming"]
        ),
        Entity(
            id=int(Utilities.generate_uuid_int64()),
            key="memory4",
            content="This is about cats and work",
            tags=["animals", "work"]
        )
    ]
    
    col.insert_dataclasses(test_entities)
    
    # Test 1: Simple string filter
    results = col.search_text("test query", topk=10, filter="'animals'")
    result_keys = {entity.key for entity, score in results}
    expected_keys = {"memory1", "memory2", "memory4"}
    assert result_keys == expected_keys, f"Expected {expected_keys}, got {result_keys}"
    
    # Test 2: AND operation
    results = col.search_text("test query", topk=10, filter="'animals' and 'pets'")
    result_keys = {entity.key for entity, score in results}
    expected_keys = {"memory1", "memory2"}
    assert result_keys == expected_keys, f"Expected {expected_keys}, got {result_keys}"
    
    # Test 3: OR operation  
    results = col.search_text("test query", topk=10, filter="'pets' or 'programming'")
    result_keys = {entity.key for entity, score in results}
    expected_keys = {"memory1", "memory2", "memory3"}
    assert result_keys == expected_keys, f"Expected {expected_keys}, got {result_keys}"
    
    # Test 4: Complex nested operation
    results = col.search_text("test query", topk=10, filter="'animals' and ('pets' or 'work')")
    result_keys = {entity.key for entity, score in results}
    expected_keys = {"memory1", "memory2", "memory4"}  # All have animals, and either pets or work
    assert result_keys == expected_keys, f"Expected {expected_keys}, got {result_keys}"
    
    # Test 5: NOT operation
    results = col.search_text("test query", topk=10, filter="not 'programming'")
    result_keys = {entity.key for entity, score in results}
    expected_keys = {"memory1", "memory2", "memory4"}  # All except memory3
    assert result_keys == expected_keys, f"Expected {expected_keys}, got {result_keys}"


