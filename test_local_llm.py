#!/usr/bin/env python3
import llama_cpp, time, json, os, re

t0 = time.time()
llm = llama_cpp.Llama(
    model_path="/home/shashi/The-Tank-Project/models/llm/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
    n_ctx=2048, n_threads=4, verbose=False,
)
print(f"TinyLlama loaded in {time.time()-t0:.1f}s")

# Test: agent-style response
prompt = (
    "<|system|>\n"
    "You are a robot agent. Respond with ONLY a JSON object.\n"
    'Example: {"action": "shell", "cmd": "uptime"}\n'
    "<|user|>\n"
    "what is the system status?\n"
    "<|assistant|>\n"
)
t1 = time.time()
resp = llm(prompt, max_tokens=150, temperature=0.2, stop=["<|user|>", "<|system|>"])
text = resp["choices"][0]["text"].strip()
print(f"Response in {time.time()-t1:.1f}s:")
print(text)
print()
print("Tokens/sec:", resp.get("usage", {}).get("prompt_tokens", 0), "prompt +", resp.get("choices", [{}])[0].get("finish_reason", "?"))
