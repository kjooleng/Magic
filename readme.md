## Script Analysis

This Python script is a **Magic Formula stock screener** for US markets (AMEX, NYSE, NASDAQ) that implements Joel Greenblatt's Magic Formula investing strategy. It fetches stock data using multi-threading, calculates rankings based on Earnings Yield (EY) and Return on Capital (ROC), and emails the results with CSV/Excel attachments.

### Key Features

- **Multi-threaded data fetching** using ThreadPoolExecutor for parallel processing
- **Auto-resume capability** with partial progress saving every N tickers
- **Smart email alerts** with conditional attachment sending based on failure rate
- **Error logging** to track failed ticker lookups
- **Industry filtering** to exclude Financial Services and Utilities sectors
- **Three exchange coverage** reading from pre-downloaded CSV files


### Required Dependencies

```bash
pip install pandas numpy yfinance requests tqdm openpyxl
```


### Input Requirements

The script expects three CSV files in the same directory:

- `NYSE20260109.csv` - NYSE ticker list with a `ticker` column
- `NASDAQ20260109.csv` - NASDAQ ticker list with a `ticker` column
- `AMEX20260109.csv` - AMEX ticker list with a `ticker` column


## Running the Script

### Basic Command

```bash
python MagicUS-Multi-Thread-Email-Override-Attach.py \
  --sender your_email@gmail.com \
  --password your_app_password \
  --recipient recipient@email.com
```


### Command-Line Arguments

| Argument | Required | Default | Description |
| :-- | :-- | :-- | :-- |
| `--sender` | Yes | None | Sender email address  |
| `--password` | Yes | None | Gmail app password or SMTP token  |
| `--recipient` | Yes | None | Recipient email address  |
| `--smtphost` | No | smtp.gmail.com | SMTP server hostname  |
| `--smtpport` | No | 587 | SMTP server port  |
| `--failthreshold` | No | 60.0 | Max failure % before skipping attachments  |
| `--partialinterval` | No | 50 | Save partial progress every N tickers  |

### Advanced Example

```bash
python MagicUS-Multi-Thread-Email-Override-Attach.py \
  --sender analytics@company.com \
  --password "app_password_here" \
  --recipient investor@company.com \
  --smtphost smtp.office365.com \
  --smtpport 587 \
  --failthreshold 40.0 \
  --partialinterval 100
```


## How It Works

### Data Processing Flow

1. **Ticker Collection**: Reads tickers from three CSV files and deduplicates them
2. **Resume Check**: Loads `partialprogress.csv` if it exists to skip completed tickers
3. **Multi-threaded Fetching**: Uses ThreadPoolExecutor with thread count based on CPU cores (min 32 threads)
4. **Data Extraction**: For each ticker, fetches EBIT, Enterprise Value, Market Cap, and Sector from yfinance
5. **Magic Formula Calculation**:
    - EY (Earnings Yield) = EBIT / Enterprise Value
    - ROC (Return on Capital) = EBIT / (Net Working Capital + Net Fixed Assets)
    - Score = EY Rank + ROC Rank (lower is better)
6. **Industry Filtering**: Excludes Financial Services and Utilities sectors
7. **Output Generation**: Creates ranked CSV and Excel files
8. **Email Delivery**: Sends results with conditional attachment logic

### Email Logic

- **Success case** (failure rate ≤ threshold): Sends full results with CSV, Excel, and error log attachments
- **High failure case** (failure rate > threshold): Sends alert with top 5 stocks summary only, no attachments


### Output Files

All files are saved in the `output/` directory:

- `USA_AMEX_NYSE_NASDAQ_magicformula_YYYY-MM-DD.csv` - Full ranked results
- `USA_AMEX_NYSE_NASDAQ_magicformula_YYYY-MM-DD.xlsx` - Excel version
- `partialprogress.csv` - Auto-saved progress (deleted on completion)
- `errorlog.txt` - Failed ticker logs with timestamps


## Gmail App Password Setup

Since this uses Gmail SMTP, you need an **App Password** (not your regular Gmail password):

1. Enable 2-Factor Authentication on your Google account
2. Go to Google Account → Security → 2-Step Verification → App passwords
3. Generate a new app password for "Mail"
4. Use this 16-character password with the `--password` argument

## Error Handling

- **Retry logic**: Each ticker is retried up to 3 times with 1-second delays
- **Graceful degradation**: Failed tickers are logged and counted but don't stop execution
- **Partial saves**: Progress is auto-saved every 50 tickers (configurable) to enable resume
- **Error logging**: All failures are timestamped in `errorlog.txt`


## Performance Notes

- Uses **dynamic thread count** based on CPU cores (minimum 32 threads for I/O-bound operations)
- Progress bar shows real-time processing status via tqdm
- Average processing time depends on total ticker count and yfinance API responsiveness

<div align="center">⁂</div>



