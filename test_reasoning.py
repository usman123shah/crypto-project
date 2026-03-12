
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import predictor

def test_prediction():
    print("Testing Predictor Logic...")
    
    # Mock Historical Data (1 Year)
    # create a bullish trend: 30% growth over year
    base_time = datetime.now() - timedelta(days=365)
    days = 365
    dates = [base_time + timedelta(days=i) for i in range(days)]
    # Start at 100, end at 130
    prices = [100 * (1 + (0.3 * i/days)) + np.random.normal(0, 1) for i in range(days)]
    
    historical_df = pd.DataFrame({'Timestamp': dates, 'Price': prices})
    
    # Mock Session Data (Last 5 mins)
    # Flat/Stable
    now = datetime.now()
    session_times = [now - timedelta(seconds=i) for i in range(300)]
    session_times.reverse()
    session_prices = [130 + np.random.normal(0, 0.1) for _ in range(300)]
    
    session_df = pd.DataFrame({'Timestamp': session_times, 'Price': session_prices})
    
    # Predict 60 mins ahead
    print("\n--- Testing Prediction ---")
    pred_price, reasoning = predictor.analyze_and_predict(historical_df, session_df, 60)
    
    print(f"Predicted Price: {pred_price:.2f}")
    print("Reasoning Output:")
    print(reasoning)
    
    # Verification
    if "1 Year" in reasoning and "Trend" in reasoning:
        print("\nPASS: Reasoning correctly identifies trend context.")
    else:
        print("\nFAIL: Reasoning text missing key context.")
        
    if pred_price > 129:
        print("PASS: Prediction respects bullish yearly trend.")
    else:
        print("FAIL: Prediction ignored bullish trend.")

if __name__ == "__main__":
    test_prediction()
