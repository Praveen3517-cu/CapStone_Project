import os
import re
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient

def setup_driver():
    """Configure headless Chrome driver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    return driver

def scrape_nciipc():
    driver = setup_driver()
    url = "https://nciipc.gov.in/alerts_advisories_more_2023.html"
    driver.get(url)
    time.sleep(2)

    vulnerabilities = []
    cve_pattern = re.compile(r"CVE-\d{4}-\d{4,7}")
    date_pattern = re.compile(r"\(\d{2} \w+ \d{4}\)")

    elements = driver.find_elements(By.CLASS_NAME, "liList")
    for elem in elements:
        try:
            title = elem.find_element(By.TAG_NAME, "b").text
            description = elem.find_element(By.CLASS_NAME, "advisoryFont").text.strip()
            link = elem.find_element(By.TAG_NAME, "a").get_attribute("href")
            cve_ids = cve_pattern.findall(description)
            date_match = date_pattern.search(title)
            date = date_match.group(0).strip("()") if date_match else None

            vulnerability = {
                "title": title,
                "description": description,
                "link": link,
                "cve_ids": cve_ids,
                "date": date
            }
            vulnerabilities.append(vulnerability)
        except Exception as e:
            print(f"Error scraping advisory: {e}")

    # Save to JSON
    with open("nciipc_advisories.json", "w") as f:
        json.dump(vulnerabilities, f, indent=4)

    # Save to MongoDB
    client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
    db = client["cyber_news_db"]
    collection = db["nciipc_advisories"]
    if vulnerabilities:
        collection.insert_many(vulnerabilities)

    driver.quit()
    print("NCI-IPC scraping completed!")

if __name__ == "__main__":
    scrape_nciipc()