import requests
import json
import urllib.parse

BASE_URL = "https://medigyaan.xyz/Neurons/api/"
HEADERS = {
    "X-App-Signature": "EduLabsRTM_Secure_v1_2026",
    "Accept": "application/json"
}

def fetch_topics(subject):
    url = f"{BASE_URL}getTopics.php?subject={urllib.parse.quote(subject)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        if data.get("success"):
            return data["data"] # Now returns [{"name":..., "count":...}]
    except Exception as e:
        print(f"Error fetching topics for {subject}: {e}")
    return []

metadata = {
    "subjects": ["NEET PG", "NEET UG"],
    "topics": {}
}

for s in metadata["subjects"]:
    print(f"Fetching {s}...")
    metadata["topics"][s] = fetch_topics(s)

with open("medigyaan_metadata.json", "w") as f:
    json.dump(metadata, f, indent=4)

print("Metadata saved to medigyaan_metadata.json")
