from huggingface_hub import hf_hub_download
import os

# Using an open mirror (Bartowski) to avoid gate/token issues
model_id = "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF"
filename = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
local_dir = "/home/brain_ai/.lmstudio/models/unsloth/Meta-Llama-3.1-8B-Instruct-GGUF"

print(f"Starting download of {filename} to {local_dir}...")
try:
    path = hf_hub_download(
        repo_id=model_id,
        filename=filename,
        local_dir=local_dir,
        local_dir_use_symlinks=False
    )
    print(f"SUCCESS: Model downloaded to {path}")
except Exception as e:
    print(f"ERROR: {e}")