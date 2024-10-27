import requests
from bs4 import BeautifulSoup
import json

def scrape_zh_links(base_url="https://www.zh.ch/de.html"):
    try:
        # Sende eine GET-Anfrage an die Basis-URL
        response = requests.get(base_url)
        response.raise_for_status()  # Überprüft, ob die Anfrage erfolgreich war

        # Parse den HTML-Inhalt der Seite
        soup = BeautifulSoup(response.text, 'html.parser')

        # Finde alle <a> Tags mit href Attribut
        links = soup.find_all('a', href=True)

        # Filtere die Links, die mit dem Basis-URL Präfix beginnen
        filtered_links = set()
        for link in links:
            href = link['href']
            if href.startswith(base_url):
                filtered_links.add(href)
            elif href.startswith('/de/'):
                # Wenn der Link relativ ist, füge den Basis-URL Präfix hinzu
                full_url = requests.compat.urljoin(base_url, href)
                filtered_links.add(full_url)

        # Konvertiere die Menge der Links in eine Liste
        links_list = list(filtered_links)

        # Erstelle ein Dictionary für das JSON
        data = {
            "links": links_list
        }

        # Speichere die Daten in einer JSON-Datei
        with open('../static/json/urls.json', 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)

        print(f"Gefundene Links wurden in 'urls.json' gespeichert.")

    except requests.exceptions.RequestException as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

# Beispielaufruf der Funktion
if __name__ == "__main__":
    scrape_zh_links()
