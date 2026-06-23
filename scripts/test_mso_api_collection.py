import requests
from config import API_BASE_URL
import json

url = f"{API_BASE_URL}"

# API call
response = requests.get(url)

print("Hello World")
# print(json.dumps(response.json(), indent=2)[:3000])
print(response.json()["total_results"])