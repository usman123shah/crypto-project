import os
import requests
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from dotenv import load_dotenv

load_dotenv()

BINANCE_BASE_URL = "https://api.binance.com/api/v3/ticker/price"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3/simple/price"

CSV_FILE = "history.csv"

def get_binance_price(symbol):
    """
    Fetches price from Binance.
    symbol: e.g., 'BTCUSDT'
    """
    api_key = os.getenv("BINANCE_API_KEY")
    headers = {"X-MBX-APIKEY": api_key} if api_key else {}
    
    try:
        params = {"symbol": symbol}
        response = requests.get(BINANCE_BASE_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print(f"Binance API failed: {e}")
        return None

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
    Tries Binance first, then CoinGecko.
    coin: 'BTC' or 'ETH'
    Returns: (price, source) or (None, None)
    """
    # Map coin to Binance Symbol and CoinGecko ID
    mapping = {
        'BTC': {'binance': 'BTCUSDT', 'coingecko': 'bitcoin'},
        'ETH': {'binance': 'ETHUSDT', 'coingecko': 'ethereum'}
    }
    
    if coin not in mapping:
        return None, None

    config = mapping[coin]
    
    # Try Binance
    price = get_binance_price(config['binance'])
    if price is not None:
        return price, "Binance"
    
    # Try CoinGecko
    price = get_coingecko_price(config['coingecko'])
    if price is not None:
        return price, "CoinGecko"
        
    return None, None

def save_to_csv(coin, price, predicted_price=None, target_horizon=None):
    """
    Appends data to CSV file.
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    # Handle predicted_price
    pred_val = predicted_price if predicted_price is not None else ""
    # Handle horizon
    horizon_val = target_horizon if target_horizon is not None else ""
    
    df = pd.DataFrame([{
        "Date": date_str,
        "Time": time_str,
        "Coin": coin,
        "Price": price,
        "Predicted_Price": pred_val,
        "Target_Horizon": horizon_val
    }])
    
    try:
        if not os.path.exists(CSV_FILE):
            df.to_csv(CSV_FILE, index=False)
        else:
            # Just append. 
            df.to_csv(CSV_FILE, mode='a', header=False, index=False)
    except PermissionError:
        print("Error: data file is open in another program. Cannot save.")
        return False
    except Exception as e:
        print(f"Save Error: {e}")
        return False
    return True

def load_data():
    """
    Loads the full history into a DataFrame.
    Returns empty DF if file doesn't exist.
    """
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            # Reconstruct Timestamp if we split columns
            if 'Date' in df.columns and 'Time' in df.columns and 'Timestamp' not in df.columns:
                try:
                    df['Timestamp'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
                except Exception as e:
                    print(f"Timestamp reconstruction error: {e}")
                    pass
            return df
        except:
            return pd.DataFrame() # Corrupt file or other error

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
        # Map symbol to CoinGecko ID
        symbol_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "BNB": "binancecoin",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin"
        }
        coin_id = symbol_map.get(symbol.upper(), "bitcoin") # Default to bitcoin
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "365",
            "interval": "daily"
        }
        
        # CoinGecko can be slow, standard version has strict rate limits
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Format: "prices": [ [timestamp_ms, price], ... ]
        prices = data.get("prices", [])
        
        records = []
        for p in prices:
            records.append({
                "Timestamp": datetime.fromtimestamp(p[0] / 1000),
                "Price": float(p[1])
            })
            
        print(f"Loaded {len(records)} days from CoinGecko.")
        return pd.DataFrame(records)
        
    except Exception as e:
        print(f"CoinGecko API failed: {e}")
        return pd.DataFrame()

