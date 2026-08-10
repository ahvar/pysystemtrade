## Dataflow in Calculation of Cumulative Net P&L for Backtest

See also [futures_price_file_representations.md](futures_price_file_representations.md) for the distinction between adjusted-price CSV files and multiple-prices CSV files, [daily_backtest_price_from_adjusted_prices.md](daily_backtest_price_from_adjusted_prices.md) for the full daily backtest price path, and [redesign_models.md](redesign_models.md) for redesign notes.

The example entrypoint is [run_backtest()](../../examples/introduction/basic_csv_backtest.py#L120) in [../../examples/introduction/basic_csv_backtest.py](../../examples/introduction/basic_csv_backtest.py). That function constructs a `System` by calling [futures_system(data=data, config=config)](../../systems/provided/futures_chapter15/basesystem.py#L22), then pulls representative outputs from each stage before finally asking the account stage for portfolio P&L.

## Stage construction

[futures_system()](../../systems/provided/futures_chapter15/basesystem.py#L22) uses [csvFuturesSimData()](../../sysdata/sim/csv_futures_sim_data.py#L20) by default if no data object is supplied. It then creates a [System](../../systems/basesystem.py#L25) with these stages, in this order:

1. `Account()`
2. `Portfolios()`
3. `PositionSizing()`
4. `RawData()`
5. `ForecastCombine()`
6. `ForecastScaleCap()`
7. `Rules()`

[System.__init__()](../../systems/basesystem.py#L42) stores the `data` and `config`, calls `data.system_init(self)`, and attaches each stage to the system using its `name` property. So after construction the backtest can access `system.accounts`, `system.portfolio`, `system.positionSize`, `system.rawdata`, `system.combForecast`, `system.forecastScaleCap`, and `system.rules`.

## How the instrument universe is chosen

[run_backtest()](../../examples/introduction/basic_csv_backtest.py#L120) calls [system.get_instrument_list()](../../systems/basesystem.py#L152) and compares the result with `config.instrument_weights`.

The method [System.get_instrument_list()](../../systems/basesystem.py#L152) delegates to [_get_raw_instrument_list_from_config()](../../systems/basesystem.py#L205) and uses this precedence:

1. `config.instrument_weights.keys()`
2. `config.instruments`
3. `self.data.get_instrument_list()`

After that it removes ignored, duplicate, short-history, or otherwise excluded instruments and returns a sorted unique list.

This matters because the backtest universe is usually driven by the config, not directly by whatever CSV files exist on disk. The data layer is only used as a fallback if the config does not specify instruments.

### What `@base_system_cache()` is doing here

[System.get_instrument_list()](../../systems/basesystem.py#L152) is decorated with [@base_system_cache()](../../systems/basesystem.py#L151), implemented by [base_system_cache()](../../systems/system_cache.py#L753).

This decorator routes the method through [system.cache.calc_or_cache()](../../systems/system_cache.py#L527), so repeated calls with the same effective arguments return the cached result instead of recomputing the instrument list.

The important part is not just memoization. The decorator also calls `calc_or_cache(..., instrument_classify=False, use_arg_names=False)` inside [base_system_cache()](../../systems/system_cache.py#L753).

That matters because the normal cache-key builder for stage methods, [cache_ref()](../../systems/system_cache.py#L589), tries to identify whether any function argument is an instrument code. To do that, when `instrument_classify=True`, it first fetches the current system instrument universe via [self.get_instrument_list()](../../systems/system_cache.py#L622).

If `System.get_instrument_list()` used the normal stage-style cache decorator, cache key generation for `get_instrument_list()` would try to call `get_instrument_list()` again while it was already in the middle of caching `get_instrument_list()`. That is the recursion problem mentioned in the comment.

The safe path is:

1. [@base_system_cache()](../../systems/basesystem.py#L151) wraps [get_instrument_list()](../../systems/basesystem.py#L152).
2. [base_system_cache()](../../systems/system_cache.py#L753) calls [calc_or_cache()](../../systems/system_cache.py#L527) with `instrument_classify=False`.
3. [cache_ref()](../../systems/system_cache.py#L589) then uses an empty `list_of_codes` instead of calling [self.get_instrument_list()](../../systems/system_cache.py#L622).
4. The cache key is treated as a cross-market key rather than an instrument-specific key, and the original [get_instrument_list()](../../systems/basesystem.py#L152) function can run normally.

So “preventing recursion problems” here specifically means preventing the cache system from recursively calling `get_instrument_list()` while trying to build the cache key for `get_instrument_list()` itself.

## Price input into the backtest

For backtests using [csvFuturesSimData()](../../sysdata/sim/csv_futures_sim_data.py#L20), the directional pipeline starts from the adjusted price series, not a raw front-contract series.

At a high level the price path is:

`multiple prices -> adjusted prices -> get_raw_price() -> daily_prices() -> forecasts -> positions -> P&L`

The detailed trace for how adjusted prices are loaded and why daily backtest prices are the last observed adjusted price per business day is in [daily_backtest_price_from_adjusted_prices.md](daily_backtest_price_from_adjusted_prices.md).

## Trace for the rest of the backtest pipeline

The example `run_backtest()` then asks the system for these values:

1. `system.rawdata.get_daily_prices(INSTRUMENT)` via [RawData.get_daily_prices()](../../systems/rawdata.py#L57)
2. `system.rules.get_raw_forecast(INSTRUMENT, "ewmac16_64")`
3. `system.forecastScaleCap.get_capped_forecast(INSTRUMENT, "ewmac16_64")`
4. `system.combForecast.get_combined_forecast(INSTRUMENT)`
5. `system.positionSize.get_subsystem_position(INSTRUMENT)` via [PositionSizing.get_subsystem_position()](../../systems/positionsizing.py#L86)
6. `system.portfolio.get_notional_position(INSTRUMENT)` via [Portfolios.get_notional_position()](../../systems/portfolio.py#L178)

That is the main directional chain:

`adjusted prices -> raw forecast -> scaled/capped forecast -> combined forecast -> subsystem position -> portfolio position`

## How cumulative portfolio P&L is built

The account stage is where the portfolio P&L is aggregated.

`Account()` is the stage named `accounts`. The portfolio-level method actually lives on [accountPortfolio](../../systems/accounts/account_portfolio.py#L8), and [accountPortfolio](../../systems/accounts/account_portfolio.py#L8) inherits from [accountInstruments](../../systems/accounts/account_instruments.py#L15).

When `run_backtest()` calls `system.accounts.portfolio()`:

1. [accountPortfolio.portfolio()](../../systems/accounts/account_portfolio.py#L10) gets capital and the system instrument list.
2. It loops over each instrument and calls [self.pandl_for_instrument(instrument_code)](../../systems/accounts/account_instruments.py#L18).
3. [accountInstruments.pandl_for_instrument()](../../systems/accounts/account_instruments.py#L18) gets the buffered position for that instrument via [get_buffered_position()](../../systems/accounts/account_buffering_system.py#L54).
4. It then calls [_pandl_for_instrument_with_positions()](../../systems/accounts/account_instruments.py#L62).
5. That chooses either the SR-cost or cash-cost P&L path.
6. Both paths pull price, FX, value-per-point, and cost inputs, construct a P&L calculator, and wrap it in an `accountCurve`.
7. [accountPortfolio.portfolio()](../../systems/accounts/account_portfolio.py#L10) combines the per-instrument curves into a `dictOfAccountCurves` and then an `accountCurveGroup`.

So cumulative net P&L is not calculated in one large function. It emerges from combining the instrument-level account curves, where each instrument curve is driven by:

`buffered position + adjusted price series + FX conversion + contract value + trading costs`

## Practical summary

If you are tracing a surprising backtest result, the usual checkpoints are:

1. `config.instrument_weights` or `config.instruments` to confirm the intended universe.
2. `system.get_instrument_list()` to see what actually survived filtering.
3. [daily_backtest_price_from_adjusted_prices.md](daily_backtest_price_from_adjusted_prices.md) to verify how the back-adjusted input series becomes a daily backtest price series.
4. `system.rawdata`, `system.rules`, `system.forecastScaleCap`, `system.combForecast`, `system.positionSize`, and `system.portfolio` to see where the numbers first diverge.
5. `system.accounts.portfolio()` and `system.accounts.pandl_for_instrument(...)` to inspect the final P&L build.

## Trace for `system.portfolio.get_notional_position()`

The portfolio stage converts a per-instrument subsystem position into a portfolio-level notional position by applying instrument weights, the instrument diversification multiplier, and optionally a risk overlay.

The path is:

1. [run_backtest()](../../examples/introduction/basic_csv_backtest.py#L120) calls [system.portfolio.get_notional_position(INSTRUMENT)](../../systems/portfolio.py#L178).
2. [Portfolios.get_notional_position()](../../systems/portfolio.py#L178) gets [get_notional_position_before_risk_scaling(instrument_code)](../../systems/portfolio.py#L231).
3. [get_notional_position_before_risk_scaling()](../../systems/portfolio.py#L231) gets [get_notional_position_without_idm(instrument_code)](../../systems/portfolio.py#L251) and multiplies it by the instrument diversification multiplier.
4. [get_notional_position_without_idm()](../../systems/portfolio.py#L251) gets the time series of instrument weights from [get_instrument_weights()](../../systems/portfolio.py#L422) and the subsystem position, aligns them by index, and multiplies them together.
5. [get_subsystem_position()](../../systems/positionsizing.py#L86) comes from the [PositionSizing](../../systems/positionsizing.py#L20) stage.
6. [PositionSizing.get_subsystem_position()](../../systems/positionsizing.py#L86) computes:

	`vol_scalar * combined_forecast / average_absolute_forecast`

7. `vol_scalar` is [get_average_position_at_subsystem_level(instrument_code)](../../systems/positionsizing.py#L164), which is the daily cash volatility target divided by instrument value volatility.
8. `combined_forecast` comes from `system.combForecast.get_combined_forecast(instrument_code)`.
9. The portfolio stage then multiplies by the instrument diversification multiplier and, if configured, a risk scalar overlay.

So the practical formula is:

`notional_position = subsystem_position * instrument_weight * IDM * optional_risk_scalar`

More explicitly, the subsystem position itself is built from:

`subsystem_position = average_position_for_one_instrument * combined_forecast / average_absolute_forecast`

where `average_position_for_one_instrument` is the position size that would hit the target volatility if the instrument were traded on its own.

### Where instrument weights come from

[system.portfolio.get_instrument_weights()](../../systems/portfolio.py#L422) does not just return the raw config dict. It:

1. reads either estimated weights or fixed weights,
2. expands them into a time series covering the subsystem position index,
3. adjusts for instruments with missing positions,
4. resamples to business days,
5. smooths them with an EWMA span from config,
6. normalises them so the row sums are one.

So even when weights begin as a static config dict, the object consumed by `get_notional_position()` is a daily aligned DataFrame of weights.

### Where buffering enters

[get_notional_position()](../../systems/portfolio.py#L178) is still the optimal portfolio position, not necessarily the traded position used for P&L. The account stage later calls [get_buffered_position()](../../systems/accounts/account_buffering_system.py#L54).

That path is:

1. [accountInstruments.pandl_for_instrument()](../../systems/accounts/account_instruments.py#L18)
2. [accountBufferingSystemLevel.get_buffered_position()](../../systems/accounts/account_buffering_system.py#L54)
3. [get_notional_position()](../../systems/portfolio.py#L178)
4. optional buffer logic from `get_buffers_for_position()` and `apply_buffer()`
5. optional rounding to whole contracts

So if the user sees a difference between a portfolio notional position and realised account P&L, the first thing to check is whether buffering or rounding has materially changed the trade path.

## Trace for the final P&L calculators

The final account curve is built instrument by instrument. Each instrument curve starts with a traded position series and a price series, then adds contract-value conversion, FX conversion, capital scaling, and costs.

The top-level path is:

1. [system.accounts.portfolio()](../../systems/accounts/account_portfolio.py#L10) loops over instruments.
2. For each instrument it calls [system.accounts.pandl_for_instrument(instrument_code)](../../systems/accounts/account_instruments.py#L18).
3. That gets the buffered position and passes it into [_pandl_for_instrument_with_positions(...)](../../systems/accounts/account_instruments.py#L62).
4. [_pandl_for_instrument_with_positions(...)](../../systems/accounts/account_instruments.py#L62) chooses one of two branches:
	- `pandlCalculationWithSRCosts`
	- `pandlCalculationWithCashCostsAndFills`

The common inputs passed into the calculator are:

1. `price`: from `get_instrument_prices_for_position_or_forecast(...)`
2. `positions`: buffered positions, optionally lagged by one period and rounded
3. `fx`: from `get_fx_rate(instrument_code)`
4. `capital`: notional trading capital
5. `value_per_point`: contract point value for the instrument

### Gross P&L path shared by both calculators

Both cost models inherit the core gross P&L logic from [pandlCalculation](../../systems/accounts/pandl_calculators/pandl_calculation.py#L8).

That logic is:

1. align positions and prices on the same index inside [calculate_pandl()](../../systems/accounts/pandl_calculators/pandl_calculation.py#L223),
2. forward-fill both inside [calculate_pandl()](../../systems/accounts/pandl_calculators/pandl_calculation.py#L223),
3. calculate `price.diff()` inside [calculate_pandl()](../../systems/accounts/pandl_calculators/pandl_calculation.py#L223),
4. multiply price changes by `positions.shift(1)` inside [calculate_pandl()](../../systems/accounts/pandl_calculators/pandl_calculation.py#L223),
5. convert points P&L into instrument currency via [pandl_in_points()](../../systems/accounts/pandl_calculators/pandl_calculation.py#L124) and `_pandl_in_instrument_ccy_given_points_pandl()`,
6. convert instrument currency into base currency via [pandl_in_base_currency()](../../systems/accounts/pandl_calculators/pandl_calculation.py#L99),
7. divide by capital when a percentage P&L curve is requested via [percentage_pandl()](../../systems/accounts/pandl_calculators/pandl_calculation.py#L83).

In formula form:

`gross_points_pandl_t = position_(t-1) * (price_t - price_(t-1))`

then:

`gross_base_ccy_pandl = gross_points_pandl * value_per_point * fx`

and percentage P&L is that series divided by capital.

This is the main reason the adjusted-price input trace matters so much: every downstream account curve is ultimately driven by differences in that price series.

### SR-cost path

If the account stage is using SR costs, [_pandl_for_instrument_with_SR_costs()](../../systems/accounts/account_instruments.py#L116) builds a [pandlCalculationWithSRCosts](../../systems/accounts/pandl_calculators/pandl_SR_cost.py#L13) object.

That path uses:

1. `price`
2. `positions`
3. `fx`
4. `value_per_point`
5. `capital`
6. `daily_returns_volatility`
7. `instrument_turnover`
8. `annualised_SR_cost`
9. `average_position`

The SR-cost model does not simulate explicit trade fills. Instead it transforms the annualised Sharpe-ratio cost assumption into a small negative return stream distributed across the periods in which the instrument is held.

Conceptually:

1. estimate annualised price volatility in points,
2. scale that by the average position,
3. multiply by the SR cost assumption with a minus sign,
4. spread that annual cost over the price index periods,
5. add it to gross P&L to get net P&L.

This is a smooth cost model. It is useful for research because it is cheaper to compute and avoids explicit trade-by-trade simulation.

### Cash-cost path

If the account stage is using cash costs, [_pandl_for_instrument_with_cash_costs()](../../systems/accounts/account_instruments.py#L178) builds a [pandlCalculationWithCashCostsAndFills](../../systems/accounts/pandl_calculators/pandl_cash_costs.py#L21) object.

That path uses:

1. `raw_costs` from instrument metadata plus spread cost data,
2. `price`
3. `positions`
4. `capital`
5. `value_per_point`
6. `fx`
7. `rolls_per_year`
8. `multiply_roll_costs_by`
9. `vol_normalise_currency_costs`

This model explicitly constructs fills and charges costs in instrument currency.

It combines:

1. trading fills from position changes,
2. pseudo-fills representing periodic roll activity,
3. cost calculations from the instrument cost object,
4. optional volatility normalisation of currency-denominated costs.

The resulting costs series is then converted:

`instrument currency costs -> points costs -> base currency costs -> percentage costs`

Net P&L is always:

`net = gross + costs`

where costs are negative numbers.

### Why the two cost paths matter

If you are comparing two backtests and the forecasts and positions match but portfolio performance differs, inspect which branch `_pandl_for_instrument_with_positions()` took.

The SR-cost branch produces a smoothed cost drag based on turnover and volatility. The cash-cost branch produces event-driven costs based on explicit fills and simulated rolls from [list_of_all_fills()](../../systems/accounts/pandl_calculators/pandl_cash_costs.py#L97), with per-fill costs from [calculate_cost_instrument_currency_for_a_fill()](../../systems/accounts/pandl_calculators/pandl_cash_costs.py#L205). Those can diverge materially, especially in higher-turnover instruments.