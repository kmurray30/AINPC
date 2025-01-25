import os
from milvus import default_server
from pymilvus import connections
import openai
from openai import OpenAI
import ollama

filename = os.path.splitext(os.path.basename(__file__))[0]
if __name__ == "__main__" or __name__ == filename: # If the script is being run directly
    from Utilities import *
else: # If the script is being imported
    from .Utilities import *

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
    print(f"Checking for running processes listening on port {port}")
    milvus_proc: psutil.Process = None
    last_proc: psutil.Process = None
    for proc in psutil.process_iter(['pid', 'name']):
        last_proc = proc
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    print(f"Found running process {proc.info['name']} on port {port}")
                    if 'milvus' in proc.info['name']:
                        milvus_proc = proc
                    else:
                        # Throw an exception if the process is not Milvus
                        raise Exception(f"Process {proc.info['name']} is running on port {port} (expected Milvus)")
        except psutil.AccessDenied:
            pass
        except psutil.ZombieProcess:
            # Kill the zombie process
            print(f"Killing zombie process {last_proc.pid}")
            last_proc.kill()
            # Check if the process is still alive
            if last_proc.is_running():
                print(f"Zombie process {last_proc.pid} is still alive")
        except Exception as e:
            print(f"Error: {e}")
            print(f"Error type: {type(e)}")
            pass

    # Return the port of the Milvus process, if found
    return milvus_proc

def initialize_server(milvus_port=19530, restart_milvus_server=False):
    # Check if the Milvus server is already running
    running_milvus_proc = find_milvus_proc(milvus_port)

    # Kill the Milvus process if it is running and the restart flag is set
    if running_milvus_proc and restart_milvus_server:
        print(f"Killing Milvus process {running_milvus_proc.pid}")
        running_milvus_proc.kill()
        running_milvus_proc = None

    if (running_milvus_proc):
        print("Connecting to established Milvus server")
  
        connections.connect(
            alias="default", 
            host='localhost',
            port=milvus_port
        )
        print("Connected to Milvus server\n")
    else:
        print("Starting Milvus server")
        default_server.start()
        # TODO: Added this because it was failing to create connection on the first run. Make sure this works on the next cold run
        connections.connect(
            alias="default", 
            host='localhost',
            port=milvus_port
        )
        print(f"Milvus server initialized on port {default_server.listen_port}\n")