import os
import json
import time
import re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------------------
# GOOGLE SHEETS SETUP
# ----------------------------
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])

with open("creds.json", "w") as f:
    json.dump(creds_dict, f)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Apartment Prices").sheet1

# ----------------------------
# SELENIUM SETUP
# ----------------------------
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# ----------------------------
# LOAD PAGE
# ----------------------------
driver.get("https://www.101crossstreetapts.com/floorplans")

time.sleep(15)

# ----------------------------
# GET FULL PAGE TEXT
# ----------------------------
body_text = driver.find_element(By.TAG_NAME, "body").text

driver.quit()

# ----------------------------
# PARSE TEXT (robust)
# ----------------------------
pattern = re.compile(
    r"\b([A-Z])\b\s+"
    r"(Studio|1\s*Bed|2\s*Bed)\s+"
    r"(\d\s*Bath)\s+"
    r"([\d,\-\sto]+Sq\.?\s*Ft\.?)\s+"
    r"(Starting at \$[\d,]+|Call for details)",
    re.IGNORECASE
)

matches = pattern.findall(body_text)

today = datetime.utcnow().strftime("%Y-%m-%d")
rows = []

for plan, beds, baths, sqft, price_text in matches:
    if "Starting at $" in price_text:
        price = price_text.replace("Starting at $", "").replace(",", "").strip()
    else:
        price = "CALL"

    rows.append([today, plan.strip(), beds.strip(), baths.strip(), sqft.strip(), price])

# Remove duplicates
unique_rows = []
seen = set()
for r in rows:
    if tuple(r) not in seen:
        seen.add(tuple(r))
        unique_rows.append(r)

print(f"Found {len(unique_rows)} rows")

# ----------------------------
# WRITE TO GOOGLE SHEETS
# ----------------------------
if not sheet.get_all_values():
    sheet.append_row(["date", "plan", "beds", "baths", "sqft", "price"])

if unique_rows:
    sheet.append_rows(unique_rows)
    print(f"Uploaded {len(unique_rows)} rows")
else:
    print("⚠️ No data extracted")
