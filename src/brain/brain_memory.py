from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, List

from src.core.ResponseTypes import ChatResponse
from src.core.Agent import Agent
from src.core.schemas.CollectionSchemas import Entity
from src.utils import Logger, Utilities
from src.utils.QdrantCollection import QdrantCollection
from src.utils import io_utils


class BrainMemory:
    collection: QdrantCollection
    TEST_DIMENSION: int = 1536
    collection_name: str

    def __init__(self, collection_name: str):
        # Bind Qdrant collection wrapper to this NPC's brain collection
        self.collection_name = collection_name
        self.collection = QdrantCollection(self.collection_name)
        self.collection.create(dim=self.TEST_DIMENSION)

    def maintain(self) -> None:
        # Persist embedding cache associated with the collection
        self.collection.maintain()

    def add_memory(self, preprocessed_user_text: str):
        rows = [
            Entity(
                key=preprocessed_user_text,
                content=preprocessed_user_text,
                tags=["memories"],
                id=int(Utilities.generate_hash_int64(preprocessed_user_text)),
            ),
        ]
        Logger.verbose(f"Updating memory with {preprocessed_user_text}")
        self.collection.insert_dataclasses(rows)

    def get_memories(self, preprocessed_user_text: str, topk: int = 5, as_str: bool = False) -> Any:
        hits = self.collection.search_text(preprocessed_user_text, topk=topk)
        Logger.verbose(f"Found {len(hits)} memories for {preprocessed_user_text}")
        # Print the memories with their similarity scores
        # Sort the hits by similarity score
        hits.sort(key=lambda x: x[1], reverse=True)
        for hit in hits:
            Logger.verbose(f"Similarity: {hit[1]}, Content: {hit[0].content}")
        Logger.verbose(f"Found {len(hits)} memories for {preprocessed_user_text}")
        if as_str:
            return "\n".join([hit[0].content for hit in hits])
        else:
            return [hit[0] for hit in hits]

    def get_all_memories(self) -> List[Entity]:
        """API method for /list command"""
        all_memories = self.collection.export_entities()
        Logger.verbose(f"All memories:")
        return all_memories

    def load_entities_from_template(self, template_path: Path) -> None:
        """API method for /load command"""
        if not template_path.suffix == ".yaml":
            raise ValueError("File must be a yaml file")

        # template_path = os.path.join(os.path.dirname(__file__), template_path)
        if not template_path.exists():
            raise FileNotFoundError(f"File {template_path} does not exist")

        entities_strs = io_utils.load_yaml_into_dataclass(template_path, List[str])
        entities = [
            Entity(
                key=e,
                content=e,
                tags=["memories"],
                id=int(Utilities.generate_hash_int64(e)),
            ) for e in entities_strs
        ]
        self.collection.insert_dataclasses(entities)
        Logger.verbose(f"Loaded {len(entities)} entities from {template_path}")

    def clear_all_memories(self) -> None:
        """API method for /clear command"""
        self.collection.drop_if_exists()
        self.collection.create(dim=self.TEST_DIMENSION)