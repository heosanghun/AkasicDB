import os
os.environ["HF_HOME"] = r"c:\Project\AkasicDB\.cache\huggingface_cache"
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
import threading

hf_device = "cuda" if torch.cuda.is_available() else "cpu"
model_name = "Qwen/Qwen1.5-1.8B-Chat"
print(f"Loading {model_name} on {hf_device}...")
hf_tokenizer = AutoTokenizer.from_pretrained(model_name)
hf_model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, low_cpu_mem_usage=True).to(hf_device)

prompt = "You are an intelligent Port Yard Copilot. Answer the question based on the context.\nContext: Container_15 is delayed.\n\nQuestion: What is the status of Container 15?\nAnswer:"
inputs = hf_tokenizer(prompt, return_tensors="pt").to(hf_device)
streamer = TextIteratorStreamer(hf_tokenizer, skip_prompt=True, skip_special_tokens=True)

kwargs = dict(inputs, streamer=streamer, max_new_tokens=50)
thread = threading.Thread(target=hf_model.generate, kwargs=kwargs)
thread.start()

print("Output:")
for text in streamer:
    print(text, end="", flush=True)
print("\nDone.")
