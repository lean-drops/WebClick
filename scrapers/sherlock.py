import requests

# Server-URL
SERVER_URL = "http://127.0.0.1:5001/scrape_sub_links"

# Funktion zum Testen der API
def test_scrape_sub_links_route(valid_data, invalid_data):
    headers = {"Content-Type": "application/json"}

    # Teste gültige Daten
    try:
        print("Testing valid data...")
        response = requests.post(SERVER_URL, json=valid_data, headers=headers)
        print(f"Valid data test result - Status Code: {response.status_code}")
        print("Response:", response.json())
    except Exception as e:
        print(f"Exception during valid data test: {e}")

    # Teste ungültige Daten
    try:
        print("Testing invalid data...")
        response = requests.post(SERVER_URL, json=invalid_data, headers=headers)
        print(f"Invalid data test result - Status Code: {response.status_code}")
        print("Response:", response.json())
    except Exception as e:
        print(f"Exception during invalid data test: {e}")

def main():
    # Testserver
    try:
        response = requests.get("http://127.0.0.1:5001/")
        if response.status_code == 200:
            print("Server is up and running.")
        else:
            print(f"Server is down. Status Code: {response.status_code}")
            return
    except Exception as e:
        print(f"Exception checking server status: {e}")
        return

    # Beispielhafte gültige und ungültige Daten
    valid_data = {"url": "http://example.com"}
    invalid_data_cases = [
        {},  # Leeres JSON
        {"wrong_key": "http://example.com"},  # Falscher Schlüssel
        {"url": ""},  # Leere URL
        {"url": "invalid-url"}  # Ungültige URL
    ]

    # Teste alle ungültigen Daten
    for invalid_data in invalid_data_cases:
        test_scrape_sub_links_route(valid_data, invalid_data)

if __name__ == "__main__":
    main()
