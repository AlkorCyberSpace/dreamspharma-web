import requests
import json

print("=" * 70)
print("Testing: GET http://localhost:8000/api/erp/config")
print("=" * 70)

try:
    response = requests.get('http://localhost:8000/api/erp/config')
    print(f"\n✅ Status Code: {response.status_code}")
    print(f"\nResponse:\n{json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"❌ Error: {e}")
