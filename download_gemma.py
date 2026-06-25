import os
os.environ["HF_HOME"] = "E:\\AI\\hf_cache"

from transformers import AutoProcessor, AutoModelForCausalLM
import torch

hf_device = "cuda" if torch.cuda.is_available() else "cpu"
model_name = "google/gemma-4-e4b-it"
print(f"Downloading and caching {model_name} to E:\\AI\\hf_cache...")

try:
    processor = AutoProcessor.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name, 
        torch_dtype=torch.float16 if hf_device=="cuda" else torch.float32, 
        low_cpu_mem_usage=True
    ).to(hf_device)
    print("Download successfully completed to E: drive!")
except Exception as e:
    print(f"Error during download: {e}")
