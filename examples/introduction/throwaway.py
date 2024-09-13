import pandas as pd
import numpy as np

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
fast_ewma = price_series.ewm(span=16).mean()
slow_ewma = price_series.ewm(span=64).mean()
raw_ewma = fast_ewma - slow_ewma



normalized_forecast_values = [None, None, None, 3.4, 2.3, -0.4, None, 0.56]
average_notional_position_values = [2345, 3521, 3056, 3478, 3332, 3498, 3674, 4021]
normalized_forecast = pd.Series(normalized_forecast_values, index=date_range)
normalized_forecast.name = "forecast"
average_notional_position = pd.Series(average_notional_position_values, index=date_range)
average_notional_position.columns = ["price"]
print(f"Normalized Forecast: \n{normalized_forecast}")
print(f"Avg Notional Position: \n{average_notional_position}")

aligned_average = average_notional_position.reindex(normalized_forecast.index, method="ffill")
print(f"Aligned Average: \n{aligned_average}")