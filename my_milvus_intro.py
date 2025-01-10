import numpy as np
import time
import os 

from pymilvus import (
    connections,
    utility,
    FieldSchema, CollectionSchema, DataType,
    Collection,
)

filename = os.path.splitext(os.path.basename(__file__))[0]
if __name__ == "__main__" or __name__ == filename: # If the script is being run directly
    from src.Utilities.Utilities import *
    from src.Utilities.MilvusUtil import *
    from Utilities.LlamaUtil import *
else: # If the script is being imported
    from .src.Utilities.Utilities import *
    from .src.Utilities.MilvusUtil import *
    from .src.Utilities.LlamaUtil import *

fmt = "\n=== {:30} ===\n"
search_latency_fmt = "search latency = {:.4f}s"
num_entities, dim = 3000, 8

# Connect to Milvus server
initialize_server()

has = utility.has_collection("hello_milvus")
print(f"Does collection hello_milvus exist in Milvus: {has}")

