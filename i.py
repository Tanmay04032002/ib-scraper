import os
import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor

# ── Settings ──────────────────────────────────────────────
download_folder = "i_downloads"
os.makedirs(download_folder, exist_ok=True)

base_url = "https://ibfd.archivalware.co.uk/awweb/pdfopener?md=1&did="

start = 73000
end   = 45001

MAX_WORKERS = 1          # 2 browsers open at all times throughout the run
DELAY_MIN   = 3          # Minimum seconds to wait between each request (per thread)
DELAY_MAX   = 6          # Maximum seconds to wait between each request (per thread)
# ──────────────────────────────────────────────────────────


def make_driver():
    """Create and return a fresh browser instance."""
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver
        

def worker(dids_chunk):
    """One browser handles its entire assigned chunk of IDs from start to finish."""
    driver = make_driver()  # Open browser ONCE

    try:
        for did in dids_chunk:
            file_path = os.path.join(download_folder, f"{did}.pdf")

            # Skip instantly WITHOUT opening browser if already downloaded
            if os.path.exists(file_path):
                print(f"{did}.pdf already exists. Skipping.")
                continue

            url = base_url + str(did)
            print(f"Checking DID {did}")

            driver.get(url)

            # Wait max 15 seconds, but exit early if page loads
            try:
                WebDriverWait(driver, 15).until(
                    lambda d: "Access denied" in d.page_source
                    or "pdfopener" in d.page_source
                )
            except:
                pass

            # Immediately skip if access denied
            if "Access denied" in driver.page_source:
                print(f"Access denied for {did}")
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                continue

            # Extract cookies from Selenium
            cookies = driver.get_cookies()
            session = requests.Session()

            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])

            try:
                response = session.get(url, stream=True)

                if response.status_code == 200 and "application/pdf" in response.headers.get("Content-Type", ""):
                    with open(file_path, "wb") as f:
                        for chunk in response.iter_content(8192):
                            f.write(chunk)

                    print(f"Saved {did}.pdf")
                else:
                    print(f"No direct PDF response for {did}")

            except Exception as e:
                print(f"Error downloading {did}")

            # Pause before next ID
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    finally:
        driver.quit()  # Close browser only when entire chunk is done


# Split all IDs into equal chunks — one chunk per worker
all_dids = list(range(start, end - 1, -1))
chunk_size = len(all_dids) // MAX_WORKERS
chunks = [all_dids[i::MAX_WORKERS] for i in range(MAX_WORKERS)]

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    executor.map(worker, chunks)

print("Done.")
