import feedparser
import threading
import time
from datetime import datetime

# Global Sentiment keywords
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

class NewsManager:
    def __init__(self):
        self.latest_news = []
        self.sentiment_score = 0.0 # -1.0 to 1.0
        self.last_updated = None
        self.feed_url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
        
    def fetch_news(self):
        """
        Fetches RSS feed and updates internal state.
        Returns: (sentiment_score, summarized_reasoning)
        """
        try:
            # Use a browser user agent to avoid blocking
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            # feedparser supports 'agent' param, but sometimes it's better to fetch via requests first
            import requests
            response = requests.get(self.feed_url, headers=headers, timeout=10)
            feed = feedparser.parse(response.content)
            
            if not feed.entries:
                return 0.0, "No news found (Feed Empty)."
                
            entries = feed.entries[:10] # Analyze last 10 headlines
            self.latest_news = []
            
            total_score = 0
            keywords_found = []
            
            for entry in entries:
                title = entry.title.lower()
                score = 0
                
                # Check Bullish
                for word in BULLISH_KEYWORDS:
                    if word in title:
                        score += 1
                        keywords_found.append(f"+{word}")
                        
                # Check Bearish
                for word in BEARISH_KEYWORDS:
                    if word in title:
                        score -= 1
                        keywords_found.append(f"-{word}")
                
                # Weighted score based on position (newer news matters more)
                # But for now, simple sum
                total_score += score
                
                self.latest_news.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published,
                    "score": score
                })
            
            # Normalize Score (-1.0 to 1.0)
            # Assume 10 headlines, max possible score is ~20? 
            # Let's cap it. If score is > 5 it's very bullish.
            self.sentiment_score = max(min(total_score / 5.0, 1.0), -1.0)
            self.last_updated = datetime.now()
            
            # Reasoning string
            sentiment_text = "Neutral"
            if self.sentiment_score > 0.2: sentiment_text = "Bullish"
            if self.sentiment_score > 0.6: sentiment_text = "Very Bullish"
            if self.sentiment_score < -0.2: sentiment_text = "Bearish"
            if self.sentiment_score < -0.6: sentiment_text = "Very Bearish"
            
            reasoning = f"News Sentiment: {sentiment_text} (Score: {self.sentiment_score:.2f}). "
            if keywords_found:
                 unique_keys = list(set(keywords_found))[:5]
                 reasoning += f"Key Drivers: {', '.join(unique_keys)}."
            else:
                 reasoning += "No major keywords detected in recent headlines."
                 
            return self.sentiment_score, reasoning
            
        except Exception as e:
            print(f"News Fetch Error: {e}")
            return 0.0, f"News Error: {e}"

# Global instance
manager = NewsManager()

def get_sentiment():
    return manager.fetch_news()
