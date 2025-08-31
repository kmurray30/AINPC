import os
from milvus import default_server
import psutil
from pymilvus import connections
from pymilvus import FieldSchema, CollectionSchema, DataType, Collection, utility
import openai
from openai import OpenAI
import ollama
from typing import List, Dict, Optional, Tuple, Type, get_origin, get_args, Union, TypeVar
from dataclasses import fields as dc_fields, is_dataclass, asdict
from pathlib import Path
import yaml
import numpy as np

from src.utils import Logger
from src.utils.Utilities import load_dotenv

# Load the OpenAI API key from the .env file
# print("Loading OpenAI API key")
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
openAIClient = OpenAI()

# Platforms:
_openai_ = "openai"
_ollama_ = "ollama"

# Embedding models
text_embedding_3_small = "text-embedding-3-small"
text_embedding_3_large = "text-embedding-3-large"
mxbai_embed_large = "mxbai-embed-large"
nomic_embed_text = "nomic-embed-text"
llama3 = "llama3"
llama3_70b = "llama3:70b"

embedding_models = {
    _openai_: {
        text_embedding_3_small: 1536,
        text_embedding_3_large: 3072,
    },
    _ollama_: {
        mxbai_embed_large: 1024,
        nomic_embed_text: 768,
        llama3: 4096,
        llama3_70b: 8192,
    }
}

def get_platform_of_model(model):
    for platform, models in embedding_models.items():
        if model in models:
            return platform
    raise Exception(f"Model {model} not found. Available models: {list(embedding_models.keys())}")

def get_dimensions_of_model(model):
    for platform, models in embedding_models.items():
        if model in models:
            return models[model]
    raise Exception(f"Model {model} not found. Available models: {list(embedding_models.keys())}")

# model options: text-embedding-3-small (1536 dimensions), text-embedding-3-large (3072 dimensions)
def get_embedding(text, model=text_embedding_3_small, dimensions=None):
    if get_platform_of_model(model) == _openai_:
        if dimensions:
            embedding = openAIClient.embeddings.create(input = [text], model=model, dimensions=dimensions).data[0].embedding
        else:
            embedding = openAIClient.embeddings.create(input = [text], model=model).data[0].embedding
        return embedding
    elif get_platform_of_model(model) == _ollama_:
        embedding = ollama.embeddings(prompt=text,model=model)["embedding"]
        return embedding
    else:
        list_of_models = [model for models in embedding_models.values() for model in models]
        raise Exception(f"Model {model} not found. Available models: {list_of_models}")

def cosine_similarity(embedding1, embedding2):
    # Convert lists to numpy arrays
    embedding1 = np.array(embedding1)
    embedding2 = np.array(embedding2)
    
    # Compute the cosine similarity
    dot_product = np.dot(embedding1, embedding2)
    norm_embedding1 = np.linalg.norm(embedding1)
    norm_embedding2 = np.linalg.norm(embedding2)
    similarity = dot_product / (norm_embedding1 * norm_embedding2)
    
    return similarity

def find_milvus_proc(port):
    """Return a list of processes listening on the given port."""
    Logger.verbose(f"Checking for running processes listening on port {port}")
    milvus_proc: psutil.Process = None
    last_proc: psutil.Process = None
    for proc in psutil.process_iter(['pid', 'name']):
        last_proc = proc
        try:
            # Use net_connections (connections is deprecated in newer psutil)
            get_conns = getattr(proc, 'net_connections', None) or getattr(proc, 'connections', None)
            for conn in get_conns(kind='inet'):
                if conn.laddr.port == port:
                    Logger.verbose(f"Found running process {proc.info['name']} {proc.info['pid']} on port {port}")
                    if 'milvus' in proc.info['name']:
                        milvus_proc = proc
                    else:
                        # Throw an exception if the process is not Milvus
                        raise Exception(f"Process {proc.info['name']} is running on port {port} (expected Milvus)")
        except psutil.AccessDenied:
            pass
        except psutil.ZombieProcess:
            # Kill the zombie process
            Logger.verbose(f"Killing zombie process {last_proc.pid}")
            last_proc.kill()
            # Check if the process is still alive
            if last_proc.is_running():
                Logger.verbose(f"Zombie process {last_proc.pid} is still alive")
        except Exception as e:
            Logger.verbose(f"Error: {e}")
            Logger.verbose(f"Error type: {type(e)}")
            pass

    # Return the port of the Milvus process, if found
    return milvus_proc

