import json, re, base64

src = open('/root/ai_keys_pool.php').read()
b = re.search(r"base64_decode\('([^']+)'\)", src).group(1)
keys = json.loads(base64.b64decode(b))
only = {k: keys.get(k, '') for k in ['OPENROUTER_API_KEY', 'OPENROUTER_MODEL']}
enc = base64.b64encode(json.dumps(only).encode('utf-8')).decode('ascii')
open('/root/or_keys_pool.php', 'w').write(
    "<?php $__k = base64_decode('%s'); return json_decode($__k, true); ?>\n" % enc)
print('wrote or_keys_pool.php')
