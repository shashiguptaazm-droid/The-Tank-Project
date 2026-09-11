import requests
import json

URL = "https://medigyaan.xyz/Neurons/api/create_order.php"
HEADERS = {
    "Content-Type": "application/json",
    "X-App-Signature": "EduLabsRTM_Secure_v1_2026"
}
PAYLOAD = {
    "amount": 1.00,
    "customer_id": "test_user_1",
    "email": "test@example.com",
    "phone": "9999999999"
}

try:
    response = requests.post(URL, headers=HEADERS, json=PAYLOAD, timeout=15)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
