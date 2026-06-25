import os
os.environ["HF_HOME"] = r"c:\Project\AkasicDB\.cache\huggingface_cache"

from transformers import AutoProcessor, AutoModelForCausalLM
import torch

hf_device = "cuda" if torch.cuda.is_available() else "cpu"
model_name = "google/gemma-4-e4b-it"
print(f"Downloading and caching {model_name} to {os.environ.get('HF_HOME')}...")

import time
import traceback

while True:
    try:
        print(f"Attempting to download and cache {model_name}...")
        processor = AutoProcessor.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name, 
            torch_dtype=torch.float16 if hf_device=="cuda" else torch.float32, 
            low_cpu_mem_usage=True
        ).to(hf_device)
        print("Download successfully completed!")
        break
    except Exception as e:
        traceback.print_exc()
        print(f"Error during download: {e}. Retrying in 10 seconds...")
        time.sleep(10)
