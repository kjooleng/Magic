# -----------------------------------------------------------------------------
# THE NUCLEAR OPTION: Bypass the entire yfinance caching system
# This prevents the import of 'peewee' and 'sqlite3' entirely.
# -----------------------------------------------------------------------------
import sys
from unittest.mock import MagicMock

# We create a fake 'yfinance.cache' module.
# When yfinance tries to 'import .cache', it will find this mock 
# and will NOT attempt to load the real cache.py (which is what crashes).
mock_cache = MagicMock()
sys.modules["yfinance.cache"] = mock_cache

# Also mock sqlite3 just in case any other part of the library checks for it
sqlite3_mock = MagicMock()
sqlite3_mock.version = (3, 39, 0)
sys.modules["sqlite3"] = sqlite3_mock

print("System Mock: yfinance.cache and sqlite3 fully bypassed.")
# -----------------------------------------------------------------------------

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm 
import os
import time
import random
import io

# Force yfinance to ignore caching entirely
os.environ['YFINANCE_CACHE'] = 'False'

# 1. Setup Session to bypass Cloud Blocking
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        response = session.get(url)
        tables = pd.read_html(io.StringIO(response.text))
        return tables[0]["Symbol"].tolist()
    except Exception as e:
        print(f"Error getting tickers: {e}")
        return []

def get_nasdaq100_tickers():
    #url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    url = "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies"
    try:
        response = session.get(url)
        tables = pd.read_html(io.StringIO(response.text))
        return tables[0]["Ticker"].tolist()
    except Exception as e:
        print(f"Error getting tickers: {e}")
        return []

def get_dow30_tickers():
    #url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
    url = "https://en.wikipedia.org/wiki/List_of_Dow_Jones_Industrial_Average_companies"
    try:
        response = session.get(url)
        tables = pd.read_html(io.StringIO(response.text))
        return tables[0]["Symbol"].tolist()
    except Exception as e:
        print(f"Error getting tickers: {e}")
        return []

#tickers = get_dow30_tickers()
tickers = tickers = list(set(get_dow30_tickers() + get_nasdaq100_tickers() + get_sp500_tickers()))

def process_ticker(ticker, max_retries=3, retry_delay=2):
    for attempt in range(max_retries):
        try:
            # Use the session to avoid IP blocks
            stock = yf.Ticker(ticker, session=session)
            
            # Fetch data
            fin = stock.financials
            bs = stock.balance_sheet
            info = stock.info

            if not info or fin.empty or bs.empty:
                return None

            # Exclude Financials & Utilities
            sector = info.get("sector", "")
            if any(x in sector for x in ["Financial Services", "Financial", "Finance", "Bank", "Insurance", "Utility", "Utilities"]):
                return None

            # EBIT
            if "Operating Income" in fin.index:
                EBIT = fin.loc["Operating Income"].iloc[0]
            else:
                return None 

            # Enterprise Value
            market_cap = info.get("marketCap", None)
            if market_cap is None:
                return None

            total_debt = bs.loc["Total Debt"].iloc[0] if "Total Debt" in bs.index else 0
            cash = bs.loc["Cash"].iloc[0] if "Cash" in bs.index else 0
            EV = market_cap + total_debt - cash
            if EV <= 0:
                return None

            # Net Working Capital
            current_assets = bs.loc["Total Current Assets"].iloc[0] if "Total Current Assets" in bs.index else 0
            current_liabilities = bs.loc["Total Current Liabilities"].iloc[0] if "Total Current Liabilities" in bs.index else 0
            NWC = current_assets - current_liabilities

            # Net Fixed Assets
            total_assets = bs.loc["Total Assets"].iloc[0] if "Total Assets" in bs.index else 0
            intangibles = bs.loc["Intangible Assets"].iloc[0] if "Intangible Assets" in bs.index else 0
            net_fixed = total_assets - current_assets - intangibles

            capital = NWC + net_fixed
            if capital <= 0:
                return None

            return {
                "Ticker": ticker,
                "Market Cap": market_cap,
                "Sector": sector,
                "EBIT": EBIT,
                "EV": EV,
                "EY": EBIT / EV,
                "ROC": EBIT / capital
            }
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay + random.uniform(0, 1))
            else:
                print(f"Error fetching {ticker}: {e}")
                return None

# 3. Execution
data = []
failed_tickers = []
print(f"Fetching data for {len(tickers)} tickers...\n")

with ThreadPoolExecutor(max_workers=2) as executor:
    futures = {executor.submit(process_ticker, t): t for t in tickers}
    for future in tqdm(as_completed(futures), total=len(futures), desc="Processing", unit="stock"):
        ticker = futures[future]
        result = future.result()
        if result:
            data.append(result)
        else:
            failed_tickers.append(ticker)

# Retry pass
if failed_tickers:
    print(f"\nRetrying {len(failed_tickers)} failed tickers...\n")
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(process_ticker, t): t for t in failed_tickers}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Retrying", unit="stock"):
            result = future.result()
            if result:
                data.append(result)

# 4. Rank and output
if not data:
    print("\nCRITICAL ERROR: No data collected. Yahoo Finance may be blocking the Cloud IP.")
    df = pd.DataFrame(columns=["Ticker", "Score"])
else:
    df = pd.DataFrame(data)
    df["EY_rank"] = df["EY"].rank(ascending=False)
    df["ROC_rank"] = df["ROC"].rank(ascending=False)
    df["Score"] = df["EY_rank"] + df["ROC_rank"]
    df = df.sort_values("Score").reset_index(drop=True)

    print("\n=== Top 20 Magic Formula Stocks ===")
    print(df.head(20)[["Ticker", "Market Cap", "Sector", "EY", "ROC", "Score"]])

    today = datetime.today().strftime("%Y-%m-%d")
    csv_file = f"Dow30_Nasdaq100_SNP500_magic_formula_ranking_{today}.csv"
    excel_file = f"Dow30_Nasdaq100_SNP500_magic_formula_ranking_{today}.xlsx"
    df.to_csv(csv_file, index=False)
    df.to_excel(excel_file, index=False)
    print(f"\nSaved as: {csv_file}, {excel_file}")
