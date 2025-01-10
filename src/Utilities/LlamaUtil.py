import json
import os
from typing import Dict
from llama_index.core import (StorageContext,
                              VectorStoreIndex, load_index_from_storage)
from llama_index.core.schema import TextNode
from llama_index.vector_stores.milvus import MilvusVectorStore
from milvus import default_server
import traceback

filename = os.path.splitext(os.path.basename(__file__))[0]
if __name__ == "__main__" or __name__ == filename: # If the script is being run directly
    from Utilities import *
else: # If the script is being imported
    from .Utilities import *

def get_vector_and_content_nodes_from_json(data):
    vector_nodes: list[TextNode] = []
    content_nodes: list[Dict] = []

    for entity in data:
        id = generate_guid()
        vector_data = entity.get('vector_node')
        vector_node = TextNode(
            text=json.dumps(vector_data),
            id_=id,
            metadata=data
        )

        content_data = entity.get('content_node')
        content_node = {"id": id, "content": content_data}

        vector_nodes.append(vector_node)
        content_nodes.append(content_node)

    return (vector_nodes, content_nodes)

# Find a list of eligible entities in the entities directory
def load_nodes_from_entity_name(filename):
    file_path = f"entities/{filename}.json"
    abs_file_path = get_path_from_project_root(file_path)
    # if file not found
    if not os.path.exists(abs_file_path):
        raise Exception(f"File {file_path} does not exist")
    with open(abs_file_path, 'r') as f:
        data: dict = json.load(f)
    (vector_nodes, content_nodes) = get_vector_and_content_nodes_from_json(data)
    return (vector_nodes, content_nodes)

def load_vectors_into_query_engine(storeName, reset_vector_store=False):
    # Try loading existing index from storage
    index_loaded = False
    if not reset_vector_store:
        try:
            print(f"Attempting to recreate vector store from storage for {storeName}")
            vector_store = MilvusVectorStore(host="localhost", port=default_server.listen_port, dim=1536, collection_name=storeName, overwrite=False)
            persist_dir=get_path_from_project_root(f"storage/{storeName}")
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                persist_dir=persist_dir
            )
            print(f"Loading index from storage location {persist_dir}")
            index = load_index_from_storage(storage_context)

            index_loaded = True
        except Exception as e:
            print(f"Existing vector store not present for {storeName} with error: {e}")
            traceback.print_exc()
            index_loaded = False

    # If index not loaded, create a new index
    if not index_loaded:
        # load data
        (vector_nodes, content_nodes) = load_nodes_from_entity_name(storeName)

        # build index
        print("Initializing vector store")
        vector_store = MilvusVectorStore(host="localhost", port=default_server.listen_port, dim=1536, collection_name=storeName, overwrite=True)
        print("Initializing storage context")
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        print("Building index")
        index = VectorStoreIndex(vector_nodes, storage_context=storage_context)

        # persist index
        print("Persisting index")
        index.storage_context.persist(persist_dir=get_path_from_project_root(f"storage/{storeName}"))

    # Create query engine
    print("Creating query engine from index\n")
    query_engine = index.as_query_engine(similarity_top_k=3)

    return query_engine
