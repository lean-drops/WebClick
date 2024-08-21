import requests
from bs4 import BeautifulSoup

def scrape_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    pages = [{'title': link.text, 'url': link['href']} for link in soup.find_all('a', href=True)]
    content = {
        'pages': pages,
    }
    return content
