import requests
from bs4 import BeautifulSoup

url = 'https://www.indeed.nl/jobs?q=hospitality&l=Nederland'

page = requests.get(url)
soup = BeautifulSoup(page.content, 'html.parser')

results = soup.find(id='resultsCol')
job_elems = results.find_all('div', class_='jobsearch-SerpJobCard')

for job_elem in job_elems:
    title_elem = job_elem.find('h2', class_='title')
    company_elem = job_elem.find('span', class_='company')
    location_elem = job_elem.find('div', class_='recJobLoc')
    if None in (title_elem, company_elem, location_elem):
        continue
    print(title_elem.text.strip())
    print(company_elem.text.strip())
    print(location_elem.text.strip())
    print()
