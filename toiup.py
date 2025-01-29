import os
import json
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

def scrape_toi():
    url = "https://timesofindia.indiatimes.com/topic/cyber-security/news"
    try:
        response = requests.get(url, verify=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        news_data = []

        articles = soup.find_all("div", class_="uwU81")
        for article in articles:
            try:
                title = article.find("div", class_="fHv_i").text.strip()
                summary = article.find("p", class_="oxXSK").text.strip() if article.find("p", class_="oxXSK") else None
                link = article.find("a")["href"]
                if link and not link.startswith("http"):
                    link = f"https://timesofindia.indiatimes.com{link}"

                source_date = article.find("div", class_="ZxBIG").text.strip() if article.find("div", class_="ZxBIG") else None
                author, date = None, None
                if source_date and "/" in source_date:
                    author, date = map(str.strip, source_date.split("/", 1))
                elif source_date:
                    date = source_date.strip()

                news_item = {
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "author": author,
                    "date": date
                }
                news_data.append(news_item)
            except Exception as e:
                print(f"Error parsing article: {e}")

        # Save to JSON
        with open("toi_cybersecurity.json", "w") as f:
            json.dump(news_data, f, indent=4)

        # Save to MongoDB
        client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
        db = client["cyber_news_db"]
        collection = db["toi_news"]
        if news_data:
            collection.insert_many(news_data)

        print("TOI scraping completed!")

    except requests.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    scrape_toi()