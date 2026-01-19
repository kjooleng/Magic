import os
import sys
import time
import math
import requests
import argparse
import threading
import traceback
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import smtplib
from email.utils import formatdate
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ====================================================
# 1. Configuration and argument parser
# ====================================================

pw = "your gmail app password"

parser = argparse.ArgumentParser(description="Magic Formula Screener with Smart Email, Auto Resume, and Logging")
parser.add_argument("--sender", help="Sender email address")
parser.add_argument("--password", help="App password or SMTP auth token")
parser.add_argument("--recipient", help="Recipient email address")
parser.add_argument("--smtp_host", help="SMTP server host (default: smtp.gmail.com)", default="smtp.gmail.com")
parser.add_argument("--smtp_port", help="SMTP port (default: 587)", type=int, default=587)
parser.add_argument("--fail_threshold", help="Max fail percentage before skipping attachments (default 20%)", type=float, default=60.0)
parser.add_argument("--partial_interval", help="Save partial progress every N tickers (default 50)", type=int, default=50)
args = parser.parse_args()

SENDER_EMAIL = args.sender or "sender email"
APP_PASSWORD = args.password or pw
#APP_PASSWORD = args.password or "your gmail app password"
RECIPIENT_EMAIL = args.recipient or "receiver email"
SMTP_HOST = args.smtp_host
SMTP_PORT = args.smtp_port
FAIL_THRESHOLD = args.fail_threshold
SAVE_INTERVAL = args.partial_interval

today = time.strftime("%Y-%m-%d")
#OUTPUT_DIR = "output"
#ERROR_LOG = os.path.join(OUTPUT_DIR, "error_log.txt")
ERROR_LOG = "error_log.txt"
#os.makedirs(OUTPUT_DIR, exist_ok=True)

# ====================================================
# 2. Logging
# ====================================================

def log_error(message):
    with open(ERROR_LOG, "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

# ====================================================
# 3. Helper functions
# ====================================================

def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}
    response = requests.get(url, headers=headers)
    tables = pd.read_html(response.text)
    df = tables[0]
    return df["Symbol"].tolist()

def get_nasdaq100_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}
    response = requests.get(url, headers=headers)
    tables = pd.read_html(response.text)
    df = tables[4]  # 5th table is current constituents
    return df["Ticker"].tolist()

def get_dow30_tickers():
    url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}    
    response = requests.get(url, headers=headers)
    tables = pd.read_html(response.text)
    df = tables[2]  # 3rd table is current components
    return df["Symbol"].tolist()   

def filter_industries(df):
    """Exclude Financials and Utilities."""
    df = df[~df["Sector"].isin(["Financial Services", "Financial", "Finance", "Bank", "Insurance", "Utility", "Utilities"])]
    #df = df[~df["Sector"].isin(["Financial", "Finance", "Bank", "Insurance", "Utility"])]
    return df

# ====================================================
# 4. Yahoo Finance Data Fetch
# ====================================================

def fetch_data(ticker, max_retries=3):
    for attempt in range(max_retries):
        try:
#====================================================================================================================            
            t = yf.Ticker(ticker)
            info = t.info
            ey = info.get("earningsYield") or (info.get("trailingEps") / info.get("previousClose") if info.get("previousClose") else None)
            roc = info.get("returnOnCapital") or info.get("returnOnAssets") or info.get("returnOnEquity")
            market_cap = info.get("marketCap", None)
            sector = info.get("sector", "N/A")
            if ey and roc:
                return {"Ticker": ticker, "Market Cap": market_cap, "EY": ey, "ROC": roc, "Sector": sector}
