import os
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any, List, Tuple, Optional, Union

from qdrant_client import QdrantClient, models
from qdrant_client.models import Filter

from src.core.schemas.CollectionSchemas import Entity
from src.utils import Logger, VectorUtils
from src.utils.qdrant_filter import parse_filter_string
from src.brain.embedding_cache import EmbeddingCache


_QDRANT_CLIENT: QdrantClient | None = None


def _get_env_host_port() -> tuple[str, int]:
    host = os.getenv("QDRANT_HOST", "localhost")
    try:
        port = int(os.getenv("QDRANT_PORT", "6333"))
    except ValueError:
        port = 6333
    return host, port


def _get_client() -> QdrantClient:
    global _QDRANT_CLIENT
    if _QDRANT_CLIENT is None:
        host, port = _get_env_host_port()
        Logger.verbose(f"Connecting to Qdrant at {host}:{port}")
        _QDRANT_CLIENT = QdrantClient(host=host, port=port)
        try:
            _QDRANT_CLIENT.get_collections()
        except Exception as exc:
            _QDRANT_CLIENT = None
            raise Exception(f"Failed to connect to Qdrant at {host}:{port}: {exc}")
    return _QDRANT_CLIENT


def _vector_params(dim: int, metric: str = "COSINE") -> models.VectorParams:
    metric_map = {
        "COSINE": models.Distance.COSINE,
        "L2": models.Distance.EUCLID,
        "IP": models.Distance.DOT,
    }
    return models.VectorParams(size=dim, distance=metric_map.get(metric.upper(), models.Distance.COSINE))


def initialize_server() -> None:
    _get_client()


class QdrantCollection:
    def __init__(self, name: str, *, embed_model: str = VectorUtils.text_embedding_3_small):
        self.name = name
        self.embed_model = embed_model
        self.embedding_cache = EmbeddingCache()

    # Lifecycle
    def create(self, dim: int, metric: str = "COSINE") -> None:
        client = _get_client()
        if client.collection_exists(collection_name=self.name):
            Logger.warning(f"Collection {self.name} already exists")
            return
        Logger.verbose(f"Creating Qdrant collection {self.name} (dim={dim}, metric={metric})")
        client.create_collection(
            collection_name=self.name,
            vectors_config=_vector_params(dim, metric=metric),
        )

    def maintain(self) -> None:
        self.embedding_cache.save()

    def drop_if_exists(self) -> None:
        client = _get_client()
        try:
            if client.collection_exists(collection_name=self.name):
                Logger.verbose(f"Dropping collection {self.name}")
                client.delete_collection(collection_name=self.name)
        except Exception as exc:
            raise Exception(f"Failed to drop collection {self.name}: {exc}")

    def _get_embedding(self, text: str) -> List[float]:
        cached = self.embedding_cache.get(text)
        if cached:
            return cached
        if cached is None:
            embedding = VectorUtils.get_embedding(text, model=self.embed_model)
            self.embedding_cache.add(text, embedding)
            return embedding

    # Data IO
    def insert_dataclasses(self, records: List[Entity]) -> None:
        if not records:
            return
        # Build embeddings with caching per record.key
        embedding_map: dict[Any, List[float]] = {}
        for record in records:
            record_id = record.id
            if record_id is None:
                raise ValueError(f"Record {record} id field is empty. Needed for embedding.")
            text_to_embed = record.key
            if text_to_embed is None:
                raise ValueError(f"Record {record} key field is empty. Needed for embedding.")
            embedding = self._get_embedding(text_to_embed)
            embedding_map[record_id] = embedding

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
        Logger.verbose(f"Inserting {len(points)} records into collection {self.name}")
        client.upsert(collection_name=self.name, points=points, wait=True)
        Logger.verbose(f"Done inserting {len(points)} records into collection {self.name}")

    def export_entities(self, limit: int = 1000) -> List[Entity]:
        client = _get_client()
        out: List[Entity] = []
        next_offset = None
        fetched = 0
        while fetched < limit:
            batch_limit = min(256, limit - fetched)
            scroll_res = client.scroll(
                collection_name=self.name,
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
                constructor_kwargs["id"] = p.id
                constructor_kwargs["key"] = p.payload["key"]
                constructor_kwargs["content"] = p.payload["content"]
                constructor_kwargs["tags"] = p.payload["tags"]
                out.append(Entity(**constructor_kwargs))
            fetched += len(points)
            if next_offset is None:
                break
        return out

    # Search
    def _search_vectors(self, query_embedding: List[float], topk: int = 5, filter: Union[str, Filter, None] = None) -> List[Tuple[Entity, float]]:
        client = _get_client()
        # Convert string filter expressions to Qdrant Filter objects
        qdrant_filter = parse_filter_string(filter)
        results = client.search(
            collection_name=self.name,
            query_vector=query_embedding,
            limit=topk,
            query_filter=qdrant_filter,
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

    def search_text(self, text: str, topk: int = 5, filter: Union[str, Filter, None] = None) -> List[Tuple[Entity, float]]:
        embedding = self._get_embedding(text)
        return self._search_vectors(embedding, topk=topk, filter=filter)

    def maintain(self) -> None:
        """Persist embedding cache associated with this collection"""
        self.embedding_cache.save()

    def init_from_file(self, saved_entities_path: str) -> None:
        from src.utils import io_utils  # local import to avoid cycles at module load
        entities = io_utils.load_yaml_into_dataclass(Path(saved_entities_path), List[Entity])
        self.insert_dataclasses(entities)


