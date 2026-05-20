# testing api connection
print("Start")

from config import API_BASE_URL
import requests
import json

url = f"{API_BASE_URL}/search.json?q=propublica"

response = requests.get(url)
data = response.json()

print(data.keys())
print(data["organizations"][0].keys())
print(json.dumps(data["organizations"][0], indent=2))