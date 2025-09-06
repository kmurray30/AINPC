import os
import psutil 
from pymilvus import connections
from pymilvus import FieldSchema, CollectionSchema, DataType, Collection, utility
import openai
from openai import OpenAI
import ollama
from typing import Any, Final, List, Optional, Tuple, Type, get_origin, get_args, Union, TypeVar
from dataclasses import fields as dc_fields, is_dataclass
from pathlib import Path
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