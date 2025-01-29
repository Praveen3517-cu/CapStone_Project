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
    """Configure headless Chrome driver for Gitpod."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    return driver

def scrape_cyware():
    driver = setup_driver()
    url = "https://cyware.com/search?search=india"
    driver.get(url)
    time.sleep(3)  # Allow page to load

    articles = driver.find_elements(By.CLASS_NAME, "cy-panel.cy-card.mb-4")
    news_data = []

    for article in articles:
        try:
            title = article.find_element(By.CLASS_NAME, "cy-card__title").text.strip()
            summary = article.find_element(By.CLASS_NAME, "cy-card__description").text.strip()
            link = article.find_element(By.TAG_NAME, "a").get_attribute("href")
            date = None

            # Extract date from meta elements
            date_elements = article.find_elements(By.CLASS_NAME, "cy-card__meta")
            for elem in date_elements:
                if re.match(r'\w+ \d{1,2}, \d{4}', elem.text.strip()):
                    date = elem.text.strip()
                    break

            news_item = {
                "title": title,
                "summary": summary,
                "link": link,
                "date": date
            }
            news_data.append(news_item)
        except Exception as e:
            print(f"Error scraping article: {e}")

    # Save to JSON
    with open("cyware_news.json", "w") as f:
        json.dump(news_data, f, indent=4)

    # Save to MongoDB
    client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
    db = client["cyber_news_db"]
    collection = db["cyware_news"]
    if news_data:
        collection.insert_many(news_data)

    driver.quit()
    print("Cyware scraping completed!")

if __name__ == "__main__":
    scrape_cyware()