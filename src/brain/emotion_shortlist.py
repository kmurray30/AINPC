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


class EmotionShortlist:
    collection: QdrantCollection
    collection_name: str = "emotion_shortlist"
    TEST_DIMENSION: int = 1536

    def __init__(self):
        # Bind Qdrant collection wrapper to this NPC's brain collection
        self.collection = QdrantCollection(self.collection_name)
        self.collection.create(dim=self.TEST_DIMENSION)

    def maintain(self) -> None:
        # Persist embedding cache associated with the collection
        self.collection.maintain()

    def add_emotion(self, emotion_name: str):
        rows = [
            Entity(
                key=emotion_name,
                content=emotion_name,
                tags=None,
                id=int(Utilities.generate_hash_int64(emotion_name)),
            ),
        ]
        Logger.verbose(f"Adding emotion {emotion_name} to shortlist")
        self.collection.insert_dataclasses(rows)

    def get_emotions(self, emotional_description: str, topk: int = 5, as_str: bool = False) -> Any:
        hits = self.collection.search_text(emotional_description, topk=topk)
        Logger.verbose(f"Found {len(hits)} emotions for input '{emotional_description}'")
        # Print the memories with their similarity scores
        # Sort the hits by similarity score
        hits.sort(key=lambda x: x[1], reverse=True)
        for hit in hits:
            Logger.verbose(f"Similarity: {hit[1]}, Emotion: {hit[0].content}")
        if as_str:
            return "\n".join([hit[0].content for hit in hits])
        else:
            return [hit[0] for hit in hits]

    def get_all_emotions(self) -> List[Entity]:
        """API method for /list command"""
        all_emotions = self.collection.export_entities()
        Logger.verbose(f"All emotions:")
        return all_emotions

    def load_entities_from_template(self, template_path: Path) -> None:
        """API method for /load command"""
        if not template_path.suffix == ".yaml":
            raise ValueError("File must be a yaml file")

        # template_path = os.path.join(os.path.dirname(__file__), template_path)
        if not template_path.exists():
            raise FileNotFoundError(f"File {template_path} does not exist")

        entities = io_utils.load_yaml_into_dataclass(template_path, List[Entity])
        # Ensure each entity has an id for Qdrant
        for e in entities:
            if getattr(e, "id", None) is None:
                e.id = int(Utilities.generate_hash_int64(e.content))
        self.collection.insert_dataclasses(entities)
        Logger.verbose(f"Loaded {len(entities)} entities from {template_path}")

    def clear_all_emotions(self) -> None:
        """API method for /clear command"""
        self.collection.drop_if_exists()
        self.collection.create(dim=self.TEST_DIMENSION)