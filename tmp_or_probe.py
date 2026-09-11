import json, urllib.request, urllib.error, re, base64

src = open('/root/ai_keys_pool.php').read()
b = re.search(r"base64_decode\('([^']+)'\)", src).group(1)
keys = json.loads(base64.b64decode(b))
KEY = keys.get('OPENROUTER_API_KEY', '')

models = ['minimax/minimax-m2.7:free', 'nvidia/nemotron-3-super-120b-a12b:free',
          'google/gemma-4-26b-a4b-it:free']
payload = {
    'model': '',
    'messages': [
        {'role': 'system', 'content': 'Reply with ONLY the JSON object requested.'},
        {'role': 'user', 'content': 'Classify: [0] A 2-year-old with bilateral pitting edema and MUAC <11.5 cm. Return {"items":[{"index":0,"topic":"..."}]}'},
    ],
    'temperature': 0.1,
    'max_tokens': 500,
}
for m in models:
    payload['model'] = m
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
        data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json',
                 'HTTP-Referer': 'https://medigyaan.xyz', 'X-Title': 'Medigyaan QBank'})
    try:
        resp = urllib.request.urlopen(req, timeout=90)
        body = resp.read().decode()
        print('===', m, resp.status)
        print(body[:600])
    except urllib.error.HTTPError as e:
        print('===', m, e.code)
        print(e.read().decode()[:500])
    except Exception as e:
        print('===', m, 'ERR', e)
