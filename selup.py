import os
import re
import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from pymongo import MongoClient
from bs4 import BeautifulSoup
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def setup_driver():
    """Configure headless Chrome driver"""
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

    # Set up WebDriver with the manually installed ChromeDriver
    driver = webdriver.Chrome(service=Service("/usr/local/bin/chromedriver"), options=chrome_options)
    return driver

def scrape_cert_in():
    """Scrape CERT-In advisories"""
    url = "https://www.cert-in.org.in/s2cMainServlet?pageid=PUBVLNOTES01"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    advisories = []

    for row in soup.select("table.table tbody tr"):
        try:
            title = row.select_one("td:nth-child(2)").text.strip()
            link = row.select_one("td:nth-child(2) a")["href"]
            date = row.select_one("td:nth-child(3)").text.strip()
            advisories.append({
                "title": title,
                "link": f"https://www.cert-in.org.in{link}",
                "date": date,
                "source": "CERT-In"
            })
        except Exception as e:
            logger.error(f"Error scraping CERT-In advisory: {e}")

    return advisories

def scrape_nciipc():
    """Scrape NCI-IPC advisories"""
    driver = setup_driver()
    url = "https://nciipc.gov.in/alerts_advisories_more_2023.html"
    driver.get(url)
    advisories = []

    try:
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "liList"))
        )
        logger.info("NCI-IPC page loaded successfully.")

        # Extract data
        elements = driver.find_elements(By.CLASS_NAME, "liList")
        for elem in elements:
            try:
                title = elem.find_element(By.TAG_NAME, "b").text
                description = elem.find_element(By.CLASS_NAME, "advisoryFont").text.strip()
                link = elem.find_element(By.TAG_NAME, "a").get_attribute("href")
                date = elem.find_element(By.CLASS_NAME, "ZxBIG").text.strip()
                advisories.append({
                    "title": title,
                    "description": description,
                    "link": link,
                    "date": date,
                    "source": "NCI-IPC"
                })
            except Exception as e:
                logger.error(f"Error scraping NCI-IPC advisory: {e}")
    except Exception as e:
        logger.error(f"Error loading NCI-IPC page: {e}")
    finally:
        driver.quit()

    return advisories

def scrape_i4c():
    """Scrape I4C news"""
    url = "https://i4c.mha.gov.in/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    news_items = []

    for item in soup.select("div.news-item"):
        try:
            title = item.select_one("h3").text.strip()
            link = item.select_one("a")["href"]
            date = item.select_one("span.date").text.strip()
            news_items.append({
                "title": title,
                "link": f"https://i4c.mha.gov.in{link}",
                "date": date,
                "source": "I4C"
            })
        except Exception as e:
            logger.error(f"Error scraping I4C news: {e}")

    return news_items

def save_to_mongodb(data, collection_name):
    """Save data to MongoDB"""
    client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
    db = client["cyber_news_db"]
    collection = db[collection_name]

    if data:
        for item in data:
            collection.update_one(
                {"link": item["link"]},  # Use link as a unique identifier
                {"$set": item},
                upsert=True
            )
        logger.info(f"Inserted/updated {len(data)} items in {collection_name}.")

def main():
    """Main function to scrape and save data"""
    # Scrape data
    cert_in_data = scrape_cert_in()
    nciipc_data = scrape_nciipc()
    i4c_data = scrape_i4c()

    # Save to JSON
    with open("cyber_news.json", "w") as f:
        json.dump(cert_in_data + nciipc_data + i4c_data, f, indent=4)
    logger.info("Data saved to cyber_news.json.")

    # Save to MongoDB
    save_to_mongodb(cert_in_data, "cert_in_news")
    save_to_mongodb(nciipc_data, "nciipc_advisories")
    save_to_mongodb(i4c_data, "i4c_news")

if __name__ == "__main__":
    main()
