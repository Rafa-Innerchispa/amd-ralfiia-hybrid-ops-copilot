import os
import sys
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

def download():
    print(f"Downloading tokenizer for {MODEL_NAME}...", file=sys.stderr)
    AutoTokenizer.from_pretrained(MODEL_NAME)
    print(f"Downloading model weights for {MODEL_NAME}...", file=sys.stderr)
    AutoModelForCausalLM.from_pretrained(MODEL_NAME)
    print("Download completed successfully!", file=sys.stderr)

if __name__ == "__main__":
    download()
