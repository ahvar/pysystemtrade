import matplotlib
import pandas as pd
from pathlib import Path
from systems.accounts.account_forecast import pandl_for_instrument_forecast, get_pandl_calculator, _get_average_notional_position, _get_normalised_forecast, _get_notional_position_for_forecast
from matplotlib.pyplot import show
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysquant.estimators.vol import robust_vol_calc, robust_daily_vol_given_price
from systems.accounts.pandl_calculators.pandl_generic_costs import (
    GROSS_CURVE,
    NET_CURVE,
    COSTS_CURVE,
    pandlCalculationWithGenericCosts,
)
from systems.accounts.pandl_calculators.pandl_calculation import calculate_pandl
from syscore.dateutils import Frequency
matplotlib.use("TkAgg")
from pprint import PrettyPrinter
pp = PrettyPrinter(indent=4)
"""

Work up a minimum example of a trend following system

"""

# Get some data

""""
Let's get some data

We can get data from various places; however for now we're going to use
prepackaged 'legacy' data stored in csv files
"""
data = csvFuturesSimData()

#pp.pprint(data)
"""
We get stuff out of data with methods
"""
#print(data.get_instrument_list())
#print(data.get_raw_price("EDOLLAR").tail(5))
"""
data can also behave in a dict like manner (though it's not a dict)
"""

#pp.pprint(data["VIX"])
#pp.pprint(data.keys())

"""
Not all the instruments are easily identifiable
"""

#pp.pprint(data.get_instrument_object_with_meta_data("MUMMY"))


"""

... however this will only access prices
(note these prices have already been backadjusted for rolls)

We have extra futures data here

"""

#print(data.get_instrument_raw_carry_data("EDOLLAR").tail(6))
"""
Technical note: csvFuturesSimData inherits from FuturesData which itself inherits
from simData
The chain is 'data specific' <- 'asset class specific' <- 'generic'

Let's create a simple trading rule

No capping or scaling
"""

from sysquant.estimators.vol import robust_vol_calc


def calc_ewmac_forecast(price, Lfast, Lslow=None):
    """
    Calculate the ewmac trading rule forecast, given a price and EWMA speeds
    Lfast, Lslow and vol_lookback

    """
    # price: This is the stitched price series
    # We can't use the price of the contract we're trading, or the volatility
    # will be jumpy
    # And we'll miss out on the rolldown. See
    # https://qoppac.blogspot.com/2015/05/systems-building-futures-rolling.html
    price = price.resample("1B").last()

    if Lslow is None:
        Lslow = 4 * Lfast

    # We don't need to calculate the decay parameter, just use the span
    # directly
    fast_ewma = price.ewm(span=Lfast).mean()
    fast_ewma.to_csv(Path(__file__).resolve().parent / "fast_ewma.csv")
    slow_ewma = price.ewm(span=Lslow).mean()
    slow_ewma.to_csv(Path(__file__).resolve().parent / "slow_ewma.csv")
    raw_ewmac = fast_ewma - slow_ewma
    raw_ewmac.to_csv(Path(__file__).resolve().parent / "raw_ewmac.csv")

    vol = robust_vol_calc(price.diff())
    return raw_ewmac / vol


"""
Try it out

(this isn't properly scaled at this stage of course)
"""
instrument_code = "SP500"
price = data.daily_prices(instrument_code)
ewmac = calc_ewmac_forecast(price, 16, 64)
ewmac2 = calc_ewmac_forecast(price, 16, 64)
ewmac.name = "forecast"

daily_returns_volatility = robust_daily_vol_given_price(price)

normalised_forecast = _get_normalised_forecast(
    ewmac, target_abs_forecast=10.0
)
average_notional_position = _get_average_notional_position(
    daily_returns_volatility,
    risk_target=0.16,
    value_per_point=1.0,
    capital=100000,
)
abs_path = Path(__file__).resolve().parent
average_notional_position.to_csv(abs_path / "average_notional_position.csv")
notional_position = _get_notional_position_for_forecast(
    normalised_forecast, average_notional_position=average_notional_position
)
pos_series = notional_position.groupby(notional_position.index).last()
pos_series.to_csv(abs_path / "notional_position_grouped_by_index.csv")
both_series = pd.concat([pos_series, price], axis=1)
both_series.columns = ["positions", "prices"]
both_series.to_csv(abs_path / "notiona_position_and_price.csv")
both_series = both_series.ffill()
price_returns = both_series.prices.diff()
price_returns.to_csv(abs_path / "price_returns.csv")
returns = both_series.positions.shift(1) * price_returns
returns[returns.isna()] = 0.0
returns.to_csv(abs_path / "pandl_in_points.csv")

#notional_position.plot()
#show()


#print(ewmac.tail(5))

#ewmac.plot()
#show()
"""
Did we make money?
"""
#pandl_calculator = get_pandl_calculator(forecast=ewmac, price=price)
#as_pd_series = pandl_calculator.as_pd_series_for_frequency(frequency=Frequency.BDay, percent=False, curve_type=NET_CURVE)
#pp.pprint(as_pd_series)
#account = pandl_for_instrument_forecast(forecast=ewmac, price=price)

#account.curve()

#account.curve().plot()
#show()

#print(account._as_ts)
