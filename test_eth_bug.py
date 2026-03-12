
import pandas as pd
import predictor

def test_mismatched_data():
    print("Testing Mismatched Data (BTC History + ETH Current)...")
    
    # Mock BTC History (Price ~90k)
    btc_history = pd.DataFrame({
        'Timestamp': pd.date_range(start='2024-01-01', periods=365, freq='D'),
        'Price': [90000.0] * 365
    })
    
    # Mock ETH Session (Price ~2k)
    eth_session = pd.DataFrame({
        'Timestamp': pd.date_range(start='2025-01-01 12:00', periods=10, freq='min'),
        'Price': [2500.0] * 10
    })
    
    # Predict
    # If the bug exists, the prediction will be weighted towards 90k, not 2k.
    pred, reasoning = predictor.analyze_and_predict(btc_history, eth_session, 30)
    
    print(f"BTC History Price: $90,000")
    print(f"ETH Current Price: $2,500")
    print(f"Prediction: ${pred:,.2f}")
    
    if pred > 10000:
        print("FAIL: Prediction is wildly influenced by mismatched BTC history.")
    else:
        print("PASS: Prediction seems reasonable (close to ETH price).")

if __name__ == "__main__":
    test_mismatched_data()
