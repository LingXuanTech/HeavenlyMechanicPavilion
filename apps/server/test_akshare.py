import akshare as ak
import pandas as pd

def test_akshare():
    try:
        # Fetch spot data for A-shares
        stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
        print("AkShare Spot Data (First 5 rows):")
        print(stock_zh_a_spot_em_df.head())
        
        # Fetch history for a specific stock (e.g., 600519 - Moutai)
        stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol="600519", period="daily", start_date="20240101", end_date="20240110", adjust="qfq")
        print("AkShare History Data for 600519:")
        print(stock_zh_a_hist_df.head())
        return True
    except Exception as e:
        print(f"AkShare Test Failed: {e}")
        return False

if __name__ == "__main__":
    test_akshare()
