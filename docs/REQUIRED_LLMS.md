# 🤖 Required AI Models & API Keys

> The Tank uses a **hybrid AI architecture**: local models for offline operation,
> cloud providers for enhanced capabilities. The evolution system automatically
> discovers and tests providers during each cycle.

## 📊 Provider Overview

| Priority | Provider | Free Tier | Speed | Models |
|----------|----------|-----------|-------|--------|
| 1 | **OpenRouter** | $5 credit | 500ms | GPT-4o, Claude, Llama, Mistral |
| 2 | **Groq** | Unlimited | 200ms | Llama 3.1 8B, Mixtral |
| 3 | **Google Gemini** | 15 RPM | 300ms | Gemini Flash, Gemini Pro |
| 4 | **Mistral AI** | 1 RPM | 400ms | Mistral Small, Medium |
| 5 | **Cerebras** | 30 RPM | 100ms | Llama 3.1 8B (fastest) |
| 6 | **Cohere** | 1000 RPM | 350ms | Command R, Command R+ |
| 7 | **Replicate** | $5 credit | 800ms | Llama, Stable Diffusion |
| 8 | **Hugging Face** | 30K chars/mo | 600ms | Llama, Falcon |
| 9 | **Cloudflare** | 10K req/day | 250ms | Llama, SD |
| 10 | OpenAI (opt) | $5 credit | 400ms | GPT-4o, DALL-E 3 |
| 11 | Anthropic (opt) | $5 credit | 450ms | Claude 3.5 Sonnet |
| 12 | Together AI (opt) | $5 credit | 500ms | Llama 3.1 70B |
| 13 | DeepInfra (opt) | $5 credit | 550ms | Llama, Mistral |
| 14 | SambaNova (opt) | Unlimited | 300ms | Llama 3.1 |

## 🔑 How to Get API Keys

### Required (for basic evolution):
1. **Groq** → https://console.groq.com/keys (fastest, unlimited free)
2. **OpenRouter** → https://openrouter.ai/keys ($5 free credit)
3. **Cerebras** → https://cloud.cerebras.ai/api-keys (fastest inference)

### Recommended (for better coverage):
4. **Google Gemini** → https://aistudio.google.com/apikey
5. **Mistral** → https://console.mistral.ai/api-keys
6. **Cohere** → https://dashboard.cohere.com/api-keys

### Optional (for advanced features):
7. **OpenAI** → https://platform.openai.com/api-keys
8. **Anthropic** → https://console.anthropic.com/api-keys
9. **Replicate** → https://replicate.com/account/api-tokens

## 📝 Setup Instructions

### Method 1: Edit .env file (recommended)
```bash
nano ~/The-Tank-Project/.env
# Add your keys:
OPENROUTER_API_KEY=sk-or-v1-...
GROQ_API_KEY=gsk_...
```

### Method 2: Environment variables
```bash
export OPENROUTER_API_KEY=sk-or-v1-...
export GROQ_API_KEY=gsk_...
```

### Method 3: Interactive setup (during evolution)
The evolution system will prompt you to paste keys interactively:
```bash
python3 -c "from tank.ai.evolution_key_manager import EvolutionKeyManager; EvolutionKeyManager().interactive_setup()"
```

## 🔄 Evolution Cycle

The evolution system runs daily and:
1. **Checks** which API keys are configured
2. **Prompts** for missing keys with setup URLs
3. **Tests** each configured provider with a benchmark
4. **Ranks** providers by speed + quality
5. **Rotates** the best provider to primary
6. **Reports** results via SMS/Telegram

If a key is missing, the system will:
- Print the setup URL to the terminal
- Send you an SMS with the link
- Wait for you to paste the key

## 🏠 Local Models (Offline)

These run on the Jetson without any API key:
| Model | Size | Purpose | RAM |
|-------|------|---------|-----|
| Phi-3 Mini 4K | 3.8B Q4 | General chat | 2.5 GB |
| TinyLlama 1.1B | 1.1B Q4 | Quick responses | 0.8 GB |
| YOLOv8n | 6MB | Object detection | 0.1 GB |
| Whisper tiny | 75MB | Speech-to-text | 0.1 GB |
| Whisper base | 142MB | Better STT | 0.2 GB |
| Piper TTS | 50MB | Text-to-speech | 0.1 GB |

## 📱 SMS Notifications

When the evolution cycle completes, you receive:
```
TankOS EVOLUTION CYCLE
Providers tested: 9/14
Working: 7
Best: Groq (142ms)
New key needed: OpenAI
Setup: https://platform.openai.com/api-keys
```

Configure SMS in .env:
```
TANK_EVOLUTION_SMS_NOTIFY=true
TANK_EVOLUTION_SMS_NUMBER=+917860245819
```