def load_local_data(symbol=None):
    """
    Tries to load 'historical_data.csv' or files from 'datasets/' folder.
    Resamples to Daily.
    params: symbol (str) - e.g. 'ETH' to filter specifically.
    """
    try:
        df = pd.DataFrame()
        
        # 1. Check specific file
        if os.path.exists("historical_data.csv"):
            print("Found historical_data.csv...")
            df = pd.read_csv("historical_data.csv")
            
        # 2. Check datasets folder if specific file not found
        elif os.path.exists("datasets"):
             for file in os.listdir("datasets"):
                 if file.endswith(".csv"):
                     # Check if filename contains symbol (simple heuristic)
                     if symbol and symbol.lower() in file.lower():
                         print(f"Found specific dataset for {symbol}: {file}")
                         df = pd.read_csv(os.path.join("datasets", file))
                         break
                     elif not symbol:
                         # Fallback to any file if no symbol specified
                         print(f"Found dataset: {file}")
                         df = pd.read_csv(os.path.join("datasets", file))
                         break 
        
        if df.empty:
            return pd.DataFrame()

        # Normalize Columns
        cols = [c.lower() for c in df.columns]
        df.columns = cols
        
        # Map common names
        rename_map = {}
        for c in df.columns:
            if c in ['date', 'time', 'unix', 'timestamp']:
                rename_map[c] = 'Timestamp'
            elif c in ['close', 'price', 'value', 'close_price']:
                rename_map[c] = 'Price'
            elif c in ['coin', 'symbol', 'asset']:
                rename_map[c] = 'Coin'
        
        df = df.rename(columns=rename_map)
        
        if 'Timestamp' not in df.columns or 'Price' not in df.columns:
            print("CSV missing required columns (Need Date/Timestamp and Price/Close)")
            return pd.DataFrame()
            
        # FILTER BY SYMBOL IF REQUESTED
        if symbol and 'Coin' in df.columns:
            # Check if any row matches symbol
            if not df[df['Coin'] == symbol].empty:
                df = df[df['Coin'] == symbol]
                print(f"Filtered for {symbol}. Rows: {len(df)}")
            else:
                print(f"Warning: Local file has 'Coin' column but no data for {symbol}.")
                # If we asked for ETH but file only has BTC, return empty to trigger fallback or fail safely
                # But if the file has NO coin column, we assume it's the right one (risky but okay for now)
                return pd.DataFrame() 

        # Convert Timestamp
        # Check if Unix (float/int) or String
        first_val = df['Timestamp'].iloc[0]
        if isinstance(first_val, (int, float)) or str(first_val).replace('.', '', 1).isdigit():
             df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s')
        else:
             df['Timestamp'] = pd.to_datetime(df['Timestamp'])
             
        # Resample to Daily
        df = df.set_index('Timestamp')
        # Only numeric columns
        numeric_cols = df.select_dtypes(include=[float, int]).columns
        df_daily = df[numeric_cols].resample('D').last().reset_index()
        
        # Filter last 365 days
        cutoff = datetime.now() - timedelta(days=365)
        df_daily = df_daily[df_daily['Timestamp'] > cutoff]
        
        print(f"Loaded {len(df_daily)} days from Local File.")
        return df_daily

    except Exception as e:
        print(f"Local File Load failed: {e}")
        return pd.DataFrame()

def get_historical_data(symbol, interval='1d', limit=365):
    """
    Priority: Binance -> CoinGecko -> Yahoo -> Local File
    """
    # 1. Try Binance
    try:
        api_key = os.getenv("BINANCE_API_KEY")
        headers = {"X-MBX-APIKEY": api_key} if api_key else {}
        base_url = "https://api.binance.com/api/v3/klines"
        
        if symbol == "BTC": pair = "BTCUSDT"
        elif symbol == "ETH": pair = "ETHUSDT"
        else: pair = f"{symbol}USDT"
            
        params = {"symbol": pair, "interval": interval, "limit": limit}
        
        # 3s timeout
        response = requests.get(base_url, params=params, headers=headers, timeout=3)
        response.raise_for_status()
        data = response.json()
        
        records = []
        for candle in data:
            timestamp = candle[0]
            records.append({
                "Timestamp": datetime.fromtimestamp(timestamp / 1000),
                "Price": float(candle[4])
            })
            
        print("Loaded history from Binance.")
        return pd.DataFrame(records)
        
    except Exception as e:
        print(f"Binance API failed: {e}")
        print("Trying CoinGecko...")

    # 2. Try CoinGecko
    df_cg = get_coingecko_data(symbol)
    if not df_cg.empty:
        return df_cg
        
    print("Trying Yahoo Finance...")

    # 3. Try Yahoo Finance
    if YFINANCE_AVAILABLE:
        try:
            ticker = f"{symbol}-USD"
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if not df.empty:
                df = df.reset_index()
                # Handle YF column inconsistencies
                if 'Date' in df.columns: df = df.rename(columns={'Date': 'Timestamp', 'Close': 'Price'})
                elif 'Datetime' in df.columns: df = df.rename(columns={'Datetime': 'Timestamp', 'Close': 'Price'})
                
                # If MultiIndex (new YF), flatten it
                if isinstance(df.columns, pd.MultiIndex):
                     df.columns = df.columns.get_level_values(0)
                
                # Check again after flatten
                if 'Close' in df.columns:
                     df = df.rename(columns={'Close': 'Price'})

                df = df[['Timestamp', 'Price']]
                print(f"Loaded {len(df)} days from Yahoo Finance.")
                return df
        except Exception as e:
            print(f"Yahoo Finance failed: {e}")
            
    # 4. Try Local File
    print("Trying Local Files...")
    df_local = load_local_data(symbol)
    if not df_local.empty:
        return df_local
        
    return pd.DataFrame()

def export_to_pdf(output_path="report.pdf"):
    """
    Reads history.csv and generates a PDF report.
    """
    if not os.path.exists(CSV_FILE):
        return False, "No data to export."

    try:
        df = pd.read_csv(CSV_FILE)
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        pdf.cell(200, 10, txt="Crypto Data Report", ln=1, align='C')
        pdf.ln(10)
        
        # Table Header logic needs to adapt to columns present
        pdf.set_font("Arial", 'B', 8) # Smaller font for more columns
        
        cols = df.columns.tolist()
        # Basic layout estimate
        col_width = 190 / len(cols)
        
        for col in cols:
            pdf.cell(col_width, 10, str(col), 1)
        pdf.ln()
        
        # Table Rows
        pdf.set_font("Arial", size=8)
        for index, row in df.iterrows():
            for col in cols:
                # Truncate if too long
                val = str(row[col])[:20] 
                pdf.cell(col_width, 10, val, 1)
            pdf.ln()
            
        pdf.output(output_path)
        return True, f"Exported to {output_path}"
    except Exception as e:
        return False, str(e)