def initialize_server(milvus_port=19530, restart_milvus_server=False):
    # Clear any existing connections
    disconnect_server()

    # Check if the Milvus server is already running
    running_milvus_proc = find_milvus_proc(milvus_port)

    # Kill the Milvus process if it is running and the restart flag is set
    if running_milvus_proc and restart_milvus_server:
        Logger.verbose(f"Killing Milvus process {running_milvus_proc.pid}")
        running_milvus_proc.kill()
        running_milvus_proc = None

    if (running_milvus_proc):
        Logger.verbose("Connecting to established Milvus server")
  
        try:
            connections.connect(
                alias="default", 
                host='localhost',
                port=milvus_port,
                timeout=10
            )
            Logger.verbose("Connected to Milvus server\n")
        except Exception as e:
            Logger.verbose(f"Connection to Milvus server failed with error: {e}")
            print(f"Killing process {running_milvus_proc.pid} and restarting Milvus server")
            running_milvus_proc.kill()
            running_milvus_proc = None
    
    if not running_milvus_proc:
        Logger.verbose("Establishing connection to Milvus server...")
        if not default_server.running:
            Logger.verbose("Milvus server is not running, starting it")
            default_server.start()
        else:
            Logger.verbose("Milvus server is already running")

        if default_server.listen_port != milvus_port:
            raise Exception(f"Milvus server is running on port {default_server.listen_port} but expected port {milvus_port}")
        # TODO: Added this because it was failing to create connection on the first run. Make sure this works on the next cold run
        if not connections.has_connection(alias="default"):
            Logger.verbose(f"Connecting to Milvus server on port {milvus_port}")
            connections.connect(
                alias="default", 
                host='localhost',
                port=milvus_port
            )
        else:
            Logger.verbose(f"Milvus server already connected on port {default_server.listen_port}")
        Logger.verbose(f"Milvus server initialized on port {default_server.listen_port}\n")


# ---------------------- Generic VDB Helpers ----------------------

def disconnect_server():
    for alias, _ in connections.list_connections():
        Logger.verbose(f"Disconnecting connection {alias}")
        connections.disconnect(alias)
        Logger.verbose(f"Removing connection {alias}")
        connections.remove_connection(alias)


def drop_collection_if_exists(name: str):
    try:
        if utility.has_collection(name):
            Logger.verbose(f"Dropping collection {name}")
            utility.drop_collection(name)
    except Exception as e:
        raise Exception(f"Failed to drop collection {name}: {e}")

def load_or_create_collection(name: str, dim: int, *, model_cls: Type, auto_id: bool = True) -> Collection:
    # Create schema from model_cls
    if not is_dataclass(model_cls):
        raise TypeError("model_cls must be a dataclass type")
    field_schemas: List[FieldSchema] = []
    for f in dc_fields(model_cls):
        fs = _py_type_to_field_schema(f.name, f.type, dim, auto_id=auto_id)
        field_schemas.append(fs)
    schema = CollectionSchema(fields=field_schemas, description=f"Collection for {model_cls.__name__}")

    # Validate there is a valid embedding and id field
    if not any(field.name == "embedding" and field.dtype == DataType.FLOAT_VECTOR for field in field_schemas):
        raise ValueError(f"No embedding field found in schema for {model_cls.__name__}. Must have an embedding field with type FLOAT_VECTOR.")
    if not any(field.name == "id" and field.dtype == DataType.INT64 for field in field_schemas):
        raise ValueError(f"No id field found in schema for {model_cls.__name__}. Must have an id field with type INT64.")
    
    # Check if the collection already exists, validate schema, and load/return if it does
    if utility.has_collection(name):
        Logger.verbose(f"Collection {name} already exists")
        # Validate compatibility with existing schema
        collection = Collection(name)
        existing_schema = collection.schema
        if existing_schema != schema:
            raise ValueError(f"Collection {name} already exists with different schema")
        # Ensure there is an embedding field
        if not any(field.name == "embedding" and field.dtype == DataType.FLOAT_VECTOR for field in existing_schema.fields):
            raise ValueError(f"No embedding field found in schema for {model_cls.__name__}. Must have an embedding field with type FLOAT_VECTOR.")
        collection.load()
        return collection

    # Create collection if it doesn't exist
    Logger.verbose(f"Creating collection {name}")
    return _create_collection(name, schema)


