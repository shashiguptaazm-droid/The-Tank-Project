import json, urllib.request, re, base64

src = open('/root/ai_keys_pool.php').read()
b = re.search(r"base64_decode\('([^']+)'\)", src).group(1)
keys = json.loads(base64.b64decode(b))
KEY = keys.get('OPENROUTER_API_KEY', '')

req = urllib.request.Request('https://openrouter.ai/api/v1/models',
                             headers={'Authorization': 'Bearer ' + KEY})
data = json.loads(urllib.request.urlopen(req, timeout=30).read())
free = []
for m in data.get('data', []):
    p = m.get('pricing', {})
    try:
        prompt = float(p.get('prompt', 1) or 1)
        compl = float(p.get('completion', 1) or 1)
    except (TypeError, ValueError):
        continue
    if prompt == 0 and compl == 0:
        free.append((m['id'], m.get('context_length') or 0,
                     m.get('description', '')[:60]))
free.sort(key=lambda x: -x[1])
print('total free models:', len(free))
for mid, ct, desc in free[:30]:
    print('%-55s ctx=%s | %s' % (mid, ct, desc.replace('\n', ' ')))
