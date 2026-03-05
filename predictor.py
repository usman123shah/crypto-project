import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def calculate_bollinger_bands(series, window=20, num_std=2):
    rolling_mean = series.rolling(window=window).mean()
    rolling_std = series.rolling(window=window).std()
    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    return upper_band, lower_band

def calculate_accuracy(historical_df, target_minutes):
    """
    Estimates prediction error (MAE) based on historical volatility.
    Uses Square Root of Time Rule: Vol_T = Vol_Daily * sqrt(T_days)
    """
    if historical_df is None or len(historical_df) < 30: 
        return 0.0
    
    current_price = historical_df['Price'].iloc[-1]
    # Calculate daily volatility (std dev of daily returns)
    daily_returns = historical_df['Price'].pct_change().dropna()
    daily_vol = daily_returns.std()
    
    # Scale to horizon
    target_days = target_minutes / 1440.0
    horizon_vol = daily_vol * np.sqrt(target_days)
    
    # MAE ~ 0.8 * StdDev (assuming normal distribution of errors)
    estimated_mae = current_price * horizon_vol * 0.8
    return estimated_mae

def analyze_and_predict(historical_df, current_session_df, target_minutes, sentiment_score=0.0):
    """
    Analyzes using Technical Indicators (RSI, MACD, BB) + Sentiment.
    Returns: (Predicted Price (float), Reasoning (str))
    """
    reasoning = []
    
    # default to current price if no history
    if historical_df is None or historical_df.empty or len(historical_df) < 50:
        if current_session_df is not None and not current_session_df.empty:
             val = current_session_df['Price'].iloc[-1]
             return val, "Insufficient historical data (Need 50+ days for TA). Prediction based on current price only."
        return 0.0, "No Data Available."

    # Prepare Data merging History + Live Session
    df = historical_df.copy()
    
    # INJECT LIVE PRICE:
    # If we have session data, we must update the last candle or append a new one
    # so that the indicators (RSI, MACD) reflect the *current* price, not yesterday's close.
    if current_session_df is not None and not current_session_df.empty:
        current_live_price = current_session_df['Price'].iloc[-1]
        current_live_time = current_session_df['Timestamp'].iloc[-1]
        
        # Check if the last row in history is today/recent
        last_hist_time = df['Timestamp'].iloc[-1]
        
        # If history is daily, and today is a new day (or same day), we essentially want to
        # "update" the latest data point to be the current price for calculation purposes.
        # A simple way: Append a new row representing "Now"
        
        new_row = pd.DataFrame([{
            'Timestamp': current_live_time,
            'Price': current_live_price
        }])
        
        # If the last history point is old (>1 day), append.
        # If it's today, replace/update (or just append a "Live" row for TA sake).
        # For TA, appending a "Live" row is usually best to see current state.
        df = pd.concat([df, new_row], ignore_index=True)

    prices = df['Price']
    current_price = prices.iloc[-1]
    
    # --- 1. Technical Analysis ---
    
    # RSI
    rsi = calculate_rsi(prices).iloc[-1]
    rsi_signal = 0 # -1 (Bear), 0 (Neutral), 1 (Bull)
    rsi_text = "Neutral"
    
    if rsi > 70:
        rsi_signal = -1 # Overbought -> Sell
        rsi_text = "Overbought (Bearish)"
    elif rsi < 30:
        rsi_signal = 1 # Oversold -> Buy
        rsi_text = "Oversold (Bullish)"
        
    reasoning.append(f"1. RSI (14): {rsi:.1f} - {rsi_text}")

    # MACD
    macd, signal = calculate_macd(prices)
    macd_val = macd.iloc[-1]
    signal_val = signal.iloc[-1]
    macd_hist = macd_val - signal_val
    
    macd_signal = 0
    macd_text = "Neutral"
    if macd_val > signal_val:
        macd_signal = 1
        macd_text = "Bullish Crossover"
    else:
        macd_signal = -1
        macd_text = "Bearish Crossover"
        
    reasoning.append(f"2. MACD: {macd_text} (Hist: {macd_hist:.2f})")
    
    # Bollinger Bands
    upper, lower = calculate_bollinger_bands(prices)
    up_band = upper.iloc[-1]
    low_band = lower.iloc[-1]
    
    bb_signal = 0
    bb_text = "Within Bands"
    
    # Simple Mean Reversion logic
    if current_price > up_band:
        bb_signal = -1 # Price too high
        bb_text = "Above Upper Band (Overextended)"
    elif current_price < low_band:
        bb_signal = 1 # Price too low
        bb_text = "Below Lower Band (Value Zone)"
    
    reasoning.append(f"3. Bollinger Bands: {bb_text}")
    
    # --- 2. Consensus Building ---
    
    # Base Drift (Long Term Trend)
    # 50-day SMA Slope
    sma50 = prices.rolling(window=50).mean().iloc[-1]
    sma200 = prices.rolling(window=200).mean().iloc[-1] if len(prices) > 200 else sma50
    
    trend_score = 0
    if current_price > sma50: trend_score += 1
    if current_price > sma200: trend_score += 1
    
    trend_text = "Bullish" if trend_score > 0 else "Bearish"
    reasoning.append(f"4. Trend (SMA 50/200): {trend_text}")
    
    # Weighing the signals
    # RSI: 30%, MACD: 30%, BB: 20%, Trend: 20%
    technical_score = (rsi_signal * 0.3) + (macd_signal * 0.3) + (bb_signal * 0.2) + ( (1 if trend_score > 0 else -1) * 0.2)
    
    # --- 3. News Sentiment Integration ---
    # Sentiment is -1.0 to 1.0
    # Weighted 20% vs Technicals 80% for final direction
    
    final_score = (technical_score * 0.8) + (sentiment_score * 0.2)
    
    direction = "Sideways"
    if final_score > 0.2: direction = "Bullish"
    elif final_score < -0.2: direction = "Bearish"
    
    reasoning.append(f"-> Consensus Score: {final_score:.2f} ({direction})")
    
    # --- 4. Prediction Calculation ---
    
    # Volatility Assessment
    daily_vol = prices.pct_change().std()
    target_days = target_minutes / 1440.0
    expected_move_pct = daily_vol * np.sqrt(target_days)
    
    # Scale move by conviction (score)
    # If score is 1.0 (Max Bullish), we predict +1 StdDev move
    # If score is 0.0, we predict 0 move
    predicted_change = expected_move_pct * final_score
    
    final_prediction = current_price * (1 + predicted_change)
    
    # --- 5. Session Momentum (Micro-Adjustment) ---
    # ALWAYS Apply slight momentum adjustment to prevent lag
    if current_session_df is not None and not current_session_df.empty and len(current_session_df) > 5:
        short_start_price = current_session_df['Price'].iloc[0]
        short_end_price = current_session_df['Price'].iloc[-1]
        
        # Calculate Time Delta in Minutes
        start_time = current_session_df['Timestamp'].iloc[0]
        end_time = current_session_df['Timestamp'].iloc[-1]
        time_diff = (end_time - start_time).total_seconds() / 60.0
        
        if time_diff > 0:
            # Velocity: Price Change per Minute
            price_change = short_end_price - short_start_price
            velocity_per_min = price_change / time_diff
            
            # Project this velocity forward
            momentum_projection = short_end_price + (velocity_per_min * target_minutes)
            
            # Dampen extreme projections (e.g. flash crash in 1 min shouldn't project to 0 in 1 hour)
            # Cap the max change from momentum to 5% of price to stay sane
            max_change = short_end_price * 0.05
            change = momentum_projection - short_end_price
            
            if abs(change) > max_change:
                momentum_projection = short_end_price + (max_change if change > 0 else -max_change)

            # If target is very short term (< 1 hour), session momentum matters A LOT (50%)
            if target_minutes < 60:
                 weight_micro = 0.5
            else:
                 # Even for long term, let's give 20% weight to "What is happening RIGHT NOW"
                 weight_micro = 0.2
            
            weight_tech = 1.0 - weight_micro
            final_prediction = (final_prediction * weight_tech) + (momentum_projection * weight_micro)
            reasoning.append(f"-> Live Momentum: ${velocity_per_min:+.2f}/min (Weight: {weight_micro*100:.0f}%)")
        else:
             reasoning.append("-> Live Momentum: Insufficient time duration.")

    # Accuracy Estimation
    accuracy = calculate_accuracy(historical_df, target_minutes)
    reasoning.append(f"-> Est. Accuracy: ±${accuracy:.2f}")

    return final_prediction, "\n".join(reasoning)
