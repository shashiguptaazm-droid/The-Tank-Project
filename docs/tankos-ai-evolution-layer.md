# 🧬 TankOS AI Evolution Layer

> Automated model discovery, evaluation, and rotation across 14 cloud providers + local models.

## How It Works

```
Daily Evolution Cycle:
┌─────────────────────────────────────────────┐
│ 1. SCAN: Check which API keys are present   │
│ 2. PROMPT: Ask user for missing keys        │
│ 3. TEST: Benchmark each provider            │
│ 4. RANK: Sort by speed + quality            │
│ 5. ROTATE: Set best as primary              │
│ 6. REPORT: SMS + Telegram notification      │
└─────────────────────────────────────────────┘
```

## Provider Priority
1. Local Phi-3 (always available, offline)
2. Groq (fastest cloud, unlimited free)
3. OpenRouter (most models, $5 credit)
4. Cerebras (fastest inference)
5. Google Gemini (multimodal)
6. Mistral, Cohere, Replicate, etc.

## Key Management
- Keys stored in `.env` file (never committed)
- Evolution prompts for missing keys at runtime
- SMS notification with setup URLs
- Interactive setup mode available

## Usage
```python
from tank.ai.evolution_key_manager import EvolutionKeyManager
mgr = EvolutionKeyManager()
mgr.run_evolution_cycle()  # Full cycle with key discovery
```
