import json
import time
import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from pymongo import MongoClient

def check_playwright_setup():
    """Verify Playwright browsers are properly installed"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as e:
        print(f"❌ Playwright setup error: {str(e)}")
        print("Run these commands:")
        print("  python -m playwright install chromium")
        print("  python -m playwright install-deps")
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
        except Exception as e:
            print(f"⚠️ MongoDB connection attempt {attempt+1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    raise ConnectionError("❌ Failed to connect to MongoDB after multiple attempts")

def scrape_cyware():
    """Main scraping function using Playwright"""
    print("🚀 Starting Cyware scraper...")
    start_time = time.time()
    
    # Initialize variables to avoid UnboundLocalError
    browser = None
    context = None
    
    try:
        # Verify dependencies first
        check_playwright_setup()
        
        # Launch browser with proper configurations
        with sync_playwright() as p:
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
                
                # Save to MongoDB
                client = mongodb_connection()
                db = client["cyber_news_db"]
                collection = db["cyware_news"]
                
                inserted_count = 0
                for item in news_data:
                    result = collection.update_one(
                        {"link": item["link"]},
                        {"$setOnInsert": item},
                        upsert=True
                    )
                    if result.upserted_id:
                        inserted_count += 1
                
                print(f"📥 Saved {inserted_count} new articles (total: {len(news_data)})")
                client.close()
            
            print(f"✅ Successfully processed {len(news_data)} articles")
            
    except Exception as e:
        print(f"❌ Scraping failed: {str(e)[:100]}...")
    finally:
        # Clean up resources safely
        try:
            if context:
                context.close()
            if browser:
                browser.close()
        except Exception as e:
            print(f"⚠️ Cleanup error: {str(e)[:50]}...")
        
        print(f"⏱️  Total execution time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    scrape_cyware()
