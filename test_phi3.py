#!/usr/bin/env python3
import llama_cpp, time

t0 = time.time()
llm = llama_cpp.Llama(
    model_path="/home/shashi/The-Tank-Project/models/llm/phi-3-mini-4k-instruct-q4.gguf",
    n_ctx=4096, n_threads=4, verbose=False,
)
print(f"Phi-3 Mini loaded in {time.time()-t0:.1f}s")

prompt = (
    "<|system|>\n"
    "You are a robot agent. Respond with ONLY a JSON object.\n"
    '{"action": "shell", "cmd": "<command>"}\n'
    "<|user|>\n"
    "what is the system status?\n"
    "<|assistant|>\n"
)
t1 = time.time()
resp = llm(prompt, max_tokens=200, temperature=0.1, stop=["<|user|>", "<|system|>"])
text = resp["choices"][0]["text"].strip()
print(f"Response in {time.time()-t1:.1f}s:")
print(text)
