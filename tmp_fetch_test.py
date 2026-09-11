import json, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
url = "https://medigyaan.xyz/Neurons/api/zz_topic_batch.php?batch=2"
req = urllib.request.Request(url, headers={
    "X-App-Signature": "EduLabsRTM_Secure_v1_2026",
    "User-Agent": UA,
    "Accept": "application/json",
    "Connection": "close",
})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        d = json.loads(resp.read().decode())
        print("OK remaining=%s rows=%d" % (d.get("remaining"), len(d.get("rows", []))))
        print("first row:", d.get("rows", [{}])[0])
except Exception as e:
    print("ERR", repr(e))
