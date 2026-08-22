# REQUIRED_LLMS.md — Which Models the TankOS Project Actually Uses

This document is the canonical "required vs optional" tiering for the local AI models in the TankOS / Simple-Internet project at `/root/the tank project/`. It is grounded in actual `Path("/var/lib/tank_os/models/...")` references, `YOLO(...)` and `PiperVoice.load(...)` call sites, and `llama-cpp-python.Llama(model_path=...)` invocations in the running code.

The numbers in the size column are the **`min_mb` threshold** baked into `scripts/tankos_setup.sh`'s `download_model` helper, not the size on disk. A model on disk below its threshold causes `tankos_setup.sh --download` (or `--status`) to re-attempt the resume, so these are also the operational floor.

---

## Tier 1 — REQUIRED (active hard-codes in the runtime)

If any of these files are missing, the named subsystem fails or strips back to a "happy/neutral fallback" stub. The Python code paths will raise `FileNotFoundError`, `OSError`, or just lose functionality.

### 1.1 Phi-3-mini-4k-instruct-q4.gguf (≥ 2.3 GB)

**Caller proof** — `Llama(model_path=str(p))` is invoked on whatever `*.gguf` is found at the model path; Phi-3 is the explicitly-named *primary* conversational LLM in the manifest:

- `tank_os/preload/manifest.py:140-153` — `id="llm-primary", name="Primary LLM (GGUF)", description="Main conversational AI model — Microsoft Phi-3 Mini 4K Instruct (2.3B params)"`
- `tank_os/ai/reasoning_engine.py:258` — `models = list(llm_dir.glob("*.gguf"))` then `model_path = str(models[0])`; any `.gguf` works as primary, Phi-3 is the canonical first install
- `scripts/llm_ops.py:151-153` — `Llama(model_path=str(p), n_ctx=args.ctx, verbose=False)`
- `tank_ws/src/tank_assistant/tank_assistant/llm_node.py:16,67` — `model_path` parameter on the ROS2 node that loads `Llama(...)`

**Why it's required**: Phi-3 is the primary wake-word → STT → RAG → LLM → TTS chain's main inference path. `docs/COMPLETE_PROJECT.md:300` documents that the assistant reliably drives end-to-end only when Phi-3 (or a same-size primary GGUF) is loaded.

### 1.2 TinyLlama 1.1B-chat-v1.0.Q4_K_M.gguf (≥ 670 MB)

**Caller proof** — the explicit fallback when the primary is too tight:

