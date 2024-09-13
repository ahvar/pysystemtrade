import pandas as pd
import numpy as np
from pathlib import Path

date_range = pd.date_range(start="2017-01-10", periods=200, freq='D').strftime("%d-%m-%Y")
def generate_random_walk_prices(start_price, num_days, volatility=1):
    prices = [start_price]
    for _ in range(num_days - 1):
        change = np.random.normal(0, volatility)
        prices.append(prices[-1] + change)
    return prices


start_price = 545.45
num_days = 200
prices = generate_random_walk_prices(start_price, num_days)
price_series = pd.Series(prices, index=date_range)
price_series.name = "price"
fast_ewma = price_series.ewm(span=16).mean()
fast_ewma.to_csv(Path(__file__).resolve().parent / "fast_ewma.csv")
slow_ewma = price_series.ewm(span=64).mean()
slow_ewma.to_csv(Path(__file__).resolve().parent / "slow_ewma.csv")
raw_ewmac = fast_ewma - slow_ewma
raw_ewmac.to_csv(Path(__file__).resolve().parent / "raw_ewmac.csv")
