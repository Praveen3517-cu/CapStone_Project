import os
import json
import time
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from pymongo.errors import PyMongoError

def connect_mongodb(retries=3, delay=2):
    """Connect to MongoDB with retries and timeout handling"""
    for attempt in range(retries):
        try:
            client = MongoClient(
                "mongodb://localhost:27017/",
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000
            )
            # Verify connection
            client.admin.command('ping')
            print("Successfully connected to MongoDB")
            return client
        except PyMongoError as e:
            print(f"MongoDB connection attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    raise Exception("Failed to connect to MongoDB after multiple attempts")

def save_to_mongodb(data):
    """Save data to MongoDB with error handling and duplicate prevention"""
    if not data:
        print("No data to save to MongoDB")
        return

    try:
        client = connect_mongodb()
        db = client["cyber_news_db"]
        collection = db["toi_news"]
        
        inserted_count = 0
        for item in data:
            # Prevent duplicates using link as unique identifier
            if not collection.find_one({"link": item["link"]}):
                result = collection.insert_one(item)
                if result.inserted_id:
                    inserted_count += 1
        
        print(f"Successfully inserted {inserted_count}/{len(data)} new articles")
        
    except Exception as e:
        print(f"MongoDB save error: {e}")
    finally:
        if 'client' in locals():
            client.close()

def scrape_toi():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        print("Starting TOI scraping...")
        response = requests.get(
            "https://timesofindia.indiatimes.com/topic/cyber-security/news",
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        news_data = []

        articles = soup.find_all("div", class_="uwU81")
        print(f"Found {len(articles)} articles")
        
        for article in articles:
            try:
                # Title
                title_elem = article.find("div", class_="fHv_i")
                title = title_elem.text.strip() if title_elem else None
                
                # Summary
                summary_elem = article.find("p", class_="oxXSK")
                summary = summary_elem.text.strip() if summary_elem else None
                
                # Link
                link_elem = article.find("a")
                link = link_elem.get("href", "") if link_elem else ""
                if link and not link.startswith("http"):
                    link = f"https://timesofindia.indiatimes.com{link}"
                
                # Source and Date
                source_date_elem = article.find("div", class_="ZxBIG")
                author, date = None, None
                if source_date_elem:
                    source_date = source_date_elem.text.strip()
                    if "/" in source_date:
                        parts = source_date.split("/", 1)
                        author = parts[0].strip() if len(parts) > 0 else None
                        date = parts[1].strip() if len(parts) > 1 else None
                    else:
                        date = source_date.strip()

                news_item = {
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "author": author,
                    "date": date,
                    "source": "Times of India"
                }
                news_data.append(news_item)
                
            except Exception as e:
                print(f"Error parsing article: {str(e)[:100]}...")

        # Save to JSON
        with open("toi_cybersecurity.json", "w") as f:
            json.dump(news_data, f, indent=4)
        print(f"Saved {len(news_data)} articles to JSON")

        # Save to MongoDB
        save_to_mongodb(news_data)
        return len(news_data)

    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return 0
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 0

if __name__ == "__main__":
    start_time = time.time()
    result_count = scrape_toi()
    duration = time.time() - start_time
    print(f"Scraping completed. Retrieved {result_count} articles in {duration:.2f} seconds")
