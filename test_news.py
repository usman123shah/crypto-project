import news_manager
import time

print("Testing News Manager...")
score, reasoning = news_manager.manager.fetch_news()

print(f"Sentiment Score: {score}")
print(f"Reasoning: {reasoning}")
print("Done.")
