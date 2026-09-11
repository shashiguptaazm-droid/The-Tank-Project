import json, urllib.request, urllib.error, re, base64

src = open('/root/ai_keys_pool.php').read()
b = re.search(r"base64_decode\('([^']+)'\)", src).group(1)
keys = json.loads(base64.b64decode(b))
KEY = keys.get('OPENROUTER_API_KEY', '')

for path in ['https://openrouter.ai/api/v1/key',
             'https://openrouter.ai/api/v1/auth/key']:
    try:
        req = urllib.request.Request(path, headers={'Authorization': 'Bearer ' + KEY})
        resp = urllib.request.urlopen(req, timeout=30)
        print('===', path, resp.status)
        body = resp.read().decode()
        print(body[:800])
        break
    except urllib.error.HTTPError as e:
        print('===', path, e.code)
        print(e.read().decode()[:400])
    except Exception as e:
        print('===', path, 'ERR', e)