def _create_collection(name: str, schema: CollectionSchema) -> Collection:
    collection = Collection(name=name, schema=schema)
    collection.create_index(
            field_name="embedding",
            index_params={
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200},
            },
        )
    # Ensure collection is loaded for immediate search/query
    collection.load()
    return collection
    

def _unwrap_optional(py_type):
    origin = get_origin(py_type)
    args = get_args(py_type)
    if origin is Union and type(None) in args and len(args) == 2:
        # typing.Optional[T] is Union[T, NoneType]
        return args[0] if args[1] is type(None) else args[1]
    return py_type


def _py_type_to_field_schema(field_name: str, py_type, vector_dim: int, auto_id: bool = True) -> FieldSchema:
    py_type = _unwrap_optional(py_type)
    origin = get_origin(py_type)
    args = get_args(py_type)

    if field_name == "id":
        if py_type is not int:
            raise ValueError(f"id field must be of type int, got {py_type}")
        return FieldSchema(name=field_name, dtype=DataType.INT64, is_primary=True, auto_id=auto_id)
    
    if field_name == "embedding":
        if origin not in (list, List) or args[0] is not float:
            raise ValueError(f"embedding field must be of type list of floats, got {py_type}")
        return FieldSchema(name=field_name, dtype=DataType.FLOAT_VECTOR, dim=vector_dim)

    if py_type is str:
        return FieldSchema(name=field_name, dtype=DataType.VARCHAR, max_length=4096)
    if py_type is int:
        return FieldSchema(name=field_name, dtype=DataType.INT64)
    if py_type is float:
        return FieldSchema(name=field_name, dtype=DataType.DOUBLE)
    if py_type is bool:
        return FieldSchema(name=field_name, dtype=DataType.BOOL)
    if origin in (list, List) and args and args[0] is str:
        # store CSV in VARCHAR
        return FieldSchema(name=field_name, dtype=DataType.VARCHAR, max_length=4096)
    if origin in (list, List) and args and args[0] is float:
        return FieldSchema(name=field_name, dtype=DataType.FLOAT_VECTOR, dim=vector_dim)

    # Fallback
    return FieldSchema(name=field_name, dtype=DataType.VARCHAR, max_length=4096)


T = TypeVar("T")

def _to_column_value(value, field_schema: FieldSchema):
    # Convert Python value to what Milvus expects based on schema dtype
    if field_schema.dtype == DataType.VARCHAR:
        # If value is a list (e.g., tags), store as CSV
        if isinstance(value, list):
            return ",".join(value)
        return "" if value is None else str(value)
    if field_schema.dtype == DataType.FLOAT_VECTOR:
        # Expected to be a list[float]
        return value or []
    # Primitive mappings
    if field_schema.dtype == DataType.INT64:
        return None if value is None else int(value)
    if field_schema.dtype == DataType.DOUBLE:
        return None if value is None else float(value)
    if field_schema.dtype == DataType.BOOL:
        return None if value is None else bool(value)
    return value


