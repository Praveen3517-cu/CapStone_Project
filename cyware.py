import os
import re
import time
import json
import subprocess
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from pymongo import MongoClient

# Hardcoded Chrome path verified in Gitpod
CHROME_PATH = "/usr/bin/google-chrome-stable"
CHROMEDRIVER_DIR = "/workspace/chromedriver"

def verify_chrome_installation():
    """Ensure Chrome is installed in expected location"""
    if not os.path.exists(CHROME_PATH):
        raise FileNotFoundError(
            f"Chrome not found at {CHROME_PATH}. "
            "Check installation in .gitpod.yml"
        )
    
    try:
        version_output = subprocess.check_output(
            [CHROME_PATH, "--version"],
            stderr=subprocess.STDOUT,
            text=True
        )
        print(f"Chrome version: {version_output.strip()}")
    except Exception as e:
        raise RuntimeError(f"Chrome verification failed: {str(e)}")

def setup_driver():
    """Configure Chrome with direct path access"""
    # Verify Chrome installation first
    verify_chrome_installation()
    
    # Install chromedriver
    os.makedirs(CHROMEDRIVER_DIR, exist_ok=True)
    chromedriver_path = chromedriver_autoinstaller.install(
        path=CHROMEDRIVER_DIR,
        detach=True,
        chmod=True
    )
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.binary_location = CHROME_PATH
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920x1080")

    return webdriver.Chrome(
        service=Service(chromedriver_path),
        options=chrome_options
    )
def scrape_cyware():
    driver = setup_driver()
    url = "https://cyware.com/search?search=india"

    try:
        driver.get(url)
        time.sleep(3)

        articles = driver.find_elements(By.CLASS_NAME, "cy-panel.cy-card.mb-4")
        news_data = []

        for article in articles:
            try:
                title = article.find_element(By.CLASS_NAME, "cy-card__title").text.strip()
                summary = article.find_element(By.CLASS_NAME, "cy-card__description").text.strip()
                link = article.find_element(By.TAG_NAME, "a").get_attribute("href")
                date = None

                date_elements = article.find_elements(By.CLASS_NAME, "cy-card__meta")
                for elem in date_elements:
                    if re.match(r'\w+ \d{1,2}, \d{4}', elem.text.strip()):
                        date = elem.text.strip()
                        break

                news_data.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "date": date
                })
            except Exception as e:
                print(f"Error parsing article: {e}")

        # Save to JSON
        with open("cyware_news.json", "w") as f:
            json.dump(news_data, f, indent=4)

        # Save to MongoDB
        client = MongoClient("mongodb://localhost:27017/")
        db = client["cyber_news_db"]
        collection = db["cyware_news"]
        if news_data:
            collection.insert_many(news_data)

        print("Scraping completed successfully!")

    except Exception as e:
        print(f"Scraping failed: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_cyware()
