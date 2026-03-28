import os
import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

FLOORPLANS_URL = "https://www.101crossstreetapts.com/floorplans"
SHEET_NAME = "Apartment Prices"

# ----------------------------
# Google auth
# ----------------------------
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])

with open("creds.json", "w") as f:
    json.dump(creds_dict, f)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# ----------------------------
# Fetch page
# ----------------------------
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

resp = requests.get(FLOORPLANS_URL, headers=headers, timeout=30)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")
text = soup.get_text("\n", strip=True)

# ----------------------------
# Parse by plan sections
# The page is structured like:
# ## A
# Studio
# 1 Bath
# 557-to 569 Sq. Ft.
# Starting at $1,670
# ----------------------------
pattern = re.compile(
    r"##\s*([A-Z])\s+"
    r"(Studio|1\s*Bed|2\s*Bed)\s+"
    r"(\d\s*Bath)\s+"
    r"([\d,\-\sto]+Sq\.\s*Ft\.)\s+"
    r"(Starting at \$[\d,]+|Call for details)",
    re.IGNORECASE
)

matches = pattern.findall(text)

today = datetime.utcnow().strftime("%Y-%m-%d")
rows = []

for plan, beds, baths, sqft, price_text in matches:
    if "Starting at $" in price_text:
        price = price_text.replace("Starting at $", "").replace(",", "").strip()
    else:
        price = "CALL"

    rows.append([today, plan.strip(), beds.strip(), baths.strip(), sqft.strip(), price])

# Deduplicate
seen = set()
deduped = []
for row in rows:
    key = tuple(row)
    if key not in seen:
        seen.add(key)
        deduped.append(row)

print(f"Found {len(deduped)} rows")
for row in deduped[:5]:
    print(row)

# ----------------------------
# Write to sheet
# ----------------------------
existing = sheet.get_all_values()
if not existing:
    sheet.append_row(["date", "plan", "beds", "baths", "sqft", "price"])

if deduped:
    sheet.append_rows(deduped, value_input_option="USER_ENTERED")
    print(f"Uploaded {len(deduped)} rows")
else:
    print("No data found")
