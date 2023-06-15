import requests

url = 'https://en.wikipedia.org/wiki/Love'
response = requests.get(url)
print(response.content)