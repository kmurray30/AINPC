import os
from dataclasses import fields as dc_fields, is_dataclass, dataclass
from pathlib import Path
from typing import Any, Final, List, Optional, Tuple, Type, TypeVar, get_args, get_origin

from qdrant_client import QdrantClient, models

from src.utils import Logger, VectorUtils
from src.utils.Utilities import generate_uuid_int64


# Public re-exports/wrappers so tests can monkeypatch like in Milvus tests
text_embedding_3_small = VectorUtils.text_embedding_3_small


QDRANT_CLIENT: QdrantClient | None = None


def _get_env_host_port() -> tuple[str, int]:
    host = os.getenv("QDRANT_HOST", "localhost")
    try:
        port = int(os.getenv("QDRANT_PORT", "6333"))
    except ValueError:
        port = 6333
    return host, port


def _get_client() -> QdrantClient:
    global QDRANT_CLIENT
    if QDRANT_CLIENT is None:
        host, port = _get_env_host_port()
        Logger.verbose(f"Connecting to Qdrant at {host}:{port}")
        QDRANT_CLIENT = QdrantClient(host=host, port=port)
        # Touch the server to validate connection
        try:
            QDRANT_CLIENT.get_collections()
        except Exception as exc:
            # Reset on failure
            QDRANT_CLIENT = None
            raise Exception(f"Failed to connect to Qdrant at {host}:{port}: {exc}")
    return QDRANT_CLIENT


def initialize_server():
    _get_client()


def disconnect_server():
    global QDRANT_CLIENT
    if QDRANT_CLIENT is not None:
        # qdrant-client uses HTTP; no persistent connection to close
        Logger.verbose("Resetting Qdrant client")
        QDRANT_CLIENT = None


def collection_exists(name: str) -> bool:
    client = _get_client()
    try:
        return bool(client.collection_exists(collection_name=name))
    except Exception:
        # Some client versions may not have collection_exists; fallback
        try:
            client.get_collection(collection_name=name)
            return True
        except Exception:
            return False


def drop_collection_if_exists(name: str):
    client = _get_client()
    try:
        if collection_exists(name):
            Logger.verbose(f"Dropping collection {name}")
            client.delete_collection(collection_name=name)
    except Exception as exc:
        raise Exception(f"Failed to drop collection {name}: {exc}")


@dataclass
class QdrantCollection:
    name: str
    auto_id: bool


def _vector_params(dim: int, metric: str = "COSINE") -> models.VectorParams:
    metric_map = {
        "COSINE": models.Distance.COSINE,
        "L2": models.Distance.EUCLID,
        "IP": models.Distance.DOT,
    }
    return models.VectorParams(size=dim, distance=metric_map.get(metric.upper(), models.Distance.COSINE))


def _create_collection(name: str, dim: int, metric: str = "COSINE") -> QdrantCollection:
    client = _get_client()
    Logger.verbose(f"Creating Qdrant collection {name} (dim={dim}, metric={metric})")
    client.create_collection(
        collection_name=name,
        vectors_config=_vector_params(dim, metric=metric),
    )
    return QdrantCollection(name=name, auto_id=True)


_UNSET: Final = object()


def _get_collection_vector_size(name: str) -> Optional[int]:
    client = _get_client()
    try:
        info = client.get_collection(collection_name=name)
        vectors_cfg = info.config.params.vectors  # type: ignore[attr-defined]
        # Single-vector collection
        if isinstance(vectors_cfg, models.VectorParams):
            return vectors_cfg.size
        # Multi-vector collection
        if isinstance(vectors_cfg, dict):
            # Prefer an "embedding" vector if present
            if "embedding" in vectors_cfg and isinstance(vectors_cfg["embedding"], models.VectorParams):
                return vectors_cfg["embedding"].size
            # Otherwise, return size of the first vector params
            for v in vectors_cfg.values():
                if isinstance(v, models.VectorParams):
                    return v.size
    except Exception:
        return None
    return None


def _load_collection(name: str, dim: int, default: Any = _UNSET) -> QdrantCollection:
    if not collection_exists(name):
        if default is _UNSET:
            raise ValueError(f"Collection {name} does not exist")
        return default
    # Validate dimension if retrievable
    actual_dim = _get_collection_vector_size(name)
    if actual_dim is not None and actual_dim != dim:
        raise ValueError(f"Collection {name} exists with dim {actual_dim}, expected {dim}")
    return QdrantCollection(name=name, auto_id=True)