#====================================================================================================================     
#            t = yf.Ticker(ticker)
#            fin = t.financials
#            bs = t.balance_sheet
#            info = t.info
#
#            sector = info.get("sector", "N/A")
#            ##if any(x in sector for x in ["Financial", "Finance", "Bank", "Insurance", "Utility"]):
#                ##return None
#
#            if "Operating Income" not in fin.index:
#                raise ValueError("Missing Operating Income")
#            EBIT = fin.loc["Operating Income"].iloc[0]
#            market_cap = info.get("marketCap")
#            if not market_cap:
#                raise ValueError("Missing Market Cap")
#
#            total_debt = bs.loc["Total Debt"].iloc[0] if "Total Debt" in bs.index else 0
#            cash = bs.loc["Cash"].iloc[0] if "Cash" in bs.index else 0
#            EV = market_cap + total_debt - cash
#            if EV <= 0:
#                raise ValueError("Invalid EV")
#
#            current_assets = bs.loc["Total Current Assets"].iloc[0] if "Total Current Assets" in bs.index else 0
#            current_liabilities = bs.loc["Total Current Liabilities"].iloc[0] if "Total Current Liabilities" in bs.index else 0
#            NWC = current_assets - current_liabilities
#            total_assets = bs.loc["Total Assets"].iloc[0] if "Total Assets" in bs.index else 0
#            intangibles = bs.loc["Intangible Assets"].iloc[0] if "Intangible Assets" in bs.index else 0
#            net_fixed = total_assets - current_assets - intangibles
#            capital = NWC + net_fixed
#            if capital <= 0:
#                raise ValueError("Invalid Capital")
#
#            EY = EBIT / EV
#            ROC = EBIT / capital
#            
#            if EY and ROC:
#                return {"Ticker": ticker, "Market Cap": market_cap, "Sector": sector, "EBIT": EBIT, "EV": EV, "EY": EY, "ROC": ROC}
#=================================================================================================================           
        except Exception as e:
            if attempt == max_retries - 1:
                log_error(f"{ticker}: {e}")
        time.sleep(1)
    return None

# ====================================================
# 5. Load or resume progress
# ====================================================

#partial_file = os.path.join(OUTPUT_DIR, "partial_progress.csv")
partial_file = "partial_progress.csv"
completed = []
if os.path.exists(partial_file):
    try:
        df_partial = pd.read_csv(partial_file)
        completed = df_partial["Ticker"].tolist()
        print(f"🔄 Resuming from {len(completed)} completed tickers.")
    except Exception as e:
        log_error(f"Failed to load partial file: {e}")
        df_partial = pd.DataFrame(columns=["Ticker", "Market Cap", "EY", "ROC", "Sector"])
        #df_partial = pd.DataFrame(columns=["Ticker", "Market Cap", "Sector", "EBIT", "EV", "EY", "ROC"])
else:
    df_partial = pd.DataFrame(columns=["Ticker", "Market Cap", "EY", "ROC", "Sector"])
    #df_partial = pd.DataFrame(columns=["Ticker", "Market Cap", "Sector", "EBIT", "EV", "EY", "ROC"])

# ====================================================
# 6. Main Processing Loop (multi-threaded)
# ====================================================

nyse_list = pd.read_csv("NYSE_20260109.csv")
nyse_stocks = list(nyse_list["<ticker>"])
nasdaq_list = pd.read_csv("NASDAQ_20260109.csv")
nasdaq_stocks = list(nasdaq_list["<ticker>"])
amex_list = pd.read_csv("AMEX_20260109.csv")
amex_stocks = list(amex_list["<ticker>"])

tickers = list(set(nyse_stocks + nasdaq_stocks + amex_stocks))

#tickers = stocks
#tickers = get_sp500_tickers()

pending = [t for t in tickers if t not in completed]
results = []
fail_count = 0
cpu_threads = min(32, (os.cpu_count() or 4) * 0.5)

print(f"🧮 Processing {len(pending)} tickers using {cpu_threads} threads...")

with ThreadPoolExecutor(max_workers=2) as executor:
    futures = {executor.submit(fetch_data, t): t for t in pending}
    for i, future in enumerate(tqdm(as_completed(futures), total=len(futures))):
        tkr = futures[future]
        res = future.result()
        if res:
            results.append(res)
        else:
            fail_count += 1
        # Autosave partial progress
        if (i + 1) % SAVE_INTERVAL == 0:
            pd.DataFrame(results + df_partial.to_dict("records")).to_csv(partial_file, index=False)

# ====================================================
# 7. Combine and rank
# ====================================================

df = pd.DataFrame(results)
if not df.empty and not df_partial.empty:
    df = pd.concat([df, df_partial]).drop_duplicates("Ticker", keep="last")

