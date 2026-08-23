"""
TankOS 100 AI Provider Abstraction Layer
==========================================
Unified interface for 100+ AI providers: LLM, Vision, OCR, STT, TTS,
Embedding, Image Gen, Video AI, Coding AI, Robotics AI, Local Models.

Provider scoring: capability + quality + reliability + latency + privacy
                  + hardware_fit + language_fit + availability
                  - cost - network_penalty - failure_rate
"""

from __future__ import annotations
import os
import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Callable

logger = logging.getLogger("tank.ai.providers")


class AICapability(Enum):
    LLM_TEXT = "llm_text"
    VLM = "vision_language"
    VISION = "vision"
    OCR = "ocr"
    STT = "speech_to_text"
    TTS = "text_to_speech"
    EMBEDDING = "embedding"
    IMAGE_GEN = "image_generation"
    VIDEO_AI = "video_ai"
    CODING = "coding"
    ROBOTICS = "robotics"
    TRANSLATION = "translation"
    SEARCH = "search"
    REASONING = "reasoning"
    CLASSIFICATION = "classification"
    ANOMALY = "anomaly_detection"


class ProviderStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"
    OFFLINE = "offline"


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    name: str
    display_name: str
    capabilities: list[AICapability]
    api_key_env: str = ""
    base_url: str = ""
    models: list[str] = field(default_factory=list)
    free_tier: bool = False
    max_tokens: int = 4096
    supports_vision: bool = False
    supports_streaming: bool = False
    supports_tools: bool = False
    latency_ms: int = 1000
    priority: int = 50
    requires_network: bool = True
    privacy_level: str = "cloud"  # cloud, hybrid, local
    languages: list[str] = field(default_factory=lambda: ["en"])
    cost_per_1k_tokens: float = 0.0


@dataclass
class ProviderHealth:
    """Health tracking for a provider."""
    status: ProviderStatus = ProviderStatus.UNKNOWN
    success_count: int = 0
    fail_count: int = 0
    total_requests: int = 0
    avg_latency_ms: float = 0
    last_success: float = 0
    last_failure: float = 0
    circuit_breaker_until: float = 0
    health_score: float = 50.0