def create_collection_from_cls(name: str, model_cls: Type, dim: int, auto_id: bool = True) -> QdrantCollection:
    if not is_dataclass(model_cls):
        raise TypeError("model_cls must be a dataclass type")
    return _create_collection(name, dim)


def load_collection_from_cls(name: str, model_cls: Type, dim: int, auto_id: bool = True) -> Optional[QdrantCollection]:
    if not is_dataclass(model_cls):
        raise TypeError("model_cls must be a dataclass type")
    return _load_collection(name, dim, default=None)


def load_or_create_collection_from_cls(name: str, dim: int, *, model_cls: Type, auto_id: bool = True) -> QdrantCollection:
    if not is_dataclass(model_cls):
        raise TypeError("model_cls must be a dataclass type")
    col = _load_collection(name, dim, default=None)
    if col:
        # Preserve caller's auto_id preference for downstream logic
        col.auto_id = auto_id
        return col
    col = _create_collection(name, dim)
    col.auto_id = auto_id
    return col


T = TypeVar("T")


def insert_dataclasses(
    collection: QdrantCollection,
    records: List[T],
    *,
    embed_model: str = text_embedding_3_small,
    embed_text_attr: str = "key",
):
    if not records:
        return

    if not all(is_dataclass(r) for r in records):
        raise ValueError("All records must be dataclass instances")

    if not all(hasattr(r, "embedding") for r in records):
        raise ValueError("All records must have an embedding field, even if empty")

    if not all(hasattr(r, embed_text_attr) for r in records):
        raise ValueError(f"All records must have a {embed_text_attr} field (specified by embed_text_attr argument), even if empty")

    # Handle ids per auto_id policy
    if not collection.auto_id:
        if not all(hasattr(r, "id") and getattr(r, "id") is not None for r in records):
            raise ValueError("All records must have an id field when auto_id is False")

    # Embed text where missing
    for r in records:
        if not getattr(r, "embedding"):
            text = getattr(r, embed_text_attr, None)
            if text is None:
                raise ValueError(f"Record {r} {embed_text_attr} field is empty. Needed for embedding.")
            Logger.verbose(f"Embedding text: {text}")
            embedding = VectorUtils.get_embedding(text, model=embed_model)
            setattr(r, "embedding", embedding)

    # Build points
    points: List[models.PointStruct] = []
    for r in records:
        record_id = getattr(r, "id", None)
        if record_id is None and collection.auto_id:
            record_id = int(generate_uuid_int64())
            setattr(r, "id", record_id)

        payload: dict[str, Any] = {}
        for f in dc_fields(type(r)):
            if f.name in ("embedding", "id"):
                continue
            payload[f.name] = getattr(r, f.name, None)

        points.append(
            models.PointStruct(
                id=record_id,
                vector=getattr(r, "embedding") or [],
                payload=payload,
            )
        )

    client = _get_client()
    Logger.verbose(f"Inserting {len(points)} records into collection {collection.name}")
    client.upsert(collection_name=collection.name, points=points, wait=True)
    Logger.verbose(f"Done inserting {len(points)} records into collection {collection.name}")


def export_dataclasses(collection: QdrantCollection, model_cls: Type[T], limit: int = 100000) -> List[T]:
    if not is_dataclass(model_cls):
        raise ValueError("model_cls must be a dataclass type")

    client = _get_client()
    out: List[T] = []
    next_offset = None
    fetched = 0
    while fetched < limit:
        batch_limit = min(256, limit - fetched)
        scroll_res = client.scroll(
            collection_name=collection.name,
            with_payload=True,
            with_vectors=False,
            limit=batch_limit,
            offset=next_offset,
        )
        points, next_offset = scroll_res
        if not points:
            break
        for p in points:
            constructor_kwargs = dict(p.payload or {})
            # Ensure id present
            constructor_kwargs["id"] = p.id
            # Ensure embedding present (we do not fetch vectors here)
            if any(field.name == "embedding" for field in dc_fields(model_cls)):
                constructor_kwargs["embedding"] = None
            out.append(model_cls(**constructor_kwargs))
        fetched += len(points)
        if next_offset is None:
            break
    return out