df = filter_industries(df)

df["EY_rank"] = df["EY"].rank(ascending=False)
df["ROC_rank"] = df["ROC"].rank(ascending=False)
df["Score"] = df["EY_rank"] + df["ROC_rank"]
df = df.sort_values("Score")

#csv_file = os.path.join(OUTPUT_DIR, f"US_AMEX_NYSE_NASDAQ_magic_formula_{today}.csv")
csv_file = f"US_AMEX_NYSE_NASDAQ_magic_formula_{today}.csv"
#excel_file = os.path.join(OUTPUT_DIR, f"US_AMEX_NYSE_NASDAQ_magic_formula_{today}.xlsx")
excel_file = f"US_AMEX_NYSE_NASDAQ_magic_formula_{today}.xlsx"
df.to_csv(csv_file, index=False)
df.to_excel(excel_file, index=False)

# ====================================================
# 8. Cleanup old partials
# ====================================================

if os.path.exists(partial_file):
    os.remove(partial_file)

# ====================================================
# 9. Email with multi-part support
# ====================================================

total_tickers = len(tickers)
fail_percent = (fail_count / total_tickers * 100) if total_tickers else 0
print(f"\n✅ Completed with failure rate: {fail_percent:.2f}%")

def send_email(subject, plain_body, html_body=None, attachments=None):
    msg = MIMEMultipart("mixed")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain_body, "plain"))
    if html_body:
        alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    if attachments:
        for file_path in attachments:
            try:
                with open(file_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(file_path)}"')
                    msg.attach(part)
            except Exception as e:
                log_error(f"Attachment failed: {file_path} — {e}")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        print(f"📧 Email sent successfully to {RECIPIENT_EMAIL}")
    except Exception as e:
        log_error(f"Email send failed: {e}")
        print("⚠️ Email sending failed. See error_log.txt.")

# ====================================================
# 10. Compose message
# ====================================================

if fail_percent <= FAIL_THRESHOLD:
    subject = f"AMEX + NYSE + NASDAQ Magic Formula Results ({today}) - Success"
    plain_body = f"Attached are the ranking files and error log. Failure rate: {fail_percent:.2f}%."
    html_body = f"""
    <html><body>
    <h2>AMEX + NYSE + NASDAQ Magic Formula Results ({today})</h2>
    <p>Attached are the ranking files and error log.</p>
    <p><b>Failure rate:</b> {fail_percent:.2f}%</p>
    </body></html>
    """
    send_email(subject, plain_body, html_body, [csv_file, excel_file, ERROR_LOG])

else:
    subject = f"AMEX + NYSE + NASDAQ Magic Formula Run ({today}) - High Failure Rate Alert (with partial summary)"
    if not df.empty:
        top5 = df.head(5)
        summary_lines = ["\nTop 5 (partial results):"]
        html_rows = ""
        for _, row in top5.iterrows():
            summary_lines.append(f"{row['Ticker']:<8}  Score={row['Score']:.1f}  EY={row['EY']:.4f}  ROC={row['ROC']:.4f}")
            html_rows += f"<tr><td>{row['Ticker']}</td><td>{row['Score']:.1f}</td><td>{row['EY']:.4f}</td><td>{row['ROC']:.4f}</td></tr>"
        summary_text = "\n".join(summary_lines)
        html_table = f"<table border='1' cellpadding='4'><tr><th>Ticker</th><th>Score</th><th>EY</th><th>ROC</th></tr>{html_rows}</table>"
    else:
        summary_text = "\nNo valid tickers processed."
        html_table = "<p>No valid tickers processed.</p>"

    plain_body = (
        f"The run completed with a high failure rate ({fail_percent:.2f}%).\n"
        f"Detailed files were not sent.\nCheck error_log.txt for details.\n"
        f"{summary_text}"
    )
    html_body = f"""
    <html><body>
    <h2>⚠️ High Failure Rate Alert ({fail_percent:.2f}%)</h2>
    <p>Detailed files were not sent. See <b>error_log.txt</b> for details.</p>
    {html_table}
    </body></html>
    """

    send_email(subject, plain_body, html_body)
