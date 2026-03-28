import os
import json
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------------------
# LOAD GOOGLE CREDS
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
# LOAD FLOORPLANS PAGE
# ----------------------------
driver.get("https://www.101crossstreetapts.com/floorplans")

time.sleep(15)

# ----------------------------
# SCRAPE FLOORPLAN DATA
# ----------------------------
rows = []
today = datetime.utcnow().strftime("%Y-%m-%d")

cards = driver.find_elements(By.CSS_SELECTOR, "[class*='floor']")

for card in cards:
    try:
        text = card.text.strip()

        if "$" in text and ("Bed" in text or "Studio" in text):
            lines = text.split("\n")

            plan = None
            price = None
            beds = None

            for line in lines:
                if "$" in line:
                    price = line.replace("Starting at $", "").replace("$", "").replace(",", "").strip()
                elif "Bed" in line or "Studio" in line:
                    beds = line
                elif len(line) == 1:  # plan names like A, B, C
                    plan = line

            if plan and price:
                rows.append([today, plan, beds, price])

    except:
        continue

driver.quit()

# ----------------------------
# WRITE TO SHEETS
# ----------------------------
if rows:
    if not sheet.get_all_values():
        sheet.append_row(["date", "plan", "beds", "price"])

    sheet.append_rows(rows)
    print(f"Uploaded {len(rows)} rows")
else:
    print("No data found")