def search_relevant_records(
    collection: QdrantCollection,
    query_embedding: List[float],
    *,
    model_cls: Type[T],
    topk: int = 5,
    metric: str = "COSINE",
) -> List[Tuple[T, float]]:
    # Qdrant uses the metric configured at collection creation; metric parameter retained for API parity
    client = _get_client()

    output_field_names = [field.name for field in dc_fields(model_cls) if field.name != "embedding"]
    # Perform search
    results = client.search(
        collection_name=collection.name,
        query_vector=query_embedding,
        limit=topk,
        with_payload=True,
        with_vectors=False,
    )

    result_records: List[Tuple[T, float]] = []
    # Identify list[str] fields for normalization if needed (payload stores lists natively)
    list_string_field_names = {
        field.name
        for field in dc_fields(model_cls)
        if get_origin(field.type) in (list, List) and (get_args(field.type) and get_args(field.type)[0] is str)
    }

    for sp in results:
        constructor_kwargs = {}
        payload = sp.payload or {}
        for field_name in output_field_names:
            if field_name == "id":
                constructor_kwargs[field_name] = sp.id
                continue
            value = payload.get(field_name, None)
            # Normalize comma-separated strings if ever encountered
            if field_name in list_string_field_names and isinstance(value, str):
                constructor_kwargs[field_name] = [tag.strip() for tag in value.split(",") if tag.strip()]
            else:
                constructor_kwargs[field_name] = value
        if any(field.name == "embedding" for field in dc_fields(model_cls)):
            constructor_kwargs["embedding"] = None
        dataclass_instance = model_cls(**constructor_kwargs)
        result_records.append((dataclass_instance, float(sp.score)))
    return result_records


def multi_search_relevant_records(
    collection: QdrantCollection,
    queries_embeddings: List[List[float]],
    *,
    model_cls: Type[T],
    topk: int = 5,
    metric: str = "COSINE",
) -> List[Tuple[T, float]]:
    if not queries_embeddings:
        return []

    seen: dict[Any, Tuple[T, float]] = {}
    for query_embedding in queries_embeddings:
        for record, score in search_relevant_records(
            collection=collection,
            query_embedding=query_embedding,
            model_cls=model_cls,
            topk=topk,
            metric=metric,
        ):
            unique_identifier = getattr(record, "key", None) or getattr(record, "id", None)
            if unique_identifier in seen:
                _, existing_score = seen[unique_identifier]
                if score > existing_score:
                    seen[unique_identifier] = (record, score)
            else:
                seen[unique_identifier] = (record, score)

    merged = sorted(seen.values(), key=lambda x: x[1], reverse=True)
    return merged[:topk]


def init_npc_collection(
    collection_name: str,
    *,
    is_new_game: bool,
    saved_entities_path: str,
    template_entities_path: str,
    embed_model: str = text_embedding_3_small,
    model_cls: Optional[Type[T]] = None,
    embed_text_attr: str = "key",
) -> (QdrantCollection, Optional[List[T]]):
    from src.utils import io_utils  # local import to avoid cycles at module load

    if model_cls is None or not is_dataclass(model_cls):
        raise TypeError("model_cls must be a dataclass type")

    initialize_server()
    col = load_or_create_collection_from_cls(
        collection_name,
        VectorUtils.get_dimensions_of_model(embed_model),
        model_cls=model_cls,
        auto_id=True,
    )

    client = _get_client()
    count = client.count(collection_name=collection_name, exact=True).count

    seeded: Optional[List[T]] = None
    if count == 0:
        source = None
        if (not is_new_game) and os.path.exists(saved_entities_path):
            source = saved_entities_path
        elif os.path.exists(template_entities_path):
            source = template_entities_path
        if source:
            try:
                records: List[T] = io_utils.load_yaml_into_dataclass(Path(source), List[model_cls])  # type: ignore
                if isinstance(records, list):
                    insert_dataclasses(col, records, embed_model=embed_model, embed_text_attr=embed_text_attr)
                    seeded = records
                    if is_new_game and source == template_entities_path:
                        try:
                            os.makedirs(os.path.dirname(saved_entities_path), exist_ok=True)
                            io_utils.save_to_yaml_file(records, Path(saved_entities_path))
                        except Exception:
                            # Best effort snapshot
                            pass
            except Exception as exc:
                Logger.warning(f"Seeding from YAML failed: {exc}")
    return col, seeded


