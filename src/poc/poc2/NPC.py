from dataclasses import dataclass
import os
from typing import Dict, List, Optional

from src.core.BaseNPC import BaseNPC
from src.core.schemas.Schemas import GameSettings
from src.core.schemas.CollectionSchemas import Entity
from src.utils import Logger, io_utils
from src.utils.Logger import Level
from src.core.Constants import Role
from src.core.ResponseTypes import ChatResponse
from src.core.ConversationMemory import ConversationMemory, ConversationMemoryState
from src.poc import proj_paths, proj_settings
from src.utils import MilvusUtil

from pymilvus import Collection


@dataclass
class NPCState:
    conversation_memory: ConversationMemoryState
    system_context: str
    user_prompt_wrapper: str


@dataclass
class NPCTemplateV2:
    initial_system_context: str
    system_prompt_mandatory: Optional[str] = None
    initial_response: Optional[str] = None


class NPC(BaseNPC):
    save_paths: proj_paths.SavePaths
    template: NPCTemplateV2
    entities_cache: List[Entity]
    collection: Collection

    def __init__(self, is_new_game: bool, npc_name: str):
        self.save_paths = proj_paths.get_paths()
        game_settings = proj_settings.get_settings().game_settings
        super().__init__(game_settings=game_settings, npc_name=npc_name, is_new_game=is_new_game)

        # Load template
        self.template = io_utils.load_yaml_into_dataclass(self.save_paths.npc_template(npc_name), NPCTemplateV2)

        # Initialize conversation state
        if not is_new_game:
            self.load_state()
        else:
            self.init_state()

        # Init Milvus and entities
        self._init_vdb(is_new_game)

    # -------------------- Base overrides --------------------
    def build_system_prompt(self) -> str:
        # Top-level sections
        parts: List[str] = []

        # Base personality/context (mandatory first, then initial context)
        if self.template.system_prompt_mandatory:
            parts.append("Mandatory:\n" + self.template.system_prompt_mandatory.strip())
        parts.append("Context:\n" + self.template.initial_system_context.strip())

        # Conversation summary
        conversation_summary = self.conversation_memory.get_chat_summary_as_string()
        if conversation_summary:
            parts.append(f"Prior conversation summary:\n{conversation_summary}")

        # Top-of-mind items (goals, traits)
        top_of_mind = self._select_top_of_mind(max_per_tag=2)
        if top_of_mind:
            tom_text = "\n".join([e.content for e in top_of_mind])
            parts.append("Top of mind:\n" + tom_text)

        # Relevant knowledge from VDB (0-5 items)
        relevant_items = self._vdb_relevant_items(limit=5)
        if relevant_items:
            rel_text = "\n".join([e.content for e in relevant_items])
            parts.append("Relevant knowledge:\n" + rel_text)

        return "\n\n".join(parts) + "\n\n"

    def get_initial_response(self) -> str:
        return self.template.initial_response or ""

    def save_state(self) -> None:
        # Ensure directory exists
        os.makedirs(self.save_paths.npc_save(self.npc_name), exist_ok=True)

        # Save NPC state
        save_path = self.save_paths.npc_save_state(self.npc_name)
        current_state = NPCState(
            conversation_memory=self.conversation_memory.get_state(),
            system_context=self.template.initial_system_context,
            user_prompt_wrapper=self.user_prompt_wrapper,
        )
        io_utils.save_to_yaml_file(current_state, save_path)

        # Export VDB snapshot to YAML (as dataclasses)
        try:
            all_entities = MilvusUtil.export_dataclasses(self.collection, Entity)
            io_utils.save_to_yaml_file(all_entities, self.save_paths.npc_entities_save(self.npc_name))
        except Exception as e:
            Logger.log(f"Warning: failed to export VDB snapshot: {e}", Level.WARNING)

    def load_state(self) -> None:
        try:
            prior: NPCState = io_utils.load_yaml_into_dataclass(self.save_paths.npc_save_state(self.npc_name), NPCState)
            self.conversation_memory = ConversationMemory.from_state(prior.conversation_memory)
            # system prompt is dynamic in POC2; keep template as source of truth
            self.user_prompt_wrapper = prior.user_prompt_wrapper
        except FileNotFoundError as e:
            Logger.log(f"NPC state file not found: {e}", Level.ERROR)
            Logger.log("Starting a new game.", Level.INFO)
            self.init_state()
        except Exception as e:
            Logger.log(f"Error loading NPC state: {e}", Level.ERROR)
            raise e

    def init_state(self) -> None:
        self.conversation_memory = ConversationMemory.new_game()

    # -------------------- Milvus/VDB helpers --------------------
    def _init_vdb(self, is_new_game: bool) -> None:
        collection_name = self._collection_name()
        self.collection, seeded = MilvusUtil.init_npc_collection(
            collection_name,
            is_new_game=is_new_game,
            saved_entities_path=str(self.save_paths.npc_entities_save(self.npc_name)),
            template_entities_path=str(self.save_paths.npc_entities_template(self.npc_name)),
            model_cls=Entity,
        )
        if seeded:
            self.entities_cache = seeded
        else:
            self.entities_cache = self._load_seed_entities(is_new_game)

    def _collection_name(self) -> str:
        return f"poc2_{self.save_paths.save_name}_{self.npc_name}"

    def _create_collection(self, name: str) -> None:
        # Handled by MilvusUtil.ensure_collection_basic; left for compatibility
        pass

    def _load_seed_entities(self, is_new_game: bool) -> List[Entity]:
        # Choose source: saved entities if not new and present, else template
        saved_path = self.save_paths.npc_entities_save(self.npc_name)
        template_path = self.save_paths.npc_entities_template(self.npc_name)
        source = None
        if (not is_new_game) and os.path.exists(saved_path):
            source = saved_path
        elif os.path.exists(template_path):
            source = template_path
        else:
            return []

        try:
            ents: List[Entity] = io_utils.load_yaml_into_dataclass(source, List[Entity])
        except Exception as e:
            Logger.log(f"Failed to load entities from {source}: {e}", Level.ERROR)
            ents = []

        # If we seeded from template on a new game, write snapshot to saves
        if is_new_game and source == template_path and ents:
            os.makedirs(self.save_paths.npc_save(self.npc_name), exist_ok=True)
            io_utils.save_to_yaml_file(ents, saved_path)
        return ents

    def _insert_entities(self, entities: List[Entity]) -> None:
        # Insert handled by MilvusUtil helpers in init; not used here
        pass

    def _export_entities_from_vdb(self) -> List[Entity]:
        # Query all docs (simple expression using id)
        try:
            results = self.collection.query(expr="id >= 0", output_fields=["key", "content", "tags"], limit=100000)
        except Exception:
            results = []
        ents: List[Entity] = []
        for r in results:
            tags = [t for t in r["tags"].split(",") if t]
            ents.append(Entity(key=r["key"], content=r["content"], tags=tags))
        return ents

    def _select_top_of_mind(self, max_per_tag: int = 2) -> List[Entity]:
        if not self.entities_cache:
            return []
        top: List[Entity] = []
        # Pick a few goals and traits deterministically (first come)
        goals = [e for e in self.entities_cache if "goals" in e.tags][:max_per_tag]
        traits = [e for e in self.entities_cache if "traits" in e.tags][:max_per_tag]
        top.extend(goals)
        top.extend(traits)
        return top

    def _vdb_relevant_items(self, limit: int = 5) -> List[Entity]:
        try:
            queries: List[List[float]] = []
            # Query A: last user message
            last_user_message = None
            for msg in reversed(self.conversation_memory.chat_memory):
                if msg.role == Role.user:
                    last_user_message = msg.content
                    break
            if last_user_message:
                queries.append(MilvusUtil.get_embedding(last_user_message, model=MilvusUtil.text_embedding_3_small))

            # Query B: context (last N messages + summary or a slice of template context)
            N = 4
            last_msgs = [m.content for m in self.conversation_memory.chat_memory[-N:]]
            ctx_parts = []
            if last_msgs:
                ctx_parts.append("\n".join(last_msgs))
            summary = self.conversation_memory.get_chat_summary_as_string()
            if summary and summary != "(No summary available.)":
                ctx_parts.append(summary)
            else:
                ctx_parts.append(self.template.initial_system_context[:800])
            ctx_text = "\n".join(ctx_parts)
            if ctx_text:
                queries.append(MilvusUtil.get_embedding(ctx_text, model=MilvusUtil.text_embedding_3_small))

            if not queries:
                return []

            hits = MilvusUtil.search_relevant_records(self.collection, queries, model_cls=Entity, topk=limit, metric="COSINE")
            return hits
        except Exception as e:
            Logger.log(f"VDB relevant search failed: {e}", Level.WARNING)
            return []


