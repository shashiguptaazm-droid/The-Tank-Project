"""Local GGUF LLM provider — wraps llama-cpp-python as an AIProvider.

Loads the smallest available GGUF model from the models directory and
makes it available through the AIManager interface for offline use.

Designed as a fallback: when no API providers are reachable, the local
model can still provide basic AI capabilities for NL→shell translation,
error explanation, and chat.

Thread safety
-------------
llama-cpp-python has a GIL-free Python binding, but model loading is
not thread-safe. We load the model once on first use and cache it.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from tank_os.core.ai_manager import AIProvider

logger = logging.getLogger("tank_os.local_llm")

# Default model directory — overridable via env var.
MODELS_DIR = Path(os.environ.get(
    "TANK_LOCAL_MODELS_DIR",
    "/var/lib/tank_os/models/llm",
))


@dataclass
class LocalModelInfo:
    """Information about a discovered GGUF model."""
    path: Path
    name: str               # filename without extension
    size_mb: float
    is_multimodal: bool = False  # Qwen2-VL etc.


def discover_gguf_models(models_dir: Optional[Path] = None) -> List[LocalModelInfo]:
    """Scan the models directory for GGUF files.

    Returns models sorted by file size (smallest first) so the caller
    can pick a default that's fast to load.
    """
    directory = models_dir or MODELS_DIR
    if not directory.exists():
        logger.debug("Local models directory %s does not exist", directory)
        return []

    models: List[LocalModelInfo] = []
    for fpath in sorted(directory.iterdir()):
        if fpath.suffix.lower() != ".gguf":
            continue
        size_mb = fpath.stat().st_size / (1024 * 1024)
        name = fpath.stem
        multimodal = "vl" in name.lower() or "vision" in name.lower()
        models.append(LocalModelInfo(
            path=fpath,
            name=name,
            size_mb=round(size_mb, 1),
            is_multimodal=multimodal,
        ))

    models.sort(key=lambda m: m.size_mb)
    return models


class LocalLlamaProvider(AIProvider):
    """AIProvider wrapping a local GGUF model via llama-cpp-python.

    The smallest model is loaded by default. Falls back gracefully when
    llama-cpp-python is not installed.
    """

    def __init__(self, *,
                 models_dir: Optional[Path] = None,
                 model_path: Optional[Path] = None,
                 n_ctx: int = 2048,
                 n_gpu_layers: int = 0,
                 verbose: bool = False) -> None:
        super().__init__("local-llama")
        self._models_dir = models_dir or MODELS_DIR
        self._model_path = model_path
        self._n_ctx = n_ctx
        self._n_gpu_layers = n_gpu_layers
        self._verbose = verbose
        self._lock = threading.Lock()
        self._model: Any = None   # llama_cpp.Llama instance
        self._model_info: Optional[LocalModelInfo] = None
        self._load_error: Optional[str] = None
        self._loaded = False

    # ── Public API ─────────────────────────────────────────────────────

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self._model is not None

    @property
    def model_info(self) -> Optional[LocalModelInfo]:
        return self._model_info

    def ensure_loaded(self) -> bool:
        """Load the model if not already loaded. Returns True on success."""
        if self._loaded and self._model is not None:
            return True
        with self._lock:
            if self._loaded:
                return self._model is not None
            return self._try_load()

    def chat(self, text: str, *,
             system_prompt: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: int = 512,
             **kwargs: Any) -> str:
        if not self.ensure_loaded():
            return self._offline_message(text)

        try:
            prompt = self._build_prompt(text, system_prompt)
            start = time.time()
            response = self._model.create_completion(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["</s>", "<|im_end|>", "User:", "\n\n\n"],
                echo=False,
            )
            elapsed = time.time() - start
            text_out = (response.get("choices", [{}])[0]
                        .get("text", "")
                        .strip())
            logger.debug("local-llama: %d tokens in %.1fs",
                         response.get("usage", {}).get("completion_tokens", 0),
                         elapsed)
            return text_out if text_out else self._offline_message(text)
        except Exception as exc:
            logger.warning("local-llama inference failed: %s", exc)
            return self._offline_message(text)

    def get_status(self) -> Dict[str, Any]:
        """Status snapshot."""
        info = self._model_info
        return {
            "name": self.name,
            "available": self.is_loaded,
            "type": "local-gguf",
            "model": info.name if info else None,
            "size_mb": info.size_mb if info else None,
            "loaded": self.is_loaded,
            "error": self._load_error,
            "models_dir": str(self._models_dir),
            "offline": not self.is_loaded,
        }

    # ── Internals ──────────────────────────────────────────────────────

    def _try_load(self) -> bool:
        """Attempt to load llama-cpp-python and the model."""
        # Already tried and failed? Don't retry on every chat call.
        if self._load_error and self._model is None:
            return False

        # Find the model file
        model_path = self._resolve_model_path()
        if model_path is None:
            self._load_error = "no GGUF model found"
            self._loaded = True  # mark as "tried" so we don't retry
            logger.warning("local-llama: %s", self._load_error)
            return False

        # Try importing llama-cpp-python
        try:
            import llama_cpp  # type: ignore
        except ImportError:
            self._load_error = "llama-cpp-python not installed"
            self._loaded = True
            logger.warning("local-llama: %s", self._load_error)
            return False

        # Load the model
        try:
            logger.info("local-llama: loading %s (%d MiB, ctx=%d, gpu=%d)",
                        model_path.name,
                        model_path.stat().st_size // (1024 * 1024),
                        self._n_ctx, self._n_gpu_layers)
            self._model = llama_cpp.Llama(
                model_path=str(model_path),
                n_ctx=self._n_ctx,
                n_gpu_layers=self._n_gpu_layers,
                verbose=self._verbose,
            )
            self._model_info = LocalModelInfo(
                path=model_path,
                name=model_path.stem,
                size_mb=round(model_path.stat().st_size / (1024 * 1024), 1),
            )
            self._loaded = True
            logger.info("local-llama: loaded %s successfully", model_path.name)
            return True
        except Exception as exc:
            self._load_error = str(exc)[:200]
            self._loaded = True
            logger.warning("local-llama: model load failed: %s", exc)
            return False

    def _resolve_model_path(self) -> Optional[Path]:
        """Return the path to the GGUF model to use."""
        if self._model_path is not None:
            return self._model_path if self._model_path.exists() else None

        models = discover_gguf_models(self._models_dir)
        if not models:
            return None
        # Return the smallest model (fastest to load for basic tasks)
        return models[0].path

    def _build_prompt(self, text: str,
                      system_prompt: Optional[str] = None) -> str:
        """Build a chat-style prompt for the local model."""
        if system_prompt:
            return (
                f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
                f"<|im_start|>user\n{text}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )
        return (
            f"<|im_start|>user\n{text}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    def _offline_message(self, original: str) -> str:
        """Return a graceful offline fallback message."""
        return (
            "[local-llama offline] Please install llama-cpp-python or "
            "check that a GGUF model exists in the models directory. "
            f"Your input: {original[:60]}"
        )
