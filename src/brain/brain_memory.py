from dataclasses import dataclass, field
import os
from typing import Any, List

from src.core.ResponseTypes import ChatResponse
from src.core.Agent import Agent
from src.core.schemas.CollectionSchemas import Entity
from src.utils import Logger, Utilities
from src.utils.QdrantCollection import QdrantCollection


class BrainMemory:
    collection: QdrantCollection
    collection_name: str = "simple_brain"
    TEST_DIMENSION: int = 1536

    def __init__(self):
        # Bind Qdrant collection wrapper to this NPC's brain collection
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
                id=int(Utilities.generate_uuid_int64()),
            ),
        ]
        Logger.verbose(f"Updating memory with {preprocessed_user_text}")
        self.collection.insert_dataclasses(rows)

    def get_memories(self, preprocessed_user_text: str, topk: int = 5, as_str: bool = False) -> Any:
        hits = self.collection.search_text(preprocessed_user_text, topk=topk)
        Logger.verbose(f"Found {len(hits)} memories for {preprocessed_user_text}")
        # Print the memories with their similarity scores
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

    def load_entities_from_template(self, template_path: str) -> None:
        """API method for /load command"""
        if not template_path.endswith(".yaml"):
            raise ValueError("File must be a yaml file")

        # template_path = os.path.join(os.path.dirname(__file__), template_path)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"File {template_path} does not exist")

        from src.brain import template_processor
        entities = template_processor.template_to_entities_simple(template_path)
        # Ensure each entity has an id for Qdrant
        for e in entities:
            if getattr(e, "id", None) is None:
                e.id = int(Utilities.generate_uuid_int64())
        self.collection.insert_dataclasses(entities)
        Logger.verbose(f"Loaded {len(entities)} entities from {template_path}")

    def clear_brain_memory(self) -> None:
        """API method for /clear command"""
        self.collection.drop_if_exists()
        self.collection.create(dim=self.TEST_DIMENSION)