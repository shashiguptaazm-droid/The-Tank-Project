import json, base64

env = {}
with open('/etc/edulabs-thesis-worker/worker.env') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k] = v.strip().strip('"').strip("'")

need = ['OPENROUTER_API_KEY', 'GROQ_API_KEY', 'GEMINI_API_KEY', 'MISTRAL_API_KEY',
        'CEREBRAS_API_KEY', 'COHERE_API_KEY', 'REPLICATE_API_KEY', 'HUGGINGFACE_API_KEY',
        'DEEPSEEK_API_KEY', 'ENDPOINT_AI_API_KEY', 'ENDPOINT_AI_BASE_URL', 'ENDPOINT_AI_MODEL',
        'DEEPSEEK_MODEL', 'OPENROUTER_MODEL', 'HUGGINGFACE_MODEL',
        'CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_WORKER_API_KEY']
keys = {k: env.get(k, '') for k in need}
b = base64.b64encode(json.dumps(keys).encode('utf-8')).decode('ascii')
open('/root/ai_keys_pool.php', 'w').write(
    "<?php $__k = base64_decode('%s'); return json_decode($__k, true); ?>\n" % b)
print('built key pool with', sum(1 for v in keys.values() if v), 'populated values')
