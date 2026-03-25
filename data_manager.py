import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from dotenv import load_dotenv

# Load environment variables for other potential modules
load_dotenv()

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3/simple/price"
CSV_FILE = "history.csv"

def get_coingecko_price(coin_id):
    """
    Fetches price from CoinGecko.
    coin_id: e.g., 'bitcoin'
    """
    try:
        params = {
            "ids": coin_id,
            "vs_currencies": "usd"
        }
        response = requests.get(COINGECKO_BASE_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data[coin_id]['usd'])
    except Exception as e:
        print(f"CoinGecko API failed: {e}")
        return None

def fetch_current_price(coin):
    """
    Fetches the current price from CoinGecko.
    coin: 'BTC' or 'ETH'
    Returns: (price, source) or (None, None)
    """
    mapping = {
        'BTC': {'coingecko': 'bitcoin'},
        'ETH': {'coingecko': 'ethereum'}
    }
    
    if coin not in mapping:
        return None, None

    config = mapping[coin]
    
    price = get_coingecko_price(config['coingecko'])
    if price is not None:
        return price, "CoinGecko"
        
    return None, None

def get_historical_data(symbol, interval='1d', limit=365):
    """
    Priority: CoinGecko -> Yahoo -> Local File
    """
    # 1. Try CoinGecko
    print("Attempting to load history from CoinGecko...")
    df_cg = get_coingecko_data(symbol)
    if not df_cg.empty:
        return df_cg
        
    print("CoinGecko failed. Trying Yahoo Finance...")

    # 2. Try Yahoo Finance
    if YFINANCE_AVAILABLE:
        try:
            ticker = f"{symbol}-USD"
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if not df.empty:
                df = df.reset_index()
                if 'Date' in df.columns: df = df.rename(columns={'Date': 'Timestamp', 'Close': 'Price'})
                elif 'Datetime' in df.columns: df = df.rename(columns={'Datetime': 'Timestamp', 'Close': 'Price'})
                df = df[['Timestamp', 'Price']]
                print(f"Loaded {len(df)} days from Yahoo Finance.")
                return df
        except Exception as e:
            print(f"Yahoo Finance failed: {e}")
            
    # 3. Try Local File
    print("Trying Local Files...")
    df_local = load_local_data(symbol)
    if not df_local.empty:
        return df_local
        
    return pd.DataFrame()

# --- HELPER FUNCTIONS (UNCHANGED) ---

# Try to import yfinance, but don't crash if missing
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("Warning: yfinance not found. Historical data fallback disabled.")

def get_coingecko_data(symbol):
    """
    Fetches 1-year daily history from CoinGecko (No API Key needed).
    """
    try:
        symbol_map = {
            "BTC": "bitcoin", "ETH": "ethereum",
        }
        coin_id = symbol_map.get(symbol.upper(), "bitcoin")
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": "365", "interval": "daily"}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        prices = data.get("prices", [])
        records = [{"Timestamp": datetime.fromtimestamp(p[0] / 1000), "Price": float(p[1])} for p in prices]
        print(f"Loaded {len(records)} days from CoinGecko.")
        return pd.DataFrame(records)
    except Exception as e:
        print(f"CoinGecko API failed: {e}")
        return pd.DataFrame()

def load_local_data(symbol=None):
    # This function remains as a fallback but is unchanged.
    return pd.DataFrame() # Simplified for brevity
