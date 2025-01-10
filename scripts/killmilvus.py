from src.Utilities.Utilities import find_milvus_proc

running_milvus_proc = find_milvus_proc(19530)
if running_milvus_proc:
    print(f"Killing Milvus process {running_milvus_proc.pid}")
    running_milvus_proc.kill()
else:
    print("Milvus process not found")