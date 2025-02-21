import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time
from datetime import datetime
from dateutil import parser
from dateutil.tz import gettz  # For handling timezones

def scrape_toi_cybersecurity():
    # Base URL for TOI cybersecurity news
    url = "https://timesofindia.indiatimes.com/topic/cyber-security/news"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        # Fetch the page
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for bad status codes
        soup = BeautifulSoup(response.text, "lxml")

        # Extract articles
        articles = soup.select('div.uwU81')  # Article container
        news_data = []

        for article in articles:
            try:
                # Extract title
                title_element = article.select_one('div.fHv_i')
                title = title_element.text.strip() if title_element else "No Title"

                # Extract link
                link_element = article.find('a')
                link = link_element['href'] if link_element else None
                if link and not link.startswith('http'):
                    link = f"https://timesofindia.indiatimes.com{link}"

                # Extract summary
                summary_element = article.select_one('p.oxXSK')
                summary = summary_element.text.strip() if summary_element else "No summary"

                # Extract and parse date
                date_element = article.select_one('div.ZxBIG')
                raw_date = date_element.text.strip() if date_element else "Unknown Date"
                parsed_date = parse_date(raw_date)  # Parse the date into a standard format

                # Append article data
                news_data.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "date": parsed_date,
                    "source": "Times of India",
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                print(f"⚠️ Error parsing article: {str(e)[:50]}")

        # Save to MongoDB
        client = MongoClient("mongodb://localhost:27017/")
        db = client["cyber_news_db"]
        collection = db["toi_news"]

        if news_data:
            collection.insert_many(news_data)
            print(f"✅ Saved {len(news_data)} TOI articles!")
        else:
            print("❌ No articles found to save.")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

def parse_date(raw_date):
    """
    Parse the raw date string into a standardized format.
    Handles timezone abbreviations like IST.
    """
    try:
        tzinfos = {'IST': gettz('Asia/Kolkata')}  # Map IST to Indian Standard Time
        return parser.parse(raw_date, fuzzy=True, tzinfos=tzinfos).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"⚠️ Date parsing error: {str(e)[:50]}")
        return "Unknown Date"

if __name__ == "__main__":
    scrape_toi_cybersecurity()
