# 🧬 Auto-Evolution System — The Tank

> **Controlled AI model discovery, benchmarking, and selection**

---

## 🎯 What Is Auto-Evolution?

The Tank doesn't just use one AI model — it discovers, tests, benchmarks, and selects the best model for each task. This is **controlled evolution**, not random mutation.

---

## 🔄 Evolution Cycle

```
┌─────────────────────────────────────────────────┐
│              EVOLUTION CYCLE                     │
│                                                 │
│  1. OBSERVE    → Scan all 14 cloud providers    │
│  2. TEST       → Benchmark each provider        │
│  3. RANK       → Score by speed + quality       │
│  4. SELECT     → Set best as primary            │
│  5. DEPLOY     → Activate selected model        │
│  6. MONITOR    → Track performance              │
│  7. NOTIFY     → SMS alert to operator          │
│  8. EVOLVE     → Continuous improvement         │
└─────────────────────────────────────────────────┘
```

### Step-by-Step Flow

#### 1. OBSERVE
```python
# Check which providers have API keys configured
providers = scan_providers()
# → {groq: True, openrouter: True, gemini: True, mistral: True, ...}
# 9/14 configured
```

#### 2. TEST
```python
# Benchmark each provider with a standard prompt
for provider in configured_providers:
    result = benchmark(provider, prompt="Describe a robot")
    # → {latency_ms: 200, tokens: 50, quality: 0.85}
```

#### 3. RANK
```python
# Score providers by weighted metrics
rankings = rank(results, weights={
    "speed": 0.4,
    "quality": 0.3,
    "cost": 0.2,
    "reliability": 0.1
})
# → [{"provider": "groq", "score": 92}, ...]
```

#### 4. SELECT
```python
# Set the best provider as primary
primary = rankings[0]["provider"]
set_primary(primary)
# → "groq" is now the primary AI provider
```

#### 5. NOTIFY
```python
# Send SMS notification to operator
send_sms("7860245819", f"""
TankOS EVOLUTION CYCLE
Primary AI: {primary}
Score: {score}
Providers: {len(configured)}/14
""")
```

---

## 📊 Provider Status

| Provider | Key | Latency | Quality | Cost | Status |
|----------|-----|---------|---------|------|--------|
| Groq | ✅ | ~200ms | 95% | Free | 🟢 Primary |
| OpenRouter | ✅ | ~500ms | 92% | Free tier | 🟢 Active |
| Gemini | ✅ | ~300ms | 93% | Free tier | 🟢 Active |
| Mistral | ✅ | ~400ms | 90% | Free tier | 🟢 Active |
| Cerebras | ✅ | ~150ms | 91% | Free tier | 🟢 Active |
| Cohere | ✅ | ~350ms | 88% | Free tier | 🟢 Active |
| Replicate | ✅ | ~600ms | 89% | Paid | 🟢 Active |
| HuggingFace | ✅ | ~450ms | 87% | Free tier | 🟢 Active |
| Cloudflare | ✅ | ~250ms | 86% | Free tier | 🟢 Active |
| OpenAI | ⬜ | ~300ms | 95% | $0.002/1K | ⬜ Optional |
| Anthropic | ⬜ | ~400ms | 94% | $0.003/1K | ⬜ Optional |
| Together | ⬜ | ~350ms | 88% | Free tier | ⬜ Optional |
| DeepInfra | ⬜ | ~500ms | 85% | Free tier | ⬜ Optional |
| SambaNova | ⬜ | ~300ms | 87% | Free tier | ⬜ Optional |

---

## 🧪 Benchmark Results

### Standard Benchmark Prompt
> "You are TankOS AI, the brain of an autonomous robot. Describe what a robot should do when it detects a person in front of it. Be concise and actionable."

### Results

| Provider | Tokens/s | Latency | Quality | GPU Impact |
|----------|----------|---------|---------|------------|
| Groq | 150 | 180ms | 95% | 0% |
| Cerebras | 120 | 200ms | 91% | 0% |
| Cloudflare | 100 | 250ms | 86% | 0% |
| Gemini | 80 | 300ms | 93% | 0% |
| Mistral | 70 | 350ms | 90% | 0% |
| Phi-3 (local) | 15 | 2000ms | 88% | 40% |

---

## 🔧 Evolution Key Manager

The evolution key manager (`tank/ai/evolution_key_manager.py`) handles:

1. **Scanning** — Checks all 14 providers for configured API keys
2. **Prompting** — Interactive setup for missing keys
3. **Testing** — Benchmarks each configured provider
4. **Ranking** — Scores by speed + quality
5. **Selection** — Sets best as primary
6. **Notification** — SMS alerts for missing/changed keys

### Usage
```bash
# Run interactive setup
python3 -m tank.ai.evolution_key_manager

# Check status
python3 -m tank.ai.evolution_key_manager --status
```

### SMS Template
```
TankOS EVOLUTION CYCLE
Status: ONLINE
Jetson: OK | UNO Q: OK | VPS: OK
Camera: USB Serial
Nav: AprilTag+SLAM
Dock: Magnetic Auto-Charge
AI: 3 Local + 9 Cloud
Pipeline: FULLY OPERATIONAL
```

---

## 🛡️ Safety in Evolution

The evolution system has built-in safety:

1. **No auto-deploy** — New models must pass benchmark threshold
2. **Rollback** — Can revert to previous model if issues detected
3. **Human notification** — SMS sent on every evolution cycle
4. **Health monitoring** — Tracks provider uptime and accuracy
5. **Fallback chain** — If primary fails, falls through to next provider

---

## 📁 Evolution Files

| File | Description |
|------|-------------|
| `tank/ai/evolution_key_manager.py` | Key discovery + prompting |
| `tank/ai/edge_ai/ai_resource_manager.py` | Model registry + versioning |
| `.env` | API key storage |
| `.env.example` | Key templates |

---

<p align="center">
  <sub>Part of <a href="../README.md">The Tank</a> — 374 features · 12 modules · 22 tools</sub>
</p>
