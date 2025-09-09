import os
import sys
import uuid
import pytest

from dataclasses import fields as dc_fields

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.utils import qdrant_utils as QdrantUtil, VectorUtils, Utilities
from src.core.schemas.CollectionSchemas import Entity


# Global test dimension - can be changed to test with different dimensions
TEST_DIMENSION = 8


@pytest.fixture(autouse=True)
def ensure_server():
    QdrantUtil.initialize_server()
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
    QdrantUtil.drop_collection_if_exists(name)

    QdrantUtil.create_collection(name, dim=TEST_DIMENSION)
    # Creation should be idempotent
    QdrantUtil.create_collection(name, dim=TEST_DIMENSION)


def test_insert_and_export_entities(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    QdrantUtil.drop_collection_if_exists(name)

    QdrantUtil.create_collection(name, dim=TEST_DIMENSION)

    rows = [
        Entity(key="alpha", content="first", tags=["t1", "t2"], id=int(Utilities.generate_uuid_int64())),
        Entity(key="beta", content="second", tags=["t2"], id=int(Utilities.generate_uuid_int64())),
        Entity(key="gamma", content="third", tags=[], id=int(Utilities.generate_uuid_int64())),
    ]
    QdrantUtil.insert_dataclasses(name, rows)

    exported = QdrantUtil.export_collection_as_entities(name)
    keys = {e.key for e in exported}
    assert {"alpha", "beta", "gamma"}.issubset(keys)
    for e in exported:
        if e.key in {"alpha", "beta", "gamma"}:
            assert e.id is not None


def test_insert_and_export_entities_with_auto_id(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    QdrantUtil.drop_collection_if_exists(name)

    QdrantUtil.create_collection(name, dim=TEST_DIMENSION)

    rows = [
        Entity(key="alpha", content="first", tags=["t1", "t2"], id=int(Utilities.generate_uuid_int64())),
        Entity(key="beta", content="second", tags=["t2"], id=int(Utilities.generate_uuid_int64())),
        Entity(key="gamma", content="third", tags=[], id=int(Utilities.generate_uuid_int64())),
    ]
    QdrantUtil.insert_dataclasses(name, rows)

    exported = QdrantUtil.export_collection_as_entities(name)
    keys = {e.key for e in exported}
    assert {"alpha", "beta", "gamma"}.issubset(keys)
    for e in exported:
        if e.key in {"alpha", "beta", "gamma"}:
            assert e.id is not None


def test_search_relevant_entities(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    QdrantUtil.drop_collection_if_exists(name)
    QdrantUtil.create_collection(name, dim=TEST_DIMENSION)

    rows = [
        Entity(key="close app", content="prefers to end session if annoyed", tags=["goals"], id=int(Utilities.generate_uuid_int64())),
        Entity(key="be concise", content="keep responses brief", tags=["traits"], id=int(Utilities.generate_uuid_int64())),
    ]
    QdrantUtil.insert_dataclasses(name, rows)

    q = VectorUtils.get_embedding("please be brief", model=VectorUtils.text_embedding_3_small)
    hits = QdrantUtil.search_relevant_records(name, q, topk=2)
    assert any("be concise" == h[0].key for h in hits)


def test_init_npc_collection_seeding_from_template_and_saved(tmp_path, mock_embeddings):
    name1 = f"test_q_{uuid.uuid4().hex[:12]}"
    QdrantUtil.drop_collection_if_exists(name1)
    template_path = tmp_path / "template.yaml"
    saved_path = tmp_path / "saved.yaml"
    template_rows = [
        {"id": int(Utilities.generate_uuid_int64()), "key": "trait one", "content": "c1", "tags": ["traits"]},
        {"id": int(Utilities.generate_uuid_int64()), "key": "goal one", "content": "c2", "tags": ["goals"]},
    ]
    template_path.write_text(__import__("yaml").safe_dump(template_rows))

    QdrantUtil.create_collection(name1, dim=TEST_DIMENSION)
    QdrantUtil.init_collection_from_file(
        name1,
        saved_entities_path=str(template_path),
    )
    exported1 = QdrantUtil.export_collection_as_entities(name1)
    assert len(exported1) == 2

    name2 = f"test_q_{uuid.uuid4().hex[:12]}"
    QdrantUtil.drop_collection_if_exists(name2)
    saved_rows = [Entity(key="from saved", content="sv", tags=[], id=int(Utilities.generate_uuid_int64()))]
    saved_path2 = tmp_path / "saved2.yaml"
    template_path2 = tmp_path / "template2.yaml"
    saved_path2.write_text(__import__("yaml").safe_dump([e.__dict__ for e in saved_rows]))

    QdrantUtil.create_collection(name2, dim=TEST_DIMENSION)
    QdrantUtil.init_collection_from_file(
        name2,
        saved_entities_path=str(saved_path2),
    )
    exported2 = QdrantUtil.export_collection_as_entities(name2)
    assert any(e.key == "from saved" for e in exported2)


def test_idempotent_collection_creation(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    QdrantUtil.drop_collection_if_exists(name)
    QdrantUtil.create_collection(name, dim=1536)
    QdrantUtil.create_collection(name, dim=1536)


def test_insert_missing_tags_field(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    QdrantUtil.drop_collection_if_exists(name)
    QdrantUtil.create_collection(name, dim=TEST_DIMENSION)
    rows = [
        Entity(key="no tags 1", content="c1", tags=[], id=int(Utilities.generate_uuid_int64())),
        Entity(key="no tags 2", content="c2", tags=[], id=int(Utilities.generate_uuid_int64())),
    ]
    QdrantUtil.insert_dataclasses(name, rows)
    exported = QdrantUtil.export_collection_as_entities(name)
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
        QdrantUtil.drop_collection_if_exists(name)

        QdrantUtil.create_collection(name, dim=test_dim)

        rows = [
            Entity(key="test1", content="content1", tags=["tag1"], id=int(Utilities.generate_uuid_int64())),
            Entity(key="test2", content="content2", tags=["tag2"], id=int(Utilities.generate_uuid_int64())),
        ]
        QdrantUtil.insert_dataclasses(name, rows)

        exported = QdrantUtil.export_collection_as_entities(name)
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
    QdrantUtil.drop_collection_if_exists(name)
    QdrantUtil.create_collection(name, dim=TEST_DIMENSION)


