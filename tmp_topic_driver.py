#!/usr/bin/env python3
"""Bulk topic filler for the MediGyaan question bank.

Loop: fetch a batch of rows needing a topic -> classify each stem with FREE
OpenRouter models only (rotate models on 429/errors) -> one guarded save call.

The shared host rate-bans IPs quickly, so pacing is deliberately gentle:
1 fetch + 1 save per iteration, long backoff on failures. Resumable (the DB
query skips rows that already have topics), so re-running continues.

Runs on the VPS where the OpenRouter key lives (worker.env).
"""
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://medigyaan.xyz/Neurons/api"
SIG = "EduLabsRTM_Secure_v1_2026"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

FREE_MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "minimax/minimax-m2.7:free",
    "z-ai/glm-5.2:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3.5-lightning:free",
    "minimax/minimax-m3:free",
    "thinkingmachines/inkling-small:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
]

PROMPT = (
    "You classify exam MCQs by the single core topic they test.\n"
    "For each indexed question below reply with ONE concise topic label (1-4 words, e.g. "
    '"Severe acute malnutrition", "Ohm law", "Contract consideration", "Hematologic malignancy"). '
    "If the stem references an image, classify by the text. "
    "Use the disease/drug/concept named in the stem.\n"
    "Reply with EXACTLY the JSON object {\"items\":[{\"index\":0,\"topic\":\"...\"}, ...]} "
    "using the same indices as the numbered questions. No markdown fences, no commentary.\n\nQuestions:\n"
)


def load_key():
    env = {}
    with open("/etc/edulabs-thesis-worker/worker.env") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k] = v.strip().strip('"').strip("'")
    return env.get("OPENROUTER_API_KEY", "")


def curl_http(url, data=None, headers=None, timeout=150):
    cmd = ["curl", "-s", "-m", str(timeout), "-H", "X-App-Signature: " + SIG,
           "-H", "Accept: application/json", "-H", "User-Agent: " + UA]
    for h in (headers or []):
        cmd += ["-H", h]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
        out = subprocess.run(cmd + [url], input=json.dumps(data).encode(),
                             capture_output=True, timeout=timeout + 20).stdout
    else:
        out = subprocess.run(cmd + [url], capture_output=True,
                             timeout=timeout + 20).stdout
    return out.decode("utf-8", errors="replace")


def fetch_batch(batch):
    raw = curl_http(BASE + "/zz_topic_batch.php?batch=%d" % batch, timeout=60)
    return json.loads(raw)


def save_topics(updates):
    raw = curl_http(BASE + "/zz_topic_save.php", data={"updates": updates}, timeout=90)
    return json.loads(raw)


