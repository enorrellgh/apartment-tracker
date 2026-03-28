import os
import json
import time
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
SPREADSHEET_ID = "11zpkRKDq1y0Rh-esy-FCJfPBuz7MhJCObyAVo6dpOq8"
WORKSHEET_NAME = "RawData"
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

run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

# Header
existing_values = worksheet.get_all_values()
if not existing_values:
    worksheet.append_row([
        "run_timestamp_utc",
        "status",
        "field_1",
        "field_2",
        "field_3",
        "field_4",
        "field_5",
        "notes"
    ])

worksheet.append_row([run_ts, "RUN_STARTED", "", "", "", "", "", "heartbeat"])

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
driver.get(TARGET_URL)
time.sleep(15)

body_text = driver.find_element(By.TAG_NAME, "body").text
page_source = driver.page_source
title = driver.title
current_url = driver.current_url

driver.quit()

# ============================================================
# WRITE DEBUG INFO TO SHEET
# ============================================================
worksheet.append_row([run_ts, "PAGE_TITLE", title, "", "", "", "", ""])
worksheet.append_row([run_ts, "CURRENT_URL", current_url, "", "", "", "", ""])
worksheet.append_row([run_ts, "BODY_LENGTH", str(len(body_text)), "", "", "", "", ""])

# Write chunks of visible body text into the sheet so you can inspect it
chunk_size = 40000
chunks = [body_text[i:i + chunk_size] for i in range(0, len(body_text), chunk_size)]

if not chunks:
    worksheet.append_row([run_ts, "NO_BODY_TEXT", "", "", "", "", "", "body text empty"])
else:
    for idx, chunk in enumerate(chunks[:5], start=1):
        worksheet.append_row([run_ts, f"BODY_TEXT_CHUNK_{idx}", chunk, "", "", "", "", ""])

# Also write page source length
worksheet.append_row([run_ts, "HTML_LENGTH", str(len(page_source)), "", "", "", "", ""])

# ============================================================
# SIMPLE TEXT CHECKS
# ============================================================
keywords = [
    "Starting at $",
    "Studio",
    "1 Bed",
    "2 Bed",
    "Sq. Ft.",
    "Availability",
    "Call for details"
]

found_keywords = [k for k in keywords if k in body_text]
worksheet.append_row([
    run_ts,
    "KEYWORDS_FOUND",
    ", ".join(found_keywords) if found_keywords else "NONE",
    "",
    "",
    "",
    "",
    ""
])

# ============================================================
# VERY SIMPLE LINE-BASED EXTRACTION
# ============================================================
lines = [x.strip() for x in body_text.split("\n") if x.strip()]

data_rows = []
for i, line in enumerate(lines):
    if line.startswith("Starting at $") or line == "Call for details":
        price = line.replace("Starting at $", "").replace(",", "").strip()
        nearby = lines[max(0, i-4):i+1]
        data_rows.append([
            run_ts,
            "CANDIDATE",
            " | ".join(nearby),
            "",
            "",
            "",
            price,
            ""
        ])

if data_rows:
    worksheet.append_rows(data_rows[:25], value_input_option="USER_ENTERED")
    worksheet.append_row([run_ts, "CANDIDATE_COUNT", str(len(data_rows)), "", "", "", "", ""])
else:
    worksheet.append_row([run_ts, "NO_CANDIDATES_FOUND", "", "", "", "", "", "no price lines detected"])
