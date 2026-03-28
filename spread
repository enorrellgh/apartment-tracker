import os
import json
import time
import re
from datetime import datetime, timezone

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ============================================================
# CONFIGURATION
# ============================================================

# Paste your spreadsheet ID here
SPREADSHEET_ID = "11zpkRKDq1y0Rh-esy-FCJfPBuz7MhJCObyAVo6dpOq8"

# Worksheet tab name inside the spreadsheet
WORKSHEET_NAME = "RawData"

# Target page
TARGET_URL = "https://www.101crossstreetapts.com/floorplans"

# ============================================================
# GOOGLE SHEETS AUTH
# ============================================================

creds_dict = json.loads(os.environ["GOOGLE_CREDS"])

with open("creds.json", "w") as f:
    json.dump(creds_dict, f)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

spreadsheet = client.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet(WORKSHEET_NAME)

print(f"Connected to spreadsheet: {spreadsheet.title}")
print(f"Connected to worksheet: {worksheet.title}")
print(f"Spreadsheet URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")

# ============================================================
# ENSURE HEADER EXISTS
# ============================================================

existing_values = worksheet.get_all_values()
if not existing_values:
    worksheet.append_row([
        "run_timestamp_utc",
        "status",
        "plan",
        "beds",
        "baths",
        "sqft",
        "price",
        "notes"
    ])
    print("Header row created.")

# ============================================================
# HEARTBEAT ROW (proves the script is writing to this exact tab)
# ============================================================

run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
worksheet.append_row([run_ts, "RUN_STARTED", "", "", "", "", "", "heartbeat"])
print("Heartbeat row written.")

# ============================================================
# SELENIUM SETUP
# ============================================================

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# ============================================================
# LOAD PAGE
# ============================================================

print(f"Loading {TARGET_URL}")
driver.get(TARGET_URL)
time.sleep(15)

body_text = driver.find_element(By.TAG_NAME, "body").text
driver.quit()

print("Page text length:", len(body_text))
print("First 1500 characters of page text:")
print(body_text[:1500])

# Save page text for debugging in the GitHub log
with open("page_text_debug.txt", "w", encoding="utf-8") as f:
    f.write(body_text)

# ============================================================
# PARSE TEXT
# ============================================================

pattern = re.compile(
    r"\b([A-Z])\b\s+"
    r"(Studio|1\s*Bed|2\s*Bed)\s+"
    r"(\d\s*Bath)\s+"
    r"([\d,\-\sto]+Sq\.?\s*Ft\.?)\s+"
    r"(Starting at \$[\d,]+|Call for details)",
    re.IGNORECASE
)

matches = pattern.findall(body_text)
print(f"Regex matches found: {len(matches)}")

rows = []
for plan, beds, baths, sqft, price_text in matches:
    if "Starting at $" in price_text:
        price = price_text.replace("Starting at $", "").replace(",", "").strip()
    else:
        price = "CALL"

    rows.append([
        run_ts,
        "DATA",
        plan.strip(),
        beds.strip(),
        baths.strip(),
        sqft.strip(),
        price,
        ""
    ])

# Deduplicate
unique_rows = []
seen = set()
for row in rows:
    key = tuple(row[2:7])  # dedupe based on plan/beds/baths/sqft/price
    if key not in seen:
        seen.add(key)
        unique_rows.append(row)

print(f"Unique rows after dedupe: {len(unique_rows)}")
for r in unique_rows[:10]:
    print(r)

# ============================================================
# WRITE DATA OR FAILURE MARKER
# ============================================================

if unique_rows:
    worksheet.append_rows(unique_rows, value_input_option="USER_ENTERED")
    print(f"Uploaded {len(unique_rows)} data rows.")
else:
    worksheet.append_row([run_ts, "NO_DATA_FOUND", "", "", "", "", "", "regex returned zero rows"])
    print("No data extracted. NO_DATA_FOUND row written.")