- `docs/COMPLETE_PROJECT.md:300` — "wake-word → STT → RAG → LLM → TTS works end-to-end, but only with the local llama.cpp tiny-llama fallback; the primary Phi-3-Q4 model is too tight for 8 GB on heavy prompts."
- `tank_os/preload/manifest.py:155-167` — `id="llm-fallback", name="Fallback LLM (GGUF), description="Lightweight model for when primary is too slow"`
- `tank_os/ai/reasoning_engine.py:258` — `models = list(llm_dir.glob("*.gguf"))` (TinyLlama is also a `.gguf`, so it's a valid first-match if Phi-3 is missing)

**Why it's required**: on the 8 GB NVIDIA Jetson Orin Nano, Phi-3 (3.8B params, 2.3 GB on disk) plus the OS + Python + Chromium + ~30 browser tabs pins RAM near saturation. `docs/COMPLETE_PROJECT.md:308` records that `llama.cpp Phi-3 Q4 at 8 GB competes with the robot's other subsystems`. TinyLlama is the always-on graceful-degradation path.

### 1.3 Piper `en_US-amy-medium.onnx` (~60 MB) + companion `.onnx.json`

**Caller proof** — TTS pipeline directly loads it:

- `tank_ws/src/tank_text/tank_text/voice_manager.py:108-115` — registers `PIPER_VOICES["en_US-amy-medium"] = VoiceSpec(...)` with the canonical HF URL
- `tank_ws/src/tank_text/tank_text/tts_node.py:50-52` — `self._voice = PiperVoice.load(model_path, config_path)`
- `tank_ws/src/tank_text/tank_text/tts_node.py:91-97` — the ROS2 tts_node declares a `model_path` parameter that defaults to this voice
- `tank_os/preload/manifest.py:266-272` — `id="piper-voice-en-us", filename="en_US-amy-medium.onnx", install_path=f"{SPEECH_DIR}/piper/voices"`

**Why it's required**: `voice_manager.py` knows several voices (en_US-amy, en_US-lessac, en_US-ryan, en_GB-alan, en_GB-cori, etc.) but `en_US-amy-medium` is the canonical default the system boots into. Without this file the `tts_node` raises at startup.

### 1.4 yolov8n.pt (≥ 6 MB)

**Caller proof** — hardcoded path:

- `tank_os/core/vision_manager.py:78` — `self._yolo_model = YOLO("yolov8n.pt")` (literal string in source)
- `tank_ws/src/tank_command_bridge/tank_command_bridge/plugins/_vision_helpers.py:85` — `model_path: str = "yolov8n.pt"` (the vision plugin's default)
- `tank_ws/src/tank_vision/tank_vision/object_tracker.py:43` — `DEFAULT_MODEL = "yolov8n.pt"`
- `scripts/vision_ops.py:141`, `scripts/vision_smoketest.py:154`, `scripts/ai_vision.py:84`, `scripts/train_pipeline.py:98-99`

**Why it's required**: Hard-coded as a relative path means `YOLO("yolov8n.pt")` runs from CWD (`/root/the tank project/` for ROS2 nodes, or wherever the entry point lives). The autodownload script places it at `<MODELS_DIR>/vision/yolo/yolov8n.pt` and the loader assumes either a CWD there or the file is on `PYTHONPATH`. Without this file, all vision features fail.

### 1.5 Whisper (auto-pulled by `openai-whisper` on first STT)

**Caller proof** — STT node loads at first call:

- `tank_ws/src/tank_speech/tank_speech/stt_node.py:97-99` — `import whisper; self._impl = whisper.load_model(model_size, device=device)`
- `tank_ws/src/tank_speech/tank_speech/stt_node.py:104-106` — preferred runtime `from faster_whisper import WhisperModel` (smaller, faster)
- `scripts/audio_smoketest.py:117-125` — `import whisper; model = whisper.load_model(args.model_size)`
- `tank_ws/src/tank_text/tank_text/stt_node.py:54-55` — secondary STT path with `whisper.load_model`

**Why it's required**: Whisper is the only STT backend in the project (no Vosk, no DeepSpeech). `whisper.load_model(...)` triggers an automatic download of the weights into `~/.cache/whisper/{tiny,base,small,medium,large}.pt` if not present, so this tier is **self-populating on first STT call** — no entry in the autodownload script needed. The autodownload's role is to install the `openai-whisper` Python package via `pip install openai-whisper`.

---

## Tier 2 — IMPORTANT (graceful-degrade without them)

These are called by name in the code; if missing, the named feature silently falls back to a stub or returns `[]`.

### 2.1 qwen2.5-coder-1.5b-instruct-q4_k_m.gguf (≥ 950 MB)

**Caller proof** — explicit coder-LLM glob:

- `tank_os/ai/self_coding.py:534` — `models = list(llm_dir.glob("*coder*gguf")) + list(llm_dir.glob("*Coder*gguf"))` then loads the first match
- `tank_os/preload/manifest.py:170-180` — `id="llm-code", description="Specialized model for code generation tasks — Qwen2.5 Coder 1.5B"`

**Without it**: F207-F311 host-level `self_coding.py` features (`scripts/ai_vision.py` integration) silently fall back to "synthetic JSON" stubs and the assistant can't generate real code through the local LLM bridge. Caller still loads `Phi-3`/`TinyLlama` for chat, but coding requests get a "no coder model found" path.

### 2.2 Qwen2-VL-7B-Instruct-Q4_K_M.gguf + mmproj-Qwen2-VL-7B-Instruct-f16.gguf (≥ 4.4 GB + ≥ 1.3 GB)

**Caller proof** — explicit VLM glob + mmproj requirement:

- `tank_os/ai/vision_understanding.py:103-107` — `candidates = list(llm_dir.glob("*VL*gguf")) + list(llm_dir.glob("*vision*gguf")) + list(llm_dir.glob("*vl*gguf"))` then loads first match
- `tank_os/ai/vision_understanding.py:225,304` — passes `model_path=self._vlm_model_path` into `llama_cpp.Llama(model_path=..., mmproj=..., ...)`
- `tank_os/preload/manifest.py:184-205` — registers both files

**Without it**: `vision_understanding.describe_scene()` and `visual_qa()` fall back to YOLO-only object detection (no scene captioning, no visual Q&A). 5.7 GB combined makes it the heaviest single bundle in the project.

### 2.3 facenet512_weights.h5 (≥ 85 MB)

**Caller proof** — emotion/age pipelines:

- `scripts/ai_vision.py:325-332` — `from deepface import DeepFace` (F225 emotion-face)
- `scripts/ai_vision.py:339-347` — `from deepface import DeepFace` (F226 age-gender)
- `tank_os/preload/manifest.py:362-366` — `id="face-recognition", filename="facenet512_weights.h5"`

**Without it**: deepface gracefully degrades to a different (often smaller / less-accurate) face-recognition backend and `ai_vision.py:332,347` falls back to "happy/neutral fallback" or empty result.

---

## Tier 3 — OPTIONAL (no direct caller; only listed for completeness)

| Model | Why it's optional |
|---|---|
| `yolov8s.pt` (≥ 20 MB) | `train_pipeline.py:99` and `tankos_setup.sh:322` reference it as a "balanced object detection" upgrade, but `vision_manager.py:78` only ever loads `yolov8n.pt`. No code-path auto-promotes. Toggling requires a code change in `vision_manager.py`. |
| `openWakeWord` models (per-wakeword) | Managed internally by `openWakeWord`'s own `download_models()` pipeline. The `_wakeword-hey-tank` entry in `manifest.py:281-289` is `verify_only=True` — we don't ship weights, the wake-word library does. |

---

## Storage Budget

Disk usage at the **Jetson default 32 GB SD card**:

| Tier | Models | Disk |
|---|---|---|
| **Tier 1 only** (lean Pi boot) | Phi-3 + TinyLlama + Piper + Whisper (auto) + yolov8n | **~3.1 GB** |
| Tier 1 + Tier 2 (full feature set) | + qwen2.5-coder + Qwen2-VL + mmproj + facenet512 | **~9.7 GB** |
| Tier 1 + 2 + 3 (everything in setup.sh, including yolov8s) | + yolov8s | **~9.8 GB** |

The autodownload script (`scripts/tankos_setup.sh --download`) defaults to Tier 1 + 2 minus facenet512 (currently). Tier 3 `yolov8s` is gated behind the same auto-discovery — it will be skipped unless code in `vision_manager.py` changes to call for it.

---

## Recommendations for the Pi 8 GB RAM profile

Based on `docs/COMPLETE_PROJECT.md:308`:

> "llama.cpp Phi-3 Q4 at 8 GB competes with the robot's other subsystems; need a swap-tuned model (< 2 GB) or offload-to-CPU strategy."

Ship **Tier 1 only** for the primary system, with **TinyLlama as the always-on primary** and Phi-3 reserved for instances where the LLM chain has >2 GB free RAM:

1. **Always-on**: TinyLlama 1.1B (~700 MB on disk, ~500 MB RAM) for the wake-word → STT → RAG → TTS chain.
2. **On-demand for batch jobs**: Phi-3 3.8B (~2.3 GB on disk, ~1.5 GB RAM at Q4) for offline analysis / summarization when the rest of the stack is idle.
3. **Optional Tier 2**: qwen2.5-coder only if the self-coding FIDs (F207-F311) are actively used; Qwen2-VL + mmproj only if visual Q&A / scene captioning are core.
4. **Skip Tier 3**: yolov8s unless vision_manager.py is patched to load it.

This profile leaves ~4 GB free for OS + ROS2 + Python + reserve, and every model has a known fallback path.

---

## How to verify these tiers

To re-derive this table at any point, run from the project root:

```bash
# Pull the canonical model list
python3 -c "from tank_os.preload.manifest import MANIFEST, categories; \
  for cat in ('llm','speech','vision'): \
    [print(i.id, i.size_mb, i.required, i.install_path, i.url[:60]) \
      for i in MANIFEST.values() if i.category==cat]"

# Find every consumer of the canonical model paths
grep -rn "Path(\"/var/lib/tank_os/models" /root/the\ tank\ project/tank_ws/src \
                                              /root/the\ tank\ project/tank_os \
                                              /root/the\ tank\ project/scripts \
                                              | grep -v 'tankos_setup.sh' | grep -v 'predownload_deps.sh'
```

Both will refresh if Tier 1 / 2 / 3 boundaries shift as new code lands.

---

_Last regenerated: with the `download_model` helper that adds `curl -C -` auto-resume + `.part` files + exit-33 handling. If the helper changes, regenerate this table._
