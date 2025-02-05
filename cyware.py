import os
import re
import time
import json
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from pymongo import MongoClient

def setup_driver():
    """Configure Chrome for Gitpod with proper path resolution"""
    # Force PATH to include Chrome location
    os.environ["PATH"] += os.pathsep + "/usr/bin"
    
    # Install matching chromedriver
    chromedriver_autoinstaller.install()
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.binary_location = "/usr/bin/google-chrome-stable"

    return webdriver.Chrome(options=chrome_options)

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