class AIProviderRegistry:
    """Registry of all 100 AI providers."""

    def __init__(self):
        self._providers: dict[str, ProviderConfig] = {}
        self._health: dict[str, ProviderHealth] = {}
        self._register_all()

    def _register(self, name: str, display: str, caps: list[AICapability],
                  **kwargs):
        config = ProviderConfig(name=name, display_name=display,
                              capabilities=caps, **kwargs)
        self._providers[name] = config
        self._health[name] = ProviderHealth()

    def _register_all(self):
        """Register all 100 providers."""
        LLM = AICapability.LLM_TEXT
        VLM = AICapability.VLM
        VIS = AICapability.VISION
        OCR = AICapability.OCR
        STT = AICapability.STT
        TTS = AICapability.TTS
        EMB = AICapability.EMBEDDING
        IMG = AICapability.IMAGE_GEN
        VID = AICapability.VIDEO_AI
        COD = AICapability.CODING
        ROB = AICapability.ROBOTICS
        TRN = AICapability.TRANSLATION
        RSN = AICapability.REASONING
        SEA = AICapability.SEARCH
        CLS = AICapability.CLASSIFICATION

        # ══ 1-15: Major LLM Providers ══
        self._register("openai", "OpenAI", [LLM, VLM, OCR, COD, RSN, CLS],
                       api_key_env="OPENAI_API_KEY", models=["gpt-4o", "gpt-4o-mini", "o1", "o1-mini"],
                       supports_vision=True, supports_tools=True, latency_ms=1500)
        self._register("anthropic", "Anthropic Claude", [LLM, VLM, COD, RSN, CLS],
                       api_key_env="ANTHROPIC_API_KEY",
                       models=["claude-opus-4-20250514", "claude-sonnet-4-20250514", "claude-3-haiku-20240307"],
                       supports_vision=True, latency_ms=2000)
        self._register("google_gemini", "Google Gemini", [LLM, VLM, OCR, STT, TTS, EMB, COD, RSN, CLS, TRN],
                       api_key_env="GEMINI_API_KEY",
                       models=["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
                       supports_vision=True, supports_streaming=True, latency_ms=800)
        self._register("groq", "Groq", [LLM, STT, EMB, CLS],
                       api_key_env="GROQ_API_KEY",
                       models=["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "whisper-large-v3"],
                       supports_tools=True, latency_ms=200, free_tier=True)
        self._register("openrouter", "OpenRouter", [LLM, VLM, COD, RSN, CLS, TRN],
                       api_key_env="OPENROUTER_API_KEY",
                       models=["meta-llama/llama-4-maverick", "google/gemini-2.5-flash", "anthropic/claude-sonnet-4"],
                       supports_vision=True, supports_tools=True, latency_ms=1200)
        self._register("mistral", "Mistral AI", [LLM, COD, RSN, CLS],
                       api_key_env="MISTRAL_API_KEY",
                       models=["mistral-large-latest", "mistral-small-latest", "codestral-latest"],
                       supports_tools=True, latency_ms=1000)
        self._register("cerebras", "Cerebras", [LLM, EMB, CLS],
                       api_key_env="CEREBRAS_API_KEY",
                       models=["llama-3.3-70b", "llama-3.1-8b"],
                       latency_ms=150, free_tier=True)
        self._register("cohere", "Cohere", [LLM, EMB, CLS, SEA, TRN],
                       api_key_env="COHERE_API_KEY",
                       models=["command-r-plus", "command-r", "embed-english-v3"],
                       supports_tools=True, latency_ms=800)
        self._register("replicate", "Replicate", [LLM, VLM, IMG, VID, TTS, STT],
                       api_key_env="REPLICATE_API_TOKEN",
                       models=["meta-llama-4-maverick", "stability-ai/sdxl", "whisper"],
                       latency_ms=3000)
        self._register("huggingface", "Hugging Face", [LLM, VLM, EMB, STT, TTS, OCR, CLS],
                       api_key_env="HF_API_TOKEN",
                       models=["meta-llama/Llama-4-Maverick-17B-128E-Instruct", "microsoft/Phi-3-mini"],
                       free_tier=True, latency_ms=2000)
        self._register("cloudflare_workers_ai", "Cloudflare Workers AI", [LLM, VLM, EMB, STT, TTS],
                       api_key_env="CLOUDFLARE_API_KEY",
                       models=["@cf/meta/llama-3.3-70b-instruct-fp16", "@cf/openai/whisper"],
                       free_tier=True, latency_ms=500)
        self._register("together", "Together AI", [LLM, VLM, EMB, IMG],
                       api_key_env="TOGETHER_API_KEY",
                       models=["meta-llama/Llama-4-Maverick-17B-128E-Instruct", "stabilityai/stable-diffusion-xl"],
                       latency_ms=1000, free_tier=True)
        self._register("deepinfra", "DeepInfra", [LLM, STT, EMB],
                       api_key_env="DEEPINFRA_API_KEY",
                       models=["meta-llama/Llama-4-Maverick-17B-128E-Instruct", "whisper-large-v3"],
                       latency_ms=600, free_tier=True)
        self._register("sambanova", "SambaNova", [LLM, EMB, CLS],
                       api_key_env="SAMBANOVA_API_KEY",
                       models=["Meta-Llama-3.3-70B-Instruct", "DeepSeek-R1-Distill-Llama-70B"],
                       latency_ms=400, free_tier=True)
        self._register("fireworks", "Fireworks AI", [LLM, VLM, EMB, IMG],
                       api_key_env="FIREWORKS_API_KEY",
                       models=["accounts/fireworks/models/llama-v3p3-70b-instruct", "stable-diffusion-xl"],
                       latency_ms=500)

        # ══ 16-25: Vision & OCR Providers ══
        self._register("google_vision", "Google Cloud Vision", [VIS, OCR, CLS],
                       api_key_env="GOOGLE_CLOUD_API_KEY", latency_ms=400)
        self._register("azure_vision", "Azure Computer Vision", [VIS, OCR, CLS],
                       api_key_env="AZURE_VISION_KEY", latency_ms=500)
        self._register("aws_rekognition", "AWS Rekognition", [VIS, CLS],
                       api_key_env="AWS_ACCESS_KEY", latency_ms=600)
        self._register("tesseract_ocr", "Tesseract OCR", [OCR], requires_network=False,
                       models=["tesseract-5"], latency_ms=200, free_tier=True)
        self._register("easyocr", "EasyOCR", [OCR], requires_network=False,
                       models=["easyocr-base"], latency_ms=300, free_tier=True)
        self._register("paddleocr", "PaddleOCR", [OCR], requires_network=False,
                       latency_ms=250, free_tier=True)
        self._register("surya_ocr", "Surya OCR", [OCR], requires_network=False,
                       models=["surya-9b"], latency_ms=400, free_tier=True)
        self._register("trocr", "TrOCR (HuggingFace)", [OCR], requires_network=False,
                       models=["microsoft/trocr-base-handwritten"], latency_ms=350, free_tier=True)
        self._register("doctr", "docTR", [OCR], requires_network=False,
                       latency_ms=300, free_tier=True)
        self._register("marker_ocr", "Marker", [OCR], requires_network=False,
                       latency_ms=500, free_tier=True)

        # ══ 26-35: Speech Providers ══
        self._register("openai_whisper", "OpenAI Whisper API", [STT],
                       api_key_env="OPENAI_API_KEY", models=["whisper-1"], latency_ms=2000)
        self._register("deepgram", "Deepgram", [STT],
                       api_key_env="DEEPGRAM_API_KEY", models=["nova-2"], latency_ms=500,
                       supports_streaming=True)
        self._register("assemblyai", "AssemblyAI", [STT],
                       api_key_env="ASSEMBLYAI_API_KEY", models=["best"], latency_ms=800)
        self._register("google_stt", "Google Speech-to-Text", [STT],
                       api_key_env="GOOGLE_CLOUD_API_KEY", latency_ms=600)
        self._register("azure_stt", "Azure Speech Services", [STT],
                       api_key_env="AZURE_SPEECH_KEY", latency_ms=700)
        self._register("whisper_local", "Whisper (Local)", [STT], requires_network=False,
                       models=["whisper-base", "whisper-small", "whisper-large-v3"],
                       latency_ms=1500, free_tier=True, privacy_level="local")
        self._register("coqui_tts", "Coqui TTS", [TTS], requires_network=False,
                       models=["tts_models-en-ljspeech-tacotron2-DDC"],
                       latency_ms=300, free_tier=True, privacy_level="local")
        self._register("piper_tts", "Piper TTS", [TTS], requires_network=False,
                       latency_ms=100, free_tier=True, privacy_level="local")
        self._register("google_tts", "Google Cloud TTS", [TTS],
                       api_key_env="GOOGLE_CLOUD_API_KEY", latency_ms=400)
        self._register("elevenlabs", "ElevenLabs", [TTS, STT],
                       api_key_env="ELEVENLABS_API_KEY", models=["eleven_multilingual_v2"],
                       latency_ms=800)

        # ══ 36-45: Embedding & Search ══
        self._register("openai_embeddings", "OpenAI Embeddings", [EMB],
                       api_key_env="OPENAI_API_KEY", models=["text-embedding-3-small"])
        self._register("voyage_ai", "Voyage AI", [EMB, SEA],
                       api_key_env="VOYAGE_API_KEY", models=["voyage-3"])
        self._register("jina_embeddings", "Jina AI", [EMB, SEA],
                       api_key_env="JINA_API_KEY", models=["jina-embeddings-v3"])
        self._register("nomic_embeddings", "Nomic Embeddings", [EMB],
                       api_key_env="NOMIC_API_KEY")
        self._register("sentence_transformers", "Sentence Transformers", [EMB],
                       requires_network=False, models=["all-MiniLM-L6-v2"],
                       free_tier=True, privacy_level="local")
        self._register("gte_qwen", "GTE-Qwen2 (Local)", [EMB],
                       requires_network=False, models=["gte-Qwen2-1.5B"],
                       free_tier=True, privacy_level="local")
        self._register("serpapi", "SerpAPI (Search)", [SEA],
                       api_key_env="SERPAPI_KEY")
        self._register("brave_search", "Brave Search", [SEA],
                       api_key_env="BRAVE_API_KEY")
        self._register("tavily", "Tavily Search", [SEA],
                       api_key_env="TAVILY_API_KEY")
        self._register("duckduckgo_search", "DuckDuckGo Search", [SEA],
                       requires_network=False, free_tier=True)

        # ══ 46-55: Image Generation ══
        self._register("dalle3", "DALL-E 3", [IMG],
                       api_key_env="OPENAI_API_KEY", models=["dall-e-3"])
        self._register("sdxl", "Stable Diffusion XL", [IMG],
                       requires_network=False, models=["stabilityai/stable-diffusion-xl-base-1.0"],
                       free_tier=True, privacy_level="local")
        self._register("stable_diffusion_3", "Stable Diffusion 3", [IMG],
                       api_key_env="STABILITY_API_KEY")
        self._register("midjourney_api", "Midjourney (via API)", [IMG],
                       latency_ms=30000)
        self._register("ideogram", "Ideogram AI", [IMG],
                       api_key_env="IDEOGRAM_API_KEY")
        self._register("flux", "Flux (by Black Forest Labs)", [IMG],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("comfyui", "ComfyUI (Local)", [IMG],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("Fooocus", "Fooocus (Local)", [IMG],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("picogen", "Picogen", [IMG],
                       api_key_env="PICOGEN_API_KEY")
        self._register("segmind", "Segmind", [IMG],
                       api_key_env="SEGMIND_API_KEY", free_tier=True)

        # ══ 56-65: Video & Multimodal ══
        self._register("runway", "Runway ML", [VID, IMG],
                       api_key_env="RUNWAY_API_KEY")
        self._register("pika", "Pika Labs", [VID],
                       api_key_env="PIKA_API_KEY")
        self._register("kling_ai", "Kling AI", [VID],
                       api_key_env="KLING_API_KEY")
        self._register("minimax_video", "MiniMax Video", [VID],
                       api_key_env="MINIMAX_API_KEY")
        self._register("luma_ai", "Luma AI", [VID, IMG],
                       api_key_env="LUMA_API_KEY")
        self._register("heygen", "HeyGen", [VID, TTS],
                       api_key_env="HEYGEN_API_KEY")
        self._register("synthesia", "Synthesia", [VID],
                       api_key_env="SYNTHESIA_API_KEY")
        self._register("hailuo_ai", "Hailuo AI (MiniMax)", [VID],
                       api_key_env="HAILUO_API_KEY")
        self._register("d_id", "D-ID", [VID, TTS],
                       api_key_env="DID_API_KEY")
        self._register("warp_transfer", "Warp Transfer AI", [VID],
                       api_key_env="WARP_API_KEY")

        # ══ 66-75: Coding AI ══
        self._register("github_copilot", "GitHub Copilot", [COD, CLS],
                       api_key_env="GITHUB_TOKEN")
        self._register("cursor_ai", "Cursor AI", [COD, CLS])
        self._register("codestral", "Codestral (Mistral)", [COD],
                       api_key_env="MISTRAL_API_KEY")
        self._register("codeshare", "Codeium/CodeShare", [COD])
        self._register("phind", "Phind AI", [COD, SEA])
        self._register("sweep_ai", "Sweep AI", [COD])
        self._register("aider", "Aider (Local)", [COD],
                       requires_network=False, free_tier=True)
        self._register("continue_dev", "Continue.dev", [COD],
                       requires_network=False, free_tier=True)
        self._register("tabnine", "Tabnine", [COD],
                       api_key_env="TABNINE_API_KEY")
        self._register("amazon_q", "Amazon Q Developer", [COD],
                       api_key_env="AWS_ACCESS_KEY")

        # ══ 76-85: Robotics & Specialized AI ══
        self._register("nvidiaisaac", "NVIDIA Isaac", [ROB, VIS, RSN],
                       requires_network=False, free_tier=True)
        self._register("yolo_ultralytics", "YOLO (Ultralytics)", [VIS, CLS],
                       requires_network=False, models=["yolov8n", "yolov8s", "yolov8m"],
                       free_tier=True, privacy_level="local")
        self._register("timm_models", "PyTorch Image Models", [VIS, CLS],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("mediapipe", "MediaPipe (Google)", [VIS, CLS, ROB],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("openpose", "OpenPose", [VIS, ROB],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("mmpose", "MMPose", [VIS, ROB],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("depth_anything", "Depth Anything", [VIS],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("sam_segment", "SAM (Segment Anything)", [VIS],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("grounding_dino", "Grounding DINO", [VIS],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("owl_vit", "OWL-ViT (Google)", [VIS],
                       requires_network=False, free_tier=True, privacy_level="local")

        # ══ 86-95: Local LLM Engines ══
        self._register("llama_cpp", "llama.cpp", [LLM, RSN, COD],
                       requires_network=False, models=["llama-3.1-8b", "phi-3-mini"],
                       free_tier=True, privacy_level="local")
        self._register("ollama", "Ollama", [LLM, VLM, EMB],
                       requires_network=False,
                       models=["llama3.1:8b", "phi3", "mistral", "gemma2", "llava"],
                       free_tier=True, privacy_level="local")
        self._register("vllm", "vLLM", [LLM],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("tensorrt_llm", "TensorRT-LLM", [LLM, RSN],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("mllama_local", "MLLama (Local)", [LLM, VLM],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("phi3_local", "Phi-3 Mini (Local)", [LLM, RSN],
                       requires_network=False, models=["phi-3-mini-4k"],
                       free_tier=True, privacy_level="local")
        self._register("tinyllama_local", "TinyLlama (Local)", [LLM],
                       requires_network=False, models=["tinyllama-1.1b"],
                       free_tier=True, privacy_level="local")
        self._register("qwen_local", "Qwen 2.5 (Local)", [LLM, VLM, COD],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("gemma_local", "Gemma 2 (Local)", [LLM],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("deepseek_local", "DeepSeek-R1 Distill (Local)", [LLM, COD, RSN],
                       requires_network=False, free_tier=True, privacy_level="local")

        # ══ 96-100: Translation & Specialized ══
        self._register("google_translate", "Google Translate", [TRN],
                       api_key_env="GOOGLE_CLOUD_API_KEY", latency_ms=300)
        self._register("deepl", "DeepL", [TRN],
                       api_key_env="DEEPL_API_KEY", latency_ms=400)
        self._register("argos_translate", "Argos Translate (Local)", [TRN],
                       requires_network=False, free_tier=True, privacy_level="local")
        self._register("indic_trans", "IndicTrans (Local)", [TRN],
                       requires_network=False, free_tier=True, privacy_level="local",
                       languages=["hi", "gu", "ta", "mr", "bn", "te"])
        self._register("opentydi", "OpenTydi", [TRN],
                       requires_network=False, free_tier=True)

    def get_provider(self, name: str) -> Optional[ProviderConfig]:
        return self._providers.get(name)

    def get_health(self, name: str) -> ProviderHealth:
        return self._health.get(name, ProviderHealth())

    def find_capable(self, capability: AICapability) -> list[ProviderConfig]:
        """Find all providers with a given capability."""
        return [p for p in self._providers.values()
                if capability in p.capabilities]

    def find_local_only(self) -> list[ProviderConfig]:
        """Find providers that work without network."""
        return [p for p in self._providers.values() if not p.requires_network]

    def find_free_tier(self) -> list[ProviderConfig]:
        """Find providers with free tier."""
        return [p for p in self._providers.values() if p.free_tier]

    def score_provider(self, provider: ProviderConfig,
                       capability: AICapability,
                       weights: dict | None = None) -> float:
        """Score a provider for a specific capability."""
        health = self._health.get(provider.name, ProviderHealth())

        # Base scores
        capability_match = 100 if capability in provider.capabilities else 0
        reliability = max(0, 100 - health.fail_count * 10)
        latency_score = max(0, 100 - provider.latency_ms / 100)
        availability = 100 if health.status != ProviderStatus.FAILED else 0
        cost_score = max(0, 100 - provider.cost_per_1k_tokens * 1000)
        privacy_score = {"local": 100, "hybrid": 70, "cloud": 40}.get(
            provider.privacy_level, 50)
        network_penalty = 20 if provider.requires_network else 0
        failure_penalty = health.fail_count * 5

        # Default weights
        w = weights or {
            "capability": 0.25, "reliability": 0.20, "latency": 0.20,
            "cost": 0.10, "privacy": 0.10, "availability": 0.15
        }

        score = (
            capability_match * w.get("capability", 0.25) +
            reliability * w.get("reliability", 0.20) +
            latency_score * w.get("latency", 0.20) +
            cost_score * w.get("cost", 0.10) +
            privacy_score * w.get("privacy", 0.10) +
            availability * w.get("availability", 0.15) -
            network_penalty - failure_penalty
        )

        return round(max(0, min(100, score)), 1)

    def select_best(self, capability: AICapability,
                    require_local: bool = False,
                    require_free: bool = False,
                    weights: dict | None = None) -> Optional[ProviderConfig]:
        """Select the best provider for a capability."""
        candidates = self.find_capable(capability)
        if require_local:
            candidates = [c for c in candidates if not c.requires_network]
        if require_free:
            candidates = [c for c in candidates if c.free_tier]

        if not candidates:
            return None

        scored = [(self.score_provider(c, capability, weights), c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None

    def select_with_fallback(self, capability: AICapability,
                             require_local: bool = False) -> list[ProviderConfig]:
        """Select primary + fallback chain."""
        candidates = self.find_capable(capability)
        if require_local:
            candidates = [c for c in candidates if not c.requires_network]

        scored = [(self.score_provider(c, capability), c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored]

    def record_success(self, name: str, latency_ms: float):
        health = self._health.get(name)
        if health:
            health.success_count += 1
            health.total_requests += 1
            health.last_success = time.time()
            health.avg_latency_ms = health.avg_latency_ms * 0.9 + latency_ms * 0.1
            health.status = ProviderStatus.HEALTHY
            health.health_score = min(100, health.health_score + 2)

    def record_failure(self, name: str):
        health = self._health.get(name)
        if health:
            health.fail_count += 1
            health.total_requests += 1
            health.last_failure = time.time()
            if health.fail_count >= 3:
                health.status = ProviderStatus.FAILED
                health.circuit_breaker_until = time.time() + 300
                health.health_score = max(0, health.health_score - 20)
            else:
                health.status = ProviderStatus.DEGRADED
                health.health_score = max(0, health.health_score - 10)

    def get_all_providers(self) -> list[ProviderConfig]:
        return list(self._providers.values())

    def get_count(self) -> int:
        return len(self._providers)

    def get_stats(self) -> dict:
        providers = self.get_all_providers()
        return {
            "total": self.get_count(),
            "cloud": sum(1 for p in providers if p.requires_network),
            "local": sum(1 for p in providers if not p.requires_network),
            "free_tier": sum(1 for p in providers if p.free_tier),
            "capabilities": len(set(c for p in providers for c in p.capabilities)),
            "healthy": sum(1 for h in self._health.values()
                         if h.status == ProviderStatus.HEALTHY),
        }


# Global singleton
AI_REGISTRY = AIProviderRegistry()
