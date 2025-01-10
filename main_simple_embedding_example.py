import os

filename = os.path.splitext(os.path.basename(__file__))[0]
if __name__ == "__main__" or __name__ == filename: # If the script is being run directly
    from src.Utilities.Utilities import *
    from src.Utilities.MilvusUtil import *
    from src.Utilities.LlamaUtil import *
else: # If the script is being imported
    from .src.Utilities.Utilities import *
    from .src.Utilities.MilvusUtil import *
    from .src.Utilities.LlamaUtil import *

from milvus import default_server
from pymilvus import connections, utility

# Get embedding for a sample text node
print("Getting embedding for a sample text node")

sample_text1 = "Tom, in his mid-thirties, is defined by his fragile masculinity, deeply rooted in traditional gender norms. He fears appearing weak or vulnerable, triggering a need to always seem strong and in control. This insecurity makes him overly sensitive to criticism, particularly when it questions his manliness or capabilities. Tom struggles with expressing emotions, viewing them as a threat to his worthiness as a mate. His adherence to these rigid norms often leaves him emotionally isolated, unable to connect deeply with others or feel safe showing his true self."
# sample_text2 = "Heat the water"

print(f"Sample text 1: {sample_text1}")
# print(f"Sample text 2: {sample_text2}")

embedding1 = get_embedding(sample_text1)
# embedding2 = get_embedding(sample_text2)

# similarity = cosine_similarity(embedding1, embedding2)
# print(f"Similarity between the embeddings: {similarity}")

while True:
    query = input("Enter a query text: ")
    if query == "exit":
        break
    if query == "":
        continue
    query_embedding = get_embedding(query)
    print(f"Embedding length: {len(query_embedding)}")
    similarity = cosine_similarity(embedding1, query_embedding)
    print(f"Similarity between the embeddings: {similarity}\n")
