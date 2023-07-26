import os
import sys
from datetime import datetime, timedelta
import asyncio
import aiohttp
import logging
import pandas as pd

try:
    import yfinance as yf

    yfinance_available = True
except:
    yfinance_available = False

# XXX temporary hack to import from src
try:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "../indralib/src"
    )
except:
    path = "~/gith/domschl/indrajala/python_indrajala/indralib/src"
    # expand ~
    path = os.path.expanduser(path)
print(path)
sys.path.append(path)
sys.path.append("/var/lib/indrajala/tasks/indralib/src")

from indra_event import IndraEvent
from indra_client import IndraClient


class FinanceData:
    def __init__(self, cache_directory, log_handler):
        self.cache_directory = cache_directory
        self.log = logging.getLogger("finance_data")
        self.log.addHandler(log_handler)
        # Create cache directory if it does not exist:
        if not os.path.exists(self.cache_directory):
            os.makedirs(self.cache_directory)
            self.log.warning(
                "Created cache directory {self.cache_directory} for finance_data"
            )
        if not os.path.exists(self.cache_directory):
            self.log.error(
                f"Cache directory {self.cache_directory} for finance_data is not a directory"
            )
            self.cache_directory = None
        else:
            if yfinance_available is True:
                self.cache_directory_yfinance = os.path.join(
                    self.cache_directory, "yfinance"
                )
                if not os.path.exists(self.cache_directory_yfinance):
                    os.makedirs(self.cache_directory_yfinance)
                    self.log.warning(
                        f"Created cache directory {self.cache_directory_yfinance} for finance_data from yfinance module"
                    )

    async def get_price_history(self, ticker):
        if not yfinance_available:
            self.log.error(
                f"yfinance not available, cannot fetch stock data for {ticker}"
            )
            return None
        stock = yf.Ticker(ticker, cache_directory=self.cache_directory_yfinance)
        # Calculate the date range for the last ten years
        end_date = (
            yf.Ticker(ticker, cache_directory=self.cache_directory_yfinance)
            .history(period="1d")
            .index[-1]
        )
        start_date = end_date - pd.DateOffset(years=10)
        # Fetch historical price data with resolution 1d for the last ten years
        history = stock.history(period="1d", start=start_date, end=end_date)
        return history

    async def get_stock_price(self, ticker):
        if not yfinance_available:
            async with aiohttp.ClientSession() as session:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                async with session.get(url) as response:
                    data = await response.json()
                    # Extract the stock price from the API response
                    stock_price = data["chart"]["result"][0]["meta"][
                        "regularMarketPrice"
                    ]
                    return stock_price
        else:
            stock = yf.Ticker(ticker, cache_directory=self.cache_directory_yfinance)
            return stock.history(period="1d")["Close"].iloc[-1]


if __name__ == "__main__":
    module_name = "finance_data"
    log_handler = logging.StreamHandler(sys.stderr)
    log_formatter = logging.Formatter(
        "[%(asctime)s]  %(levelname)s [%(module)s::FinanceData] %(message)s"
    )
    log_handler.setFormatter(log_formatter)
    log = logging.getLogger(module_name)
    log.addHandler(log_handler)

    if len(sys.argv) < 4:
        log.error(
            "Missing parameter for finance_data.py: hour cache-dir profile [yahoo-ticker-symbol]+",
        )
        sys.exit(1)

    hour = int(sys.argv[1])
    cache_directory = sys.argv[2]
    profile = sys.argv[3]
    if profile.lower() in ["default", "none", ""]:
        profile = None
    tickers = []
    for ticker in sys.argv[4:]:
        tickers.append(ticker)

    fd = FinanceData(cache_directory=cache_directory, log_handler=log_handler)

    async def main():
        cl = IndraClient(
            profile=profile,
            verbose=True,
            log_handler=log_handler,
            module_name=module_name,
        )
        ws = await cl.init_connection(verbose=True)
        if ws is None:
            log.error("Could not create Indrajala client for finance_data")
            return
        else:
            await cl.info(
                f"Indrajala client for finance_data created, running each day at {hour} o'clock (UTC), monitoring {len(tickers)} tickers: {tickers}"
            )

        target_time_utc = datetime.utcnow().replace(
            hour=hour, minute=0, second=0, microsecond=0
        )

        while True:
            now_utc = datetime.utcnow()
            if now_utc >= target_time_utc:
                try:
                    await cl.info("Polling finance_data")
                    # stock_price = await get_stock_price(ticker)
                    # print(
                    #     f"Current Price for Deutsche Bank (WKN: 514000): €{stock_price:.2f}"
                    # )

                except Exception as e:
                    print(f"Error fetching stock prices: {e}")

                # Calculate the time until the next day's target time
                tomorrow_utc = now_utc + timedelta(days=1)
                target_time_utc = tomorrow_utc.replace(
                    hour=hour, minute=0, second=0, microsecond=0
                )

            # Sleep for a short duration before checking again
            await asyncio.sleep(60)  # Check every minute

    asyncio.run(main())
