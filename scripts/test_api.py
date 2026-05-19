# testing api connection
print("Start")

import requests
from config import API_BASE_URL

url = f"{API_BASE_URL}/search.json?q=propublica"

# API call
response = requests.get(url)

print(response.status_code)
print(response.text[:500])