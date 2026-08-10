## Futures Price File Representations

This note explains the two CSV file types used for futures backtests in pysystemtrade:

1. `data/futures/adjusted_prices_csv/<INSTRUMENT>.csv`
2. `data/futures/multiple_prices_csv/<INSTRUMENT>.csv`

For example, for AEX these are:

1. [../../data/futures/adjusted_prices_csv/AEX.csv](../../data/futures/adjusted_prices_csv/AEX.csv)
2. [../../data/futures/multiple_prices_csv/AEX.csv](../../data/futures/multiple_prices_csv/AEX.csv)

They are both loaded by `csvFuturesSimData`, but they represent different levels of abstraction.

## Which loader reads which file

The adjusted-price file is loaded by [csvFuturesAdjustedPricesData](../../sysdata/csv/csv_adjusted_prices.py#L16).

The multiple-prices file is loaded by [csvFuturesMultiplePricesData](../../sysdata/csv/csv_multiple_prices.py#L16).

Those two storage classes are both added by [csvFuturesSimData](../../sysdata/sim/csv_futures_sim_data.py#L20) when the simulation data blob is constructed.

## What the adjusted-price file is

The adjusted-price file is a single synthetic continuous price series for an instrument.

For AEX, [../../data/futures/adjusted_prices_csv/AEX.csv](../../data/futures/adjusted_prices_csv/AEX.csv) has the shape:

```csv
DATETIME,price
2009-08-18 23:00:00,101.67000000000019
2009-08-19 23:00:00,101.37000000000023
...
```

It is loaded by [csvFuturesAdjustedPricesData._get_adjusted_prices_without_checking()](../../sysdata/csv/csv_adjusted_prices.py#L40) and converted into a [futuresAdjustedPrices](../../sysobjects/adjusted_prices.py#L11) object, which is just a pandas Series with some domain-specific methods.

This is not the literal close series of one fixed futures contract month. It is a back-adjusted stitched series.

The code path for that is in [futuresAdjustedPrices.stitch_multiple_prices()](../../sysobjects/adjusted_prices.py#L28), which creates adjusted prices from a [futuresMultiplePrices](../../sysobjects/multiple_prices.py#L58) object.

The default stitching logic is the Panama method in [_panama_stitch()](../../sysobjects/adjusted_prices.py#L58). When a roll happens, [_roll_in_panama()](../../sysobjects/adjusted_prices.py#L90) shifts all prior adjusted values by the roll differential:

`previous_row.FORWARD - previous_row.PRICE`

That is why the adjusted AEX prices are on a very different numeric level from the raw `PRICE` column in the multiple-prices file. The adjusted series accumulates historical roll offsets.

## What the multiple-prices file is

The multiple-prices file is the contract-aware source series used to derive adjusted prices and carry data.

The object definition in [../../sysobjects/multiple_prices.py](../../sysobjects/multiple_prices.py#L1) and the docs in [../data.md](../data.md#L732) describe it as a DataFrame with six columns:

1. `PRICE`
2. `CARRY`
3. `FORWARD`
4. `PRICE_CONTRACT`
5. `CARRY_CONTRACT`
6. `FORWARD_CONTRACT`

The named-price constants are defined in [../../sysobjects/dict_of_named_futures_per_contract_prices.py](../../sysobjects/dict_of_named_futures_per_contract_prices.py#L10).

For AEX, [../../data/futures/multiple_prices_csv/AEX.csv](../../data/futures/multiple_prices_csv/AEX.csv) begins like this:

```csv
DATETIME,CARRY,CARRY_CONTRACT,PRICE,PRICE_CONTRACT,FORWARD,FORWARD_CONTRACT
2009-08-18 23:00:00,284.45,20091000,284.4,20090900,284.45,20091000
2009-08-19 23:00:00,284.15,20091000,284.1,20090900,284.15,20091000
...
```

This means:

1. `PRICE` is the price series for the currently priced contract.
2. `PRICE_CONTRACT` tells you which contract month that `PRICE` value came from.
3. `FORWARD` is the price series for the next contract, typically the one that would be rolled into.
4. `FORWARD_CONTRACT` tells you which contract month that forward value came from.
5. `CARRY` is the contract used for carry calculations.
6. `CARRY_CONTRACT` tells you which contract month that carry value came from.

The docs phrase these as the current priced contract, the next contract, and the carry contract in [../data.md](../data.md#L720).

## Is this daily close data?

Mostly, but not always.

The naming in the object layer uses “final prices”, which strongly suggests closing or final sampled prices for a timestamp; see [futuresNamedContractFinalPricesWithContractID](../../sysobjects/dict_of_named_futures_per_contract_prices.py#L37).

However, the multiple-prices file is not guaranteed to be strictly one row per day. Your AEX file clearly includes intraday timestamps starting around `2011-05-25 07:00:00`.

So the safest interpretation is:

1. `PRICE`, `FORWARD`, and `CARRY` are timestamped final prices for their named contracts.
2. In many historical sections they appear daily.
3. In some sections they become intraday.

The adjusted-price file is likewise a timestamped stitched series, not a guarantee of one official exchange close per session.

## Why there are two files

The multiple-prices file is the richer contract-aware representation.

It is needed for:

1. carry calculations,
2. tracking which contract is current, forward, and carry,
3. constructing a continuous adjusted series across rolls.

The adjusted-price file is the simpler backtest-ready representation.

It is needed because the futures simulation layer uses the back-adjusted series as the instrument “raw price”; see [futuresSimData.get_raw_price_from_start_date()](../../sysdata/sim/futures_sim_data.py#L68).

So the relationship is:

`multiple prices -> adjusted prices -> backtest price input`

## How to read an AEX roll in practice

Take these two adjacent AEX rows from [../../data/futures/multiple_prices_csv/AEX.csv](../../data/futures/multiple_prices_csv/AEX.csv):

```csv
2009-09-16 23:00:00,312.7,20091000,312.7,20090900,312.7,20091000
2009-09-17 23:00:00,312.5,20091100,313.8,20091000,312.5,20091100
```

On the first row:

1. the priced contract is `20090900`,
2. the forward contract is `20091000`.

On the next row:

1. the priced contract has rolled to `20091000`,
2. the forward contract has moved to `20091100`.

That contract change is what [futuresAdjustedPrices.stitch_multiple_prices()](../../sysobjects/adjusted_prices.py#L28) detects. The Panama stitch then uses the prior row’s `FORWARD - PRICE` differential to shift historical adjusted prices before appending the new `PRICE` value.

So the adjusted-price file is not just a copy of the `PRICE` column. It is a transformed continuous series derived from the contract transitions encoded in the multiple-prices file.

## Practical summary

If you are tracing what the backtest is consuming:

1. [../../data/futures/multiple_prices_csv/AEX.csv](../../data/futures/multiple_prices_csv/AEX.csv) is the contract-aware source representation.
2. [../../data/futures/adjusted_prices_csv/AEX.csv](../../data/futures/adjusted_prices_csv/AEX.csv) is the derived continuous representation.
3. [csvFuturesMultiplePricesData](../../sysdata/csv/csv_multiple_prices.py#L16) loads the first.
4. [csvFuturesAdjustedPricesData](../../sysdata/csv/csv_adjusted_prices.py#L16) loads the second.
5. The backtest ultimately uses the adjusted series as its futures price input via [futuresSimData.get_raw_price_from_start_date()](../../sysdata/sim/futures_sim_data.py#L68).