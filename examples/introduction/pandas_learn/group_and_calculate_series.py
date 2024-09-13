import pandas as pd
import numpy as np

date_range = pd.date_range(start="2017-01-10", periods=100, freq='D').strftime("%d-%m-%Y")
def generate_random_walk_prices(start_price, num_days, volatility=1):
    prices = [start_price]
    for _ in range(num_days - 1):
        change = np.random.normal(0, volatility)
        prices.append(prices[-1] + change)
    return prices

prices = generate_random_walk_prices