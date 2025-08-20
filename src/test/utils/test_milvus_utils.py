import os
import sys
import uuid
import pytest

from dataclasses import fields as dc_fields
from pymilvus import utility, connections, Collection

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.utils import MilvusUtil, Utilities
from src.core.schemas.CollectionSchemas import Entity


@pytest.fixture(autouse=True)
def ensure_server():
    # Ensure Milvus server is up for each test session
    MilvusUtil.initialize_server()
    yield
    # Do not stop server; tests may rely on persistence


@pytest.fixture()
def mock_embeddings(monkeypatch):
    def fake_dim(model):
        return 8

    def fake_embed(text, model=MilvusUtil.text_embedding_3_small, dimensions=None):
        # Deterministic 8-dim embedding from text bytes
        arr = [0.0] * 8
        for i, ch in enumerate(text.encode("utf-8")):
            arr[i % 8] += (ch % 31) / 31.0
        return arr

    monkeypatch.setattr(MilvusUtil, "get_dimensions_of_model", fake_dim)
    monkeypatch.setattr(MilvusUtil, "get_embedding", fake_embed)
    yield


@pytest.fixture()
def unique_collection_name():
    return f"test_{uuid.uuid4().hex[:12]}"


def test_dataclass_collection_creation_and_schema(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    MilvusUtil.drop_collection_if_exists(name)

    col = MilvusUtil.load_or_create_collection(name, dim=8, model_cls=Entity)
    assert isinstance(col, Collection)

    col_field_names = {f.name for f in col.schema.fields}
    for cls_field in dc_fields(Entity):
        assert cls_field.name in col_field_names

def test_insert_and_export_entities(unique_collection_name):
    name = unique_collection_name
    MilvusUtil.drop_collection_if_exists(name)

    col = MilvusUtil.load_or_create_collection(name, dim=8, model_cls=Entity, auto_id=False)

    rows = [
        Entity(key="alpha", content="first", tags=["t1", "t2"], id=Utilities.generate_uuid_int64()),
        Entity(key="beta", content="second", tags=["t2"], id=Utilities.generate_uuid_int64()),
        Entity(key="gamma", content="third", tags=[], id=Utilities.generate_uuid_int64()),
    ]
    MilvusUtil.insert_dataclasses(col, rows)

    col.flush()
    assert col.num_entities >= 3

    exported = MilvusUtil.export_dataclasses(col, Entity)
    keys = {e.key for e in exported}
    assert {"alpha", "beta", "gamma"}.issubset(keys)
    # ids should be present
    for e in exported:
        if e.key in {"alpha", "beta", "gamma"}:
            assert e.id is not None


def test_insert_and_export_entities_with_auto_id(unique_collection_name):
    name = unique_collection_name
    MilvusUtil.drop_collection_if_exists(name)

    col = MilvusUtil.load_or_create_collection(name, dim=8, model_cls=Entity, auto_id=True)

    rows = [
        Entity(key="alpha", content="first", tags=["t1", "t2"]),
        Entity(key="beta", content="second", tags=["t2"]),
        Entity(key="gamma", content="third", tags=[]),
    ]
    MilvusUtil.insert_dataclasses(col, rows)

    col.flush()
    assert col.num_entities >= 3

    exported = MilvusUtil.export_dataclasses(col, Entity)
    keys = {e.key for e in exported}
    assert {"alpha", "beta", "gamma"}.issubset(keys)
    # ids should be present
    for e in exported:
        if e.key in {"alpha", "beta", "gamma"}:
            assert e.id is not None


def test_search_relevant_entities(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    MilvusUtil.drop_collection_if_exists(name)
    col = MilvusUtil.load_or_create_collection(name, dim=8, model_cls=Entity)

    rows = [
        Entity(key="close app", content="prefers to end session if annoyed", tags=["goals"]),
        Entity(key="be concise", content="keep responses brief", tags=["traits"]),
    ]
    MilvusUtil.insert_dataclasses(col, rows, model_cls=Entity)
    col.flush()

    q = MilvusUtil.compute_embeddings(["please be brief"], model=MilvusUtil.text_embedding_3_small)[0]
    hits = MilvusUtil.search_relevant_records(col, [q], model_cls=Entity, topk=2)
    assert any("be concise" == h.key for h in hits)


def test_init_npc_collection_seeding_from_template_and_saved(tmp_path, mock_embeddings):
    # Template-only seed
    name1 = f"test_{uuid.uuid4().hex[:12]}"
    MilvusUtil.drop_collection_if_exists(name1)
    template_path = tmp_path / "template.yaml"
    saved_path = tmp_path / "saved.yaml"
    template_rows = [
        {"key": "trait one", "content": "c1", "tags": ["traits"]},
        {"key": "goal one", "content": "c2", "tags": ["goals"]},
    ]
    template_path.write_text(__import__("yaml").safe_dump(template_rows))

    col1, seeded1 = MilvusUtil.init_npc_collection(
        name1,
        is_new_game=True,
        saved_entities_path=str(saved_path),
        template_entities_path=str(template_path),
        model_cls=Entity,
    )
    assert seeded1 is not None and len(seeded1) == 2
    assert saved_path.exists()

    # Saved-only seed
    name2 = f"test_{uuid.uuid4().hex[:12]}"
    MilvusUtil.drop_collection_if_exists(name2)
    saved_rows = [Entity(key="from saved", content="sv", tags=[])]
    saved_path2 = tmp_path / "saved2.yaml"
    template_path2 = tmp_path / "template2.yaml"
    saved_path2.write_text(__import__("yaml").safe_dump([e.__dict__ for e in saved_rows]))

    col2, seeded2 = MilvusUtil.init_npc_collection(
        name2,
        is_new_game=False,
        saved_entities_path=str(saved_path2),
        template_entities_path=str(template_path2),
        model_cls=Entity,
    )
    assert seeded2 is not None and seeded2[0].key == "from saved"


def test_disconnect_and_reconnect(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    MilvusUtil.drop_collection_if_exists(name)
    col = MilvusUtil.load_or_create_collection(name, dim=8, model_cls=Entity)
    MilvusUtil.insert_dataclasses(col, [Entity(key="k", content="v", tags=[])], model_cls=Entity)
    col.flush()

    # Disconnect
    try:
        connections.disconnect(alias="default")
    except Exception:
        pass

    # Reconnect
    MilvusUtil.initialize_server()
    assert utility.has_collection(name)
    col2 = Collection(name)
    exported = MilvusUtil.export_dataclasses(col2, Entity)
    assert any(e.key == "k" for e in exported)


def test_idempotent_collection_creation(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    MilvusUtil.drop_collection_if_exists(name)
    col1 = MilvusUtil.load_or_create_collection(name, dim=8, model_cls=Entity)
    # Calling again should not error and should return a Collection
    col2 = MilvusUtil.load_or_create_collection(name, dim=8, model_cls=Entity)
    assert isinstance(col1, Collection) and isinstance(col2, Collection)


def test_insert_missing_tags_field(unique_collection_name, mock_embeddings):
    name = unique_collection_name
    MilvusUtil.drop_collection_if_exists(name)
    col = MilvusUtil.load_or_create_collection(name, dim=8, model_cls=Entity)
    rows = [
        Entity(key="no tags 1", content="c1", tags=[]),
        Entity(key="no tags 2", content="c2", tags=[]),
    ]
    MilvusUtil.insert_dataclasses(col, rows, model_cls=Entity)
    col.flush()
    exported = MilvusUtil.export_dataclasses(col, Entity)
    keys = {e.key for e in exported}
    assert {"no tags 1", "no tags 2"}.issubset(keys)


def test_init_npc_collection_no_seed_sources(unique_collection_name, tmp_path, mock_embeddings):
    name = unique_collection_name
    MilvusUtil.drop_collection_if_exists(name)
    saved_path = tmp_path / "saved.yaml"
    template_path = tmp_path / "template.yaml"  # does not exist
    col, seeded = MilvusUtil.init_npc_collection(
        name,
        is_new_game=False,
        saved_entities_path=str(saved_path),
        template_entities_path=str(template_path),
        model_cls=Entity,
    )
    assert isinstance(col, Collection)
    assert seeded is None


def test_compute_embeddings_len_and_dim(mock_embeddings):
    texts = ["a", "bb", "ccc"]
    embs = MilvusUtil.compute_embeddings(texts, model=MilvusUtil.text_embedding_3_small)
    assert len(embs) == 3
    assert all(len(v) == 8 for v in embs)


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
    MilvusUtil.drop_collection_if_exists(name)
    col = MilvusUtil.load_or_create_collection(name, dim=8, model_cls=Alt)
    assert isinstance(col, Collection)


