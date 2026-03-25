
import feedparser
import time
from datetime import datetime, timedelta
import requests

# --- Constants ---
BULLISH_KEYWORDS = [
    "etf", "approval", "adoption", "record", "bull", "surge", "soar", "gain", "rally", "buy",
    "long", "support", "upgrade", "launch", "partnership", "integration", "institutional",
    "accumulate", "breakout", "positive"
]

BEARISH_KEYWORDS = [
    "ban", "regulation", "sec", "lawsuit", "crash", "hack", "sell", "bear", "drop", "plunge",
    "dump", "resistance", "downgrade", "scam", "fraud", "investigation", "fine", "delay",
    "reject", "negative", "insolvency", "bankruptcy"
]

# --- Singleton News Manager Class ---
class NewsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NewsManager, cls).__new__(cls)
            # Initialize state only once
            cls._instance.latest_news = []
            cls._instance.sentiment_score = 0.0
            cls._instance.sentiment_reasoning = "Initializing..."
            cls._instance.last_updated = None
            cls._instance.feed_url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
            cls._instance.fetch_interval = timedelta(minutes=15)
        return cls._instance

    def fetch_news_and_analyze(self):
        """
        Fetches RSS feed, analyzes sentiment, and updates the instance's state.
        This method contains the actual network request and processing.
        """
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(self.feed_url, headers=headers, timeout=10)
            feed = feedparser.parse(response.content)

            if not feed.entries:
                self.sentiment_score = 0.0
                self.sentiment_reasoning = "No news found in the feed."
                return

            entries = feed.entries[:10]  # Analyze the 10 most recent headlines
            self.latest_news = []
            total_score = 0
            keywords_found = []

            for entry in entries:
                title = entry.title.lower()
                score = 0
                for kw in BULLISH_KEYWORDS:
                    if kw in title:
                        score += 1
                        keywords_found.append(kw.upper())
                for kw in BEARISH_KEYWORDS:
                    if kw in title:
                        score -= 1
                        keywords_found.append(kw.upper())
                
                if score != 0:
                    self.latest_news.append({'title': entry.title, 'score': score})
                total_score += score

            # Update state
            self.sentiment_score = total_score / len(entries) if entries else 0.0
            self.last_updated = datetime.now()

            # Create reasoning string
            reasoning = f"News Sentiment Score: {self.sentiment_score:.2f}. "
            if keywords_found:
                reasoning += f"Key drivers: { ', '.join(list(set(keywords_found))[:5]) }."
            else:
                reasoning += "Neutral market chatter."
            self.sentiment_reasoning = reasoning

        except Exception as e:
            # If fetching fails, keep the old score but update reasoning with the error
            self.sentiment_reasoning = f"Error fetching news: {e}"
            # Optionally log this error

# --- Public Interface Function ---

def get_sentiment():
    """
    This is the main function to be called from the Streamlit app.
    It uses the singleton manager to fetch news only when the cache is stale.
    Returns the cached sentiment score and reasoning.
    """
    manager = NewsManager() # Gets the singleton instance
    now = datetime.now()

    # Fetch only if it has never been fetched OR if the fetch interval has passed
    if manager.last_updated is None or (now - manager.last_updated) > manager.fetch_interval:
        manager.fetch_news_and_analyze()
    
    return manager.sentiment_score, manager.sentiment_reasoning

# To maintain compatibility with old imports if they exist
manager = NewsManager()
