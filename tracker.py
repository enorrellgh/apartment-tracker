import time
import pandas as pd
from datetime import datetime
import json
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------------------
# LOAD CREDS FROM ENV
# ----------------------------
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])

with open("creds.json", "w") as f:
    json.dump(creds_dict, f)

# ----------------------------
# GOOGLE SHEETS SETUP
# ----------------------------
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

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# ----------------------------
# LOAD PAGE
# ----------------------------
driver.get("https://www.101crossstreetapts.com/site-map")
time.sleep(15)

# ----------------------------
# SWITCH TO IFRAME
# ----------------------------
iframes = driver.find_elements(By.TAG_NAME, "iframe")

for iframe in iframes:
    src = iframe.get_attribute("src")
    if "sightmap" in (src or ""):
        driver.switch_to.frame(iframe)
        break

time.sleep(6)

# ----------------------------
# SCRAPE DATA
# ----------------------------
rows = []
today = datetime.today().strftime("%Y-%m-%d")

units = driver.find_elements(By.CSS_SELECTOR, "[class*='unit']")

for u in units:
    try:
        text = u.text.strip()

        if "$" in text:
            lines = text.split("\n")

            unit = None
            price = None

            for line in lines:
                if "$" in line:
                    price = line.replace("$", "").replace(",", "")
                elif any(char.isdigit() for char in line):
                    unit = line

            if unit and price:
                rows.append([today, unit, price])

    except:
        continue

driver.quit()

# ----------------------------
# PUSH TO SHEETS
# ----------------------------
if rows:
    if not sheet.get_all_values():
        sheet.append_row(["date", "unit", "price"])

    for row in rows:
        sheet.append_row(row)

    print(f"Uploaded {len(rows)} rows")
else:
    print("No data found")