def insert_dataclasses(
    collection: Collection,
    records: List[T],
    *,
    embed_model: str = text_embedding_3_small,
    embed_text_attr: str = "key",
):
    if not records:
        return

    # Ensure records are dataclass instances
    if not all(is_dataclass(r) for r in records):
        raise ValueError("All records must be dataclass instances")
    
    # Ensure all records have an embedding
    if not all(hasattr(r, "embedding") for r in records):
        raise ValueError("All records must have an embedding field, even if empty")
    
    # Ensure all records have an embedding
    if not all(hasattr(r, embed_text_attr) for r in records):
        raise ValueError(f"All records must have a {embed_text_attr} field (specified by embed_text_attr argument), even if empty")

    # Ensure all records have an id IF auto_id is false
    is_auto_id = collection.schema.auto_id
    if not is_auto_id:
        if not all(hasattr(r, "id") and r.id is not None for r in records):
            raise ValueError("All records must have an id field")
    
    # Embed text
    for r in records:
        if not getattr(r, "embedding"):
            text = getattr(r, embed_text_attr, None)
            if text is None:
                raise ValueError(f"Record {r} {embed_text_attr} field is empty. Needed for embedding.")
            Logger.verbose(f"Embedding text: {text}")
            embedding = get_embedding(text, model=embed_model)
            setattr(r, "embedding", embedding)
    
    # Build column arrays matching collection schema (skip auto-id primary)
    columns: List[List] = []
    for f in collection.schema.fields:
        if f.is_primary and getattr(f, "auto_id", False): # Skip auto-id primary
            continue
        col_vals: List = []
        for _, r in enumerate(records):
            value = getattr(r, f.name, None)
            col_vals.append(_to_column_value(value, f))
        columns.append(col_vals)

    Logger.verbose(f"Inserting {len(records)} records into collection {collection.name}")
    collection.insert(columns)
    collection.flush()
    Logger.verbose(f"Done inserting {len(records)} records into collection {collection.name}")


def export_dataclasses(collection: Collection, model_cls: Type[T], limit: int = 100000) -> List[T]:
    # Ensure T is a dataclass
    if not is_dataclass(model_cls):
        raise ValueError("model_cls must be a dataclass type")

    # Ensure loaded - check if collection is already loaded before loading
    from pymilvus import utility
    load_state = utility.load_state(collection.name)
    if hasattr(load_state, 'state'):
        # Newer pymilvus API
        if load_state.state != utility.State.Loaded:
            collection.load()
    else:
        # Older pymilvus API - LoadState object itself indicates status
        if str(load_state) != 'Loaded':
            collection.load()
    
    # Prepare fields to fetch (exclude embedding; Milvus may not return vectors via query)
    fetch_fields = [f.name for f in collection.schema.fields]
    # Milvus has a max query window; cap to safe value
    MAX_WINDOW = 16384
    eff_limit = min(limit, MAX_WINDOW)
    
    # Query with proper error handling
    if collection.num_entities == 0:
        results = []
    else:
        results = collection.query(expr="id >= 0", output_fields=fetch_fields, limit=eff_limit)
    out: List[T] = []
    for r in results:
        out.append(model_cls(**r))
    return out


def search_relevant_records(
    collection: Collection,
    query_embedding: List[float],
    *,
    model_cls: Type[T],
    topk: int = 5,
    metric: str = "COSINE",
) -> List[Tuple[T, float]]:
    """
    Search for relevant records in a Milvus collection using a single query embedding.
    
    Args:
        collection: The Milvus collection to search in
        query_embedding: Single embedding vector to search with
        model_cls: Dataclass type to return results as
        topk: Maximum number of results to return
        metric: Distance metric to use (COSINE, L2, etc.)
    
    Returns:
        List of tuples containing (dataclass_instance, similarity_score)
    """
    # Ensure collection is loaded before searching
    load_state = utility.load_state(collection.name)
    if hasattr(load_state, 'state'):
        # Newer pymilvus API - check state attribute
        if load_state.state != utility.State.Loaded:
            collection.load()
    else:
        # Older pymilvus API - LoadState object itself indicates status
        if str(load_state) != 'Loaded':
            collection.load()
    
    # Build output fields for dataclass (exclude embedding field)
    output_fields = [field.name for field in dc_fields(model_cls) if field.name != "embedding"]
    
    # Identify fields that are List[str] but stored as comma-separated strings
    list_string_field_names = {
        field.name for field in dc_fields(model_cls) 
        if get_origin(field.type) in (list, List) and 
        (get_args(field.type) and get_args(field.type)[0] is str)
    }
    
    # Perform the search
    search_results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param={"metric_type": metric, "params": {"ef": 64}},
        limit=topk,
        output_fields=output_fields,
    )
    
    # Process search results into dataclass instances with similarity scores
    result_records: List[Tuple[T, float]] = []
    for result_batch in search_results:
        for hit in result_batch:
            # Build keyword arguments for dataclass constructor
            constructor_kwargs = {}
            for field_name in output_fields:
                field_value = hit.entity.get(field_name)
                
                # Handle List[str] fields that are stored as comma-separated strings
                if field_name in list_string_field_names and isinstance(field_value, str):
                    constructor_kwargs[field_name] = [tag.strip() for tag in field_value.split(",") if tag.strip()]
                else:
                    constructor_kwargs[field_name] = field_value
            
            # Ensure embedding field is present (set to None since we don't retrieve it)
            if any(field.name == "embedding" for field in dc_fields(model_cls)):
                constructor_kwargs["embedding"] = None
            
            # Create dataclass instance and add to results with similarity score
            dataclass_instance = model_cls(**constructor_kwargs)
            similarity_score = hit.score
            result_records.append((dataclass_instance, similarity_score))
    
    return result_records


