import os
import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------------------
# CONFIG
# ----------------------------
FLOORPLANS_URL = "https://www.101crossstreetapts.com/floorplans"
SHEET_NAME = "Apartment Prices"

# ----------------------------
# GOOGLE SHEETS AUTH
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
# FETCH PAGE
# ----------------------------
headers = {
    "User-Agent": "Mozilla/5.0"
}

resp = requests.get(FLOORPLANS_URL, headers=headers, timeout=30)
resp.raise_for_status()

html = resp.text
soup = BeautifulSoup(html, "html.parser")
text = soup.get_text("\n", strip=True)

# ----------------------------
# PARSE FLOOR PLAN BLOCKS
# ----------------------------
# Pattern matches sections like:
# A ... Studio ... 1 Bath ... 557-to 569 Sq. Ft. ... Starting at $1,670
pattern = re.compile(
    r"\b([A-R])\b\s+"
    r"(Studio|1\s*Bed|2\s*Bed)\s+"
    r"(\d\s*Bath)\s+"
    r"([\d,\-\sto\.]+Sq\. Ft\.)\s+"
    r"(Starting at \$[\d,]+|Call for details)",
    re.IGNORECASE
)

matches = pattern.findall(text)

today = datetime.utcnow().strftime("%Y-%m-%d")
rows = []

for plan, beds, baths, sqft, price in matches:
    rows.append([
        today,
        plan.strip(),
        beds.strip(),
        baths.strip(),
        sqft.strip(),
        price.replace("Starting at $", "").replace("$", "").replace(",", "").strip()
        if "Starting at $" in price else "CALL",
    ])

# Remove duplicates while preserving order
seen = set()
deduped_rows = []
for row in rows:
    key = tuple(row)
    if key not in seen:
        seen.add(key)
        deduped_rows.append(row)

# ----------------------------
# WRITE HEADER IF NEEDED
# ----------------------------
existing = sheet.get_all_values()
if not existing:
    sheet.append_row(["date", "floor_plan", "beds", "baths", "sqft", "price"])

# ----------------------------
# APPEND NEW ROWS
# ----------------------------
if deduped_rows:
    sheet.append_rows(deduped_rows, value_input_option="USER_ENTERED")
    print(f"Uploaded {len(deduped_rows)} rows")
else:
    print("No floor plan data found")
