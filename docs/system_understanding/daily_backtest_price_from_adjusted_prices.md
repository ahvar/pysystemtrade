## Daily Backtest Price From Last Observed Adjusted Price

This note explains how pysystemtrade turns futures contract-aware data into the daily price series consumed by the backtest.

See also [futures_price_file_representations.md](futures_price_file_representations.md) for the distinction between multiple prices and adjusted prices.

## Short answer

For a futures backtest using [csvFuturesSimData()](../../sysdata/sim/csv_futures_sim_data.py#L20), the daily backtest price is the last observed value of the adjusted-price series in each business-day bucket.

The concrete resampling rule is [resample_prices_to_business_day_index()](../../syscore/pandas/frequency.py#L169):

```python
return x.resample("1B").last()
```

So the effective path is:

`multiple prices -> adjusted prices -> get_raw_price() -> daily_prices() -> resample("1B").last()`

## Step 1: Multiple prices are the contract-aware source

The richer source file is [../../data/futures/multiple_prices_csv/AEX.csv](../../data/futures/multiple_prices_csv/AEX.csv) or the equivalent file for another instrument.

That file is loaded by [csvFuturesMultiplePricesData](../../sysdata/csv/csv_multiple_prices.py#L16) and represented as a [futuresMultiplePrices](../../sysobjects/multiple_prices.py#L58) object.

It contains timestamped values for:

1. the current priced contract,
2. the forward contract,
3. the carry contract,
4. plus the associated contract IDs.

This file can mix daily and intraday timestamps. It is not required to be exactly one row per session.

## Step 2: Adjusted prices are the continuous instrument series

The adjusted-price file is [../../data/futures/adjusted_prices_csv/AEX.csv](../../data/futures/adjusted_prices_csv/AEX.csv) or its peer for another instrument.

That file is loaded by [csvFuturesAdjustedPricesData](../../sysdata/csv/csv_adjusted_prices.py#L16) and returned as [futuresAdjustedPrices](../../sysobjects/adjusted_prices.py#L11).

Conceptually, that adjusted series is derived from multiple prices by [futuresAdjustedPrices.stitch_multiple_prices()](../../sysobjects/adjusted_prices.py#L28), with the default Panama implementation in [_panama_stitch()](../../sysobjects/adjusted_prices.py#L58).

When the priced contract rolls, [_roll_in_panama()](../../sysobjects/adjusted_prices.py#L90) shifts historical values by the prior row’s roll differential:

`previous_row.FORWARD - previous_row.PRICE`

That is why the adjusted series is continuous across contract rolls and why its level can differ materially from the raw `PRICE` column in the multiple-prices file.

## Step 3: Futures sim data defines adjusted prices as the "raw" price

The naming is a little misleading if you expect “raw” to mean unadjusted contract prices.

In the futures simulation layer, [futuresSimData.get_raw_price_from_start_date()](../../sysdata/sim/futures_sim_data.py#L68) defines the instrument raw price as the back-adjusted futures price.

The lookup path is:

1. [simData.get_raw_price()](../../sysdata/sim/sim_data.py#L161) gets the configured start date and delegates to `get_raw_price_from_start_date(...)`.
2. [futuresSimData.get_raw_price_from_start_date()](../../sysdata/sim/futures_sim_data.py#L68) calls [genericBlobUsingFuturesSimData.get_backadjusted_futures_price()](../../sysdata/sim/futures_sim_data_with_data_blob.py#L63).
3. That calls `self.db_futures_adjusted_prices_data.get_adjusted_prices(instrument_code)`.
4. Under [csvFuturesSimData()](../../sysdata/sim/csv_futures_sim_data.py#L20), that resolves to [csvFuturesAdjustedPricesData](../../sysdata/csv/csv_adjusted_prices.py#L16), which reads `data/futures/adjusted_prices_csv/<INSTRUMENT>.csv`.

So for futures backtests, the “raw price” is already the stitched adjusted series.

## Step 4: `daily_prices()` resamples the adjusted series to business days

[RawData.get_daily_prices()](../../systems/rawdata.py#L49) is the stage method the backtest commonly calls.

That method simply delegates to [simData.daily_prices()](../../sysdata/sim/sim_data.py#L102) through `self.data_stage.daily_prices(instrument_code)`.

The actual daily conversion happens in [simData._get_daily_prices_for_directional_instrument()](../../sysdata/sim/sim_data.py#L114):

1. get the natural-frequency instrument price with `self.get_raw_price(instrument_code)`,
2. pass it to [resample_prices_to_business_day_index()](../../syscore/pandas/frequency.py#L169),
3. return the resampled series.

And [resample_prices_to_business_day_index()](../../syscore/pandas/frequency.py#L169) is just:

```python
return x.resample("1B").last()
```

This means the daily backtest series is not an average, not the first tick of the day, and not a special exchange-settlement selection. It is the last observed adjusted-price sample inside each business-day resample bucket.

## Step 5: Why mixed-frequency adjusted prices still work

Because the final daily conversion is `resample("1B").last()`, the system can tolerate an adjusted series that contains:

1. mostly daily observations in older history,
2. intraday timestamps in other periods,
3. mixed timestamp granularity across the full instrument history.

The daily backtest layer normalizes that mixed-frequency adjusted series into one business-day series by taking the last observed value in each business day.

## Related path: denominator prices

This same “last observation in the business-day bucket” idea also shows up elsewhere in the research pipeline.

For example, [RawData.daily_denominator_price()](../../systems/rawdata.py) ultimately works with daily-normalized price series for downstream calculations such as volatility scaling and percentage-style transformations.

So the daily adjusted-price path is not an isolated quirk. It is a broader assumption in the backtest stack: normalize to business days after obtaining the natural-frequency series.

## Practical interpretation

If you inspect a multiple-prices CSV and see intraday timestamps, that does not mean the backtest is running directly on those contract-aware intraday rows.

The backtest first moves to the adjusted continuous series, then collapses that series to one value per business day with `.resample("1B").last()`.

So the clean mental model is:

1. multiple prices describe which contracts are current, forward, and carry,
2. adjusted prices turn those contract transitions into a continuous instrument series,
3. daily backtest prices are the last observed adjusted prices in each business day.