def multi_search_relevant_records(
    collection: Collection,
    queries_embeddings: List[List[float]],
    *,
    model_cls: Type[T],
    topk: int = 5,
    metric: str = "COSINE",
) -> List[Tuple[T, float]]:
    """
    Search for relevant records using multiple query embeddings and merge results.
    Deduplicates results based on key field or id field, keeping the highest similarity score.
    
    Args:
        collection: The Milvus collection to search in
        queries_embeddings: List of embedding vectors to search with
        model_cls: Dataclass type to return results as
        topk: Maximum number of results to return (total across all queries)
        metric: Distance metric to use (COSINE, L2, etc.)
    
    Returns:
        List of unique tuples containing (dataclass_instance, highest_similarity_score)
    """
    if not queries_embeddings:
        return []
    
    # Track seen records to avoid duplicates, keeping track of best scores
    seen_record_ids = {}  # Maps unique_id -> (record, best_score)
    merged_results: List[Tuple[T, float]] = []
    
    # Get output fields to determine deduplication strategy
    output_fields = [field.name for field in dc_fields(model_cls) if field.name != "embedding"]
    
    # Search with each query embedding
    for query_embedding in queries_embeddings:
        # Use single search function for each query
        query_results = search_relevant_records(
            collection=collection,
            query_embedding=query_embedding,
            model_cls=model_cls,
            topk=topk,
            metric=metric
        )
        
        # Process results and deduplicate
        for record, similarity_score in query_results:
            # Determine unique identifier for deduplication
            # Prefer key field if available, otherwise use id
            unique_identifier = None
            if "key" in output_fields:
                unique_identifier = getattr(record, "key", None)
            
            if unique_identifier is None:
                unique_identifier = getattr(record, "id", None)
            
            # Check if we've seen this record before
            if unique_identifier in seen_record_ids:
                # Keep the record with the higher similarity score
                existing_record, existing_score = seen_record_ids[unique_identifier]
                if similarity_score > existing_score:
                    seen_record_ids[unique_identifier] = (record, similarity_score)
            else:
                # New record, add it to our tracking
                seen_record_ids[unique_identifier] = (record, similarity_score)
    
    # Convert to final result list, sorted by similarity score (highest first)
    merged_results = sorted(seen_record_ids.values(), key=lambda x: x[1], reverse=True)
    
    # Limit to topk results
    return merged_results[:topk]


def init_npc_collection(
    collection_name: str,
    *,
    is_new_game: bool,
    saved_entities_path: str,
    template_entities_path: str,
    embed_model: str = text_embedding_3_small,
    model_cls: Optional[Type[T]] = None,
    embed_text_attr: str = "key",
) -> (Collection, Optional[List[T]]):
    """Initialize a Milvus collection for the given dataclass type.
    Returns (collection, seeded_records_or_None) where seeded records are instances of model_cls.
    """
    from src.utils import io_utils  # local import to avoid cycles at module load

    if model_cls is None or not is_dataclass(model_cls):
        raise TypeError("model_cls must be a dataclass type")

    initialize_server()
    col = load_or_create_collection(collection_name, get_dimensions_of_model(embed_model), model_cls=model_cls)

    seeded: Optional[List[T]] = None
    if col.num_entities == 0:
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
                    # Snapshot to saves if seeded from template on new game
                    if is_new_game and source == template_entities_path:
                        try:
                            os.makedirs(os.path.dirname(saved_entities_path), exist_ok=True)
                            io_utils.save_to_yaml_file(records, Path(saved_entities_path))
                        except Exception:
                            pass
            except Exception:
                pass
        # Ensure loaded for search
        col.load()
    return col, seeded