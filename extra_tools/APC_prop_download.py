import requests
import os

# URLs
INDEX_URL = "https://www.apcprop.com/files/PER2_TITLEDAT.DAT"
BASE_FILE_URL = "https://www.apcprop.com/files/"

# Output directory (one level up in APC/)
OUTPUT_DIR = os.path.join("..", "APC")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

# Download and parse the index file
response = requests.get(INDEX_URL, headers=HEADERS)
response.raise_for_status()
lines = response.text.splitlines()

# Extract .dat filenames from the index
filenames = []
for line in lines:
    parts = line.strip().split()
    if parts and parts[0].lower().endswith(".dat"):
        filenames.append(parts[0])

print(f"Found {len(filenames)} .dat files.")

# Download each file
for name in filenames:
    file_url = f"{BASE_FILE_URL}{name}"
    dest_path = os.path.join(OUTPUT_DIR, name)

    print(f"Downloading {name}...")
    r = requests.get(file_url, headers=HEADERS)
    if r.status_code == 200:
        with open(dest_path, "wb") as f:
            f.write(r.content)
    else:
        print(f"Failed to download {name}: status code {r.status_code}")

print(f"Done. Files saved to: {os.path.abspath(OUTPUT_DIR)}")
