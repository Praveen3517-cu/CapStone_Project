import json
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from pymongo import MongoClient
from pymongo.errors import PyMongoError

def check_dependencies():
    """Verify system dependencies are installed"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as e:
        print(f"❌ Missing dependencies: {str(e)}")
        print("Run these commands in your workspace:")
        print("sudo apt-get update && sudo apt-get install -y libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libxkbcommon0 libpango-1.0-0 libcairo2")
        sys.exit(1)
        
def mongodb_connection(retries=3, delay=2):
    """Robust MongoDB connection handler with retries"""
    for attempt in range(retries):
        try:
            client = MongoClient(
                "mongodb://localhost:27017/",
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000
            )
            client.admin.command('ping')
            print("✅ Successfully connected to MongoDB")
            return client
        except PyMongoError as e:
            print(f"⚠️ MongoDB connection attempt {attempt+1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    raise ConnectionError("❌ Failed to connect to MongoDB after multiple attempts")

def save_to_mongodb(data):
    """Save data to MongoDB with duplicate prevention"""
    if not data:
        print("⚠️ No data to save")
        return

    try:
        client = mongodb_connection()
        db = client["cyber_news_db"]
        collection = db["cyware_news"]
        
        inserted_count = 0
        for item in data:
            # Update existing or insert new
            result = collection.update_one(
                {"link": item["link"]},
                {"$setOnInsert": item},
                upsert=True
            )
            if result.upserted_id:
                inserted_count += 1
        
        print(f"📥 Saved {inserted_count} new articles (total: {len(data)})")
        
    except Exception as e:
        print(f"❌ MongoDB save error: {e}")
    finally:
        if 'client' in locals():
            client.close()

def scrape_cyware():
    """Main scraping function using Playwright"""
    print("🚀 Starting Cyware scraper...")
    start_time = time.time()
    
    with sync_playwright() as p:
        try:
            # Launch browser with proper configurations
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )
            
            # Create new context with desktop viewport
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            # Navigate to target URL
            print("🌐 Loading page...")
            page.goto("https://cyware.com/search?search=india", timeout=60000)
            
            # Wait for content to load
            page.wait_for_selector(".cy-panel.cy-card.mb-4", timeout=30000)
            
            # Get rendered HTML
            html = page.content()
            soup = BeautifulSoup(html, "lxml")
            
            # Extract articles
            articles = soup.find_all("div", class_="cy-panel")
            news_data = []
            
            print(f"🔍 Found {len(articles)} articles")
            
            for article in articles:
                try:
                    title = article.find("div", class_="cy-card__title").get_text(strip=True)
                    summary = article.find("div", class_="cy-card__description").get_text(strip=True)
                    link = article.find("a")["href"]
                    date = article.find("div", class_="cy-card__meta").get_text(strip=True)
                    
                    news_data.append({
                        "title": title,
                        "summary": summary,
                        "link": link,
                        "date": date,
                        "source": "Cyware",
                        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Exception as e:
                    print(f"⚠️ Error parsing article: {str(e)[:50]}...")
            
            # Save results
            if news_data:
                with open("cyware_news.json", "w") as f:
                    json.dump(news_data, f, indent=4)
                save_to_mongodb(news_data)
            
            print(f"✅ Successfully processed {len(news_data)} articles")
            
        except Exception as e:
            print(f"❌ Scraping failed: {str(e)[:100]}...")
        finally:
            # Clean up
            context.close()
            browser.close()
            print(f"⏱️  Total execution time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    scrape_cyware()