def clean_stem(s):
    s = re.sub(r"^\s*(?:\d+\s*[.)]\s*|Question\s*\d+\s*[:.]\s*)", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def parse_items(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text)
        text = re.sub(r"```$", "", text)
    decoded = None
    try:
        decoded = json.loads(text)
    except Exception:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e > s:
            try:
                decoded = json.loads(text[s:e + 1])
            except Exception:
                decoded = None
    if isinstance(decoded, dict):
        decoded = decoded.get("items", decoded)
    return decoded if isinstance(decoded, list) else None


def classify_chunk(chunk, key, start_model_idx):
    """chunk: list of {id, q}. Returns (topics_map, model_used).
    Tries up to 6 models starting at start_model_idx (rotating)."""
    p = PROMPT
    for i, row in enumerate(chunk):
        p += "[%d] %s\n" % (i, clean_stem(row["q"])[:400])
    payload = {
        "messages": [
            {"role": "system", "content": "You are a precise classifier. Reply with ONLY the requested JSON object."},
            {"role": "user", "content": p},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }
    n_models = len(FREE_MODELS)
    last_err = ""
    max_tries = 6   # don't burn minutes trying every model when several fail
    for attempt in range(max_tries):
        model = FREE_MODELS[(start_model_idx + attempt) % n_models]
        payload["model"] = model
        cmd = ["curl", "-s", "-m", "150",
               "-H", "Authorization: Bearer " + key,
               "-H", "Content-Type: application/json",
               "-H", "User-Agent: " + UA,
               "-H", "HTTP-Referer: https://medigyaan.xyz",
               "-H", "X-Title: Medigyaan Question Bank",
               "--data-binary", "@-",
               "https://openrouter.ai/api/v1/chat/completions"]
        try:
            proc = subprocess.run(cmd, input=json.dumps(payload).encode(),
                                  capture_output=True, timeout=170)
            raw = proc.stdout.decode("utf-8", errors="replace")
            if proc.returncode != 0:
                last_err = "curl exit %d %s" % (proc.returncode, raw[:120])
                continue
            body = json.loads(raw)
            content = body["choices"][0]["message"]["content"]
            items = parse_items(content)
            if items is None:
                last_err = "unparsable"
                continue
            topics = {}
            for it in items:
                idx = it.get("index", -1)
                topic = (it.get("topic") or "").strip()
                if isinstance(idx, int) and 0 <= idx < len(chunk) and topic:
                    topics[chunk[idx]["id"]] = topic
            if topics:
                return topics, model
            last_err = "empty"
            continue
        except subprocess.TimeoutExpired:
            last_err = "timeout"
            continue
        except Exception as e:
            last_err = str(e)
            time.sleep(3)
            continue
    return {}, "none(%s)" % last_err


def main():
    key = load_key()
    if not key:
        print("no openrouter key", flush=True)
        sys.exit(1)
    start_model = int(time.time()) % len(FREE_MODELS)
    global_filled = 0
    no_progress = 0
    fetch_errs = 0
    workers = 3

    while True:
        try:
            batch = fetch_batch(500)
            fetch_errs = 0
        except Exception as e:
            fetch_errs += 1
            wait = 120 if fetch_errs <= 3 else 300
            print("fetch error: %s (backoff %ds)" % (repr(e), wait), flush=True)
            time.sleep(wait)
            continue

        remaining = batch.get("remaining", 0)
        rows = batch.get("rows", [])
        if not rows:
            print("NO_MORE_ROWS remaining=%d" % remaining, flush=True)
            break

        updates = []
        filled_here = 0
        chunks = [rows[i:i + 120] for i in range(0, len(rows), 120)]
        n_chunks = len(chunks)
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {}
            for ci, chunk in enumerate(chunks):
                mi = (start_model + ci) % len(FREE_MODELS)
                futs[ex.submit(classify_chunk, chunk, key, mi)] = ci
            for fut in as_completed(futs):
                ci = futs[fut]
                topics, model = fut.result()
                for qid, t in topics.items():
                    updates.append({"id": qid, "topic": t})
                done += 1
                print("  chunk %d/%d rows=%d classified=%d model=%s"
                      % (ci + 1, n_chunks, len(chunks[ci]), len(topics), model),
                      flush=True)
        start_model = (start_model + n_chunks) % len(FREE_MODELS)

        if updates:
            try:
                res = save_topics(updates)
                filled_here = res.get("filled", 0)
                remaining = res.get("remaining", remaining)
            except Exception as e:
                print("save error: %s" % repr(e), flush=True)
                filled_here = -1
        if filled_here >= 0:
            global_filled += filled_here
            no_progress = no_progress + 1 if filled_here == 0 else 0
            print("rows=%d saved=%d total_filled=%d remaining=%d last_model=%s"
                  % (len(rows), filled_here, global_filled, remaining, model),
                  flush=True)
        if no_progress >= 3 and remaining > 0:
            print("STALLED no progress, remaining=%d" % remaining, flush=True)
            break
        if remaining <= 0:
            print("DONE remaining=0 total_filled=%d" % global_filled, flush=True)
            break
        time.sleep(10)


if __name__ == "__main__":
    main()
