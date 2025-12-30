import requests
response = requests.get("http://127.0.0.1:8000/search?q=Journal%20of%20Sample%20Studies")
print(response.json())