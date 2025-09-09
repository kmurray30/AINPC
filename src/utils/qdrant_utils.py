import os
from dataclasses import fields as dc_fields, is_dataclass, dataclass
from pathlib import Path
from typing import Any, Final, List, Optional, Tuple, Type, TypeVar, get_args, get_origin

from qdrant_client import QdrantClient, models

from src.core.schemas.CollectionSchemas import Entity
from src.utils import Logger, VectorUtils
from src.utils.Utilities import generate_uuid_int64

T = TypeVar("T")


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


def drop_collection_if_exists(name: str):
    client = _get_client()
    try:
        if client.collection_exists(collection_name=name):
            Logger.verbose(f"Dropping collection {name}")
            client.delete_collection(collection_name=name)
    except Exception as exc:
        raise Exception(f"Failed to drop collection {name}: {exc}")


def _vector_params(dim: int, metric: str = "COSINE") -> models.VectorParams:
    metric_map = {
        "COSINE": models.Distance.COSINE,
        "L2": models.Distance.EUCLID,
        "IP": models.Distance.DOT,
    }
    return models.VectorParams(size=dim, distance=metric_map.get(metric.upper(), models.Distance.COSINE))


def create_collection(name: str, dim: int, metric: str = "COSINE"):
    client = _get_client()
    if client.collection_exists(collection_name=name):
        Logger.warning(f"Collection {name} already exists")
        return
    Logger.verbose(f"Creating Qdrant collection {name} (dim={dim}, metric={metric})")
    client.create_collection(
        collection_name=name,
        vectors_config=_vector_params(dim, metric=metric),
    )


def insert_dataclasses(
    collection_name: str,
    records: List[Entity],
    embed_model: str = text_embedding_3_small,
):
    embedding_map = {}

    # Embed text where missing
    for record in records:
        record_id = record.id
        if record_id is None:
            raise ValueError(f"Record {record} id field is empty. Needed for embedding.")
        text_to_embed = record.key
        if text_to_embed is None:
            raise ValueError(f"Record {record} key field is empty. Needed for embedding.")
        Logger.verbose(f"Embedding text: {text_to_embed}")
        embedding = VectorUtils.get_embedding(text_to_embed, model=embed_model)
        embedding_map[record_id] = embedding
    
    # Build points
    points: List[models.PointStruct] = []
    for record in records:
        record_id = record.id
        embedding = embedding_map[record_id]
        payload = {
            "key": record.key,
            "content": record.content,
            "tags": record.tags,
        }

        points.append(
            models.PointStruct(
                id=record_id,
                vector=embedding,
                payload=payload,
            )
        )

    client = _get_client()
    Logger.verbose(f"Inserting {len(points)} records into collection {collection_name}")
    client.upsert(collection_name=collection_name, points=points, wait=True)
    Logger.verbose(f"Done inserting {len(points)} records into collection {collection_name}")


def export_collection_as_entities(collection_name: str, limit: int = 1000) -> List[Entity]:
    client = _get_client()
    out: List[Entity] = []
    next_offset = None
    fetched = 0
    while fetched < limit:
        batch_limit = min(256, limit - fetched)
        scroll_res = client.scroll(
            collection_name=collection_name,
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
            constructor_kwargs["key"] = p.payload["key"]
            constructor_kwargs["content"] = p.payload["content"]
            constructor_kwargs["tags"] = p.payload["tags"]
            out.append(Entity(**constructor_kwargs))
        fetched += len(points)
        if next_offset is None:
            break
    return out


def search_relevant_records(
    collection_name: str,
    query_embedding: List[float],
    topk: int = 5,
) -> List[Tuple[Entity, float]]:
    # Qdrant uses the metric configured at collection creation; metric parameter retained for API parity
    client = _get_client()

    # Perform search TODO add filtering by tags
    results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=topk,
        with_payload=True,
        with_vectors=False,
    )

    result_records: List[Tuple[Entity, float]] = [] 

    for scored_point in results:
        payload = scored_point.payload or {}
        constructor_kwargs = {}
        for field in dc_fields(Entity):
            if field.name == "id":
                constructor_kwargs["id"] = scored_point.id
            else:
                constructor_kwargs[field.name] = payload.get(field.name)
        if not constructor_kwargs.get("id", None):
            raise ValueError(f"Entity {scored_point.id} has no id")
        result_records.append((Entity(**constructor_kwargs), float(scored_point.score)))
    return result_records


def multi_search_relevant_records(
    collection_name: str,
    queries_embeddings: List[List[float]],
    topk: int = 5,
    metric: str = "COSINE",
) -> List[Tuple[Entity, float]]:
    if not queries_embeddings:
        return []
    best_by_id: dict[Any, Tuple[Entity, float]] = {}
    for query_embedding in queries_embeddings:
        for ent, score in search_relevant_records(collection_name, query_embedding, topk=topk):
            uid = ent.id or ent.key
            prev = best_by_id.get(uid)
            # Since a given entry/id can have multiple keys/embeddings, we keep the highest score
            if not prev or score > prev[1]:
                best_by_id[uid] = (ent, score)
    merged = sorted(best_by_id.values(), key=lambda x: x[1], reverse=True)
    return merged[:topk]


def init_collection_from_file(
    collection_name: str,
    saved_entities_path: str,
    embed_model: str = text_embedding_3_small,
) -> None:
    from src.utils import io_utils  # local import to avoid cycles at module load
    entities = io_utils.load_yaml_into_dataclass(Path(saved_entities_path), List[Entity])
    insert_dataclasses(collection_name, entities, embed_model=embed_model)


