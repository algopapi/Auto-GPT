import requests
from bs4 import BeautifulSoup

url = 'https://en.wikipedia.org/wiki/The_History_of_Love'

response = requests.get(url)

soup = BeautifulSoup(response.content, 'html.parser')

print(soup.prettify())