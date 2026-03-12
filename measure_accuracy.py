import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import sys
import os

# Redirect print to file AND stdout
class Tee(object):
    def __init__(self, name, mode):
        self.file = open(name, mode)
        self.stdout = sys.stdout
        sys.stdout = self
    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)
        self.file.flush()
        self.stdout.flush()
    def flush(self):
        self.file.flush()
        self.stdout.flush()

# Hook stdout
sys.stdout = Tee('accuracy_report.txt', 'w')

print(f"Starting Backtest v2 at {datetime.now()}...", flush=True)

try:
    sys.path.append(os.getcwd())
    import predictor
    import data_manager
    print("Modules imported successfully.", flush=True)
except Exception as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def run_backtest():
    print("Loading data...", flush=True)
    df = pd.DataFrame()
    high_res = False
    
    # Try specific high-res file first
    target_file = 'datasets/btcusd_1-min_data.csv'
    if os.path.exists(target_file):
        print(f"Reading '{target_file}' (limit 50k rows)...", flush=True)
        try:
            df = pd.read_csv(target_file, nrows=50000)
            
            # Normalize columns
            cols = [c.lower() for c in df.columns]
            df.columns = cols
            
            # Smart rename
            rename_map = {}
            for c in df.columns:
                if 'timestamp' in c or 'date' in c: rename_map[c] = 'Timestamp'
                if 'close' in c or 'price' in c: rename_map[c] = 'Price'
            df = df.rename(columns=rename_map)
            
            if 'Timestamp' in df.columns and 'Price' in df.columns:
                # Convert
                first_val = df['Timestamp'].iloc[0]
                if isinstance(first_val, (int, float)) or str(first_val).replace('.', '', 1).isdigit():
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s')
                else:
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                
                df = df.sort_values('Timestamp')
                high_res = True
                print("High-res data loaded successfully.", flush=True)
            else:
                print("High-res file missing required columns.", flush=True)
                df = pd.DataFrame() # Reset
        except Exception as e:
            print(f"Error reading high-res file: {e}", flush=True)
            df = pd.DataFrame()

    # Fallback to daily via DataManager
    if df.empty:
        print("Fetching daily data via DataManager...", flush=True)
        try:
            df = data_manager.get_historical_data("BTC")
            high_res = False
            # Check if valid
            if df.empty or 'Price' not in df.columns:
                 print("DataManager returned empty or invalid data.", flush=True)
                 return
        except Exception as e:
             print(f"DataManager fail: {e}", flush=True)
             return

    if df.empty:
        print("No data available.", flush=True)
        return

    print(f"Dataset Size: {len(df)} rows. Range: {df['Timestamp'].min()} to {df['Timestamp'].max()}", flush=True)
    
    samples = 50
    errors_30m = []
    errors_1d = []
    
    print(f"Running {samples} simulations...", flush=True)
    
    # Validation logic
    valid_indices = range(365, len(df) - 1500) # Ensure future room
    if len(valid_indices) < 10:
         valid_indices = range(365, len(df) - 10)
         if len(valid_indices) <= 0:
              print("Not enough history for simulations.", flush=True)
              return

    import random
    indices = random.sample(list(valid_indices), min(samples, len(valid_indices)))
    
    for i, idx in enumerate(indices):
        try:
            current_row = df.iloc[idx]
            current_time = current_row['Timestamp']
            
            # Slice history
            history_slice = df.iloc[max(0, idx-365):idx].copy()
            
            # Fake session
            if high_res:
                session_slice = df.iloc[max(0, idx-10):idx].copy()
            else:
                 # Generate fake session with some noise to test stability
                 base_price = current_row['Price']
                 noise = np.random.normal(0, base_price * 0.0001, 5) # 0.01% noise
                 
                 timestamps = [current_time - timedelta(minutes=5-i) for i in range(5)]
                 prices = [base_price + n for n in noise]
                 # Ensure last point matches current
                 prices[-1] = base_price
                 
                 session_slice = pd.DataFrame({
                    'Timestamp': timestamps,
                    'Price': prices
                 })
            
            # Predict 30m
            pred_30m, _ = predictor.analyze_and_predict(history_slice, session_slice, 30)
            
            # Predict 1d
            pred_1d, _ = predictor.analyze_and_predict(history_slice, session_slice, 1440)
            
            # Actuals
            if high_res:
                # 30m later
                future_time_30m = current_time + timedelta(minutes=30)
                # Find closest match
                future_idx_30m = df['Timestamp'].searchsorted(future_time_30m)
                if future_idx_30m < len(df):
                    actual_30m = df.iloc[future_idx_30m]['Price']
                    errors_30m.append(abs(pred_30m - actual_30m))
                
                # 1d later
                future_time_1d = current_time + timedelta(days=1)
                future_idx_1d = df['Timestamp'].searchsorted(future_time_1d)
                if future_idx_1d < len(df):
                     actual_1d = df.iloc[future_idx_1d]['Price']
                     errors_1d.append(abs(pred_1d - actual_1d))
            else:
                # Day data
                if idx + 1 < len(df):
                    actual_1d = df.iloc[idx+1]['Price']
                    errors_1d.append(abs(pred_1d - actual_1d))
            
            if i % 10 == 0: print(f"Sim {i}/{samples}...", flush=True)
            
        except Exception as e:
            print(f"Error in sim {i}: {e}", flush=True)

    print("-" * 30, flush=True)
    if errors_30m:
        mae = np.mean(errors_30m)
        print(f"30-Minute MAE: ${mae:.2f}", flush=True)
    
    if errors_1d:
        mae = np.mean(errors_1d)
        print(f"1-Day MAE: ${mae:.2f}", flush=True)
        avg_price = df['Price'].mean()
        print(f"1-Day Error %: {(mae/avg_price)*100:.2f}%", flush=True)
    else:
        print("No valid predictions made.", flush=True)

if __name__ == "__main__":
    run_backtest()
