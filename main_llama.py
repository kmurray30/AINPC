import os
import openai
from dotenv import load_dotenv
from milvus import default_server
from llama_index.llms.openai import OpenAI

from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings

embed_model = OpenAIEmbedding(embed_batch_size=10, model="text-embedding-3-small")
Settings.embed_model = embed_model

# from llama_index.core.agent import ReActAgent
# from llama_index.llms.openai import OpenAI
# llm = OpenAI(model="gpt-3.5-turbo-0613")

# agent = ReActAgent.from_tools(
#     query_engine_tools,
#     llm=llm,
#     verbose=True,
#     # context=context
# )

filename = os.path.splitext(os.path.basename(__file__))[0]
if __name__ == "__main__" or __name__ == filename: # If the script is being run directly
    from src.Utilities.Utilities import *
    from src.Utilities.MilvusUtil import *
    from Utilities.LlamaUtil import *
else: # If the script is being imported
    from .src.Utilities.Utilities import *
    from .src.Utilities.MilvusUtil import *
    from .src.Utilities.LlamaUtil import *

# Args (temp until we have a proper CLI)
reset_vector_store = True
restart_milvus_server = False

# Constants
milvus_port = 19530

# Global variables
node_graph = []

# Load the OpenAI API key from the .env file
print("Loading OpenAI API key")
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
chatGptClient = OpenAI()

data_files_path = get_path_from_project_root("entities/")

# Initialize the chat messages
chatGptMessages = [
    {"role": "system", "content": "You are a helpful assistant."}
]

def on_exit():
    # Stop and clean up Milvus server if it is running
    if (default_server.running):
        print("Stopping Milvus server")
        default_server.stop()
        default_server.cleanup()
    print("Exiting the script")

### Begin execution here

# Set up exit handling
# atexit.register(on_exit)

# Start milvus server if it is not already running, otherwise connect to the running server
initialize_server(milvus_port, restart_milvus_server)

# If reset is set to True, the store will be reset
storage_path = get_path_from_project_root("storage")
if (reset_vector_store and not is_dir_empty(storage_path)):
    print("Resetting storage directory")
    os.system(f"rm -rf {get_path_from_project_root('storage')}")

# Load vectors
query_engine = load_vectors_into_query_engine("emotions")

print("Ask me anything!")
while(True):
    inputStr = input()
    if (inputStr == "exit"):
        break
    if (inputStr == ""):
        continue
    response = query_engine.query(inputStr)
    source_nodes = response.source_nodes
    for node in source_nodes:
        print()
        print(node)
    print("\nAsk me anything else! (or type 'exit' to quit)")