# Terms And Definitions

This short glossary collects a few futures-data terms that appear in the introductory backtest example and elsewhere in pysystemtrade.

## Futures Contract

A standardized agreement between two parties to buy or sell a specific asset at a specific price on a set future date. No matter what happens to the underlying asset prices in the interim, both sides are legally obligated to follow through when the contract expires. In practice, most traders unwind their positions prior to expiry.

### Futures Pricing

Futures prices aren't forecasts of where spot prices will land at expiration. Instead, they reflect current spot prices adjusted for the cost of holding the asset until delivery. This relationship is called the cost-of-carry model.

### Key Components of a Futures Contract

 - underlying asset: what is being traded (e.g crude oil, a stock index, currency, etc.)
 - standardized contract size: how many per contract (e.g. 1,000 barrels of crude oil)
 - delivery date: the month and day when the contract expires
 - tick size: minimum price movement ($0.01 per barrel for oil)
 - settlement: is the contract cash settled, or phyiscally delivered
 - margin requirements: the amount of $$ needed to be held at the clearinghouse

### How Futures Contracts Work

When you open a futures position, you're either going long, meaning you agree to buy the underlying asset at the specified price when the contract expires, or, you're going short, meaning you agree to sell the underlying asset at the specified price.

You don't have to pay the full contract value up front, instead you deposit margin, which typically ranges from 5 - 20% of the contract's total value. This creates leverage, meaning small price movements translate into large percentage gains or losses on your deposit.

Most traders of futures close positions before expiration by entering an opposite trade. If you took a position by buying one December crude oil contract, you'd exit by selling one December crude oil contract. The difference between your entry and exit prices is your profit or loss.

### Margin in Futures Trading

 - Initial Margin: what you deposit to open a position
 - Maintenance Margin: the minimum balance your account must maintain to continue holding that position

If the market moves against you and your account balance falls below the maintenance level, you'll receive a margin call; a demand to deposit funds immediately to restore your account all the way back to the initial margin amount, not just the maintenance margin.

For example, if you control a $50,000 contract with $5,000 initial margin and a $4,000 maintenance requirement, a drop below $4,000 means you must bring the account back to $5,000 immediately, or the broker can liquidate your position without asking.

### Daily Settlement and Mark-to-Market

Futures accounts settle at the end of every trading day through a process called mark-to-market. Cash is credited or debited to your account accordingly.

### Types of Futures Contracts

The two broad categories are commodity futures and financial futures. Commodity futures include agriculture, energy, and metals contracts. Common financial futures include equity indicies, interest rates, and currencies. 

## Back-adjusted price per instrument

A back-adjusted price is a continuous historical futures price series for a single instrument, adjusted to remove artificial jumps that occur when the system rolls from one contract month to the next.

In pysystemtrade, this series is primarily used for signal generation and volatility calculations. It is built from multiple-price data using a back-adjustment process.

## Carry contracts

In futures trading, carry contracts (or back-month/deferred contracts) refer to later expiration months compared to the current front-month price, reflecting the cost-of-carry model. Their pricing structure is defined by market conditions relative to the spot or near-term price.

In practice, pysystemtrade stores both the current contract and the carry contract so it can compare prices across expiries and infer the slope of the futures curve.

## Carry rules

Carry rules are trading rules that convert carry information into a forecast.

Instead of looking for trend, a carry rule looks at the relationship between contract expiries. That relationship is used to estimate whether holding the position offers positive or negative carry.

## Point size

Point size is the cash value of a one-point move in the futures price for one contract.

It is the quantity that converts a price move into P&L and risk. If a contract moves by 1.0 price points, the cash change per contract is `1.0 * point_size` in the instrument currency.

## Contango

Contango is a futures-curve shape in which farther-dated contracts trade above nearer-dated contracts. When futures prices exceed spot prices, the market is in contango.

In many cases, that implies a negative roll yield for a long position when exposure is rolled forward over time.

## Backwardation

Backwardation is a futures-curve shape in which farther-dated contracts trade below nearer-dated contracts. When futures prices trade below spot prices, the market is in backwardation, often signaling tight current supply or strong immediate demand.

In many cases, that implies a positive roll yield for a long position when exposure is rolled forward over time.

## Roll

A roll is the act of closing exposure in one contract month and moving it into another contract month before expiry.

In pysystemtrade, roll calendars define when this happens, and the resulting sequence of contracts is used to build multiple-price and back-adjusted price series.

## Backtest output variables

The introductory backtest example also prints a sequence of intermediate variables that show how a price series is transformed into a portfolio position.

### `raw_forecast`

`raw_forecast` is the direct output of one trading rule for one instrument before scaling or capping.

In the example, it is the `ewmac16_64` forecast for `SOFR`, produced from the rule definition in the Chapter 15 futures configuration.

### `capped_forecast`

`capped_forecast` is the same trading-rule forecast after forecast scaling and forecast capping have been applied.

This is the normalized single-rule forecast that the forecast-combination stage consumes.

### `combined_forecast`

`combined_forecast` is the instrument-level forecast produced by combining all active forecasts for that instrument using forecast weights and the forecast diversification multiplier.

In the Chapter 15 example configuration, this is not just the `ewmac16_64` rule. It combines the active weighted rules for the instrument.

### `subsystem_position`

`subsystem_position` is the position implied by the combined forecast after volatility-based position sizing, assuming the instrument is being sized in isolation.

It is the position before portfolio-level instrument weighting is applied.

### `notional_position`

`notional_position` is the portfolio-level position after applying instrument weights and the instrument diversification multiplier to the subsystem position.

`Notional` means the position is still based on the configured fixed trading capital rather than capital that changes through realized profit and loss.

## Signal and orders

These terms help connect the backtest outputs to actual trading decisions.

### `signal`

A signal is the model's directional opinion about an instrument.

In this system, the forecast is the signal. A positive forecast implies a long bias, a negative forecast implies a short bias, and the magnitude of the forecast indicates signal strength.

### `target position`

A target position is the position size the system wants to hold after translating a forecast into portfolio exposure.

In the backtest pipeline, `subsystem_position` is an instrument-in-isolation target, and `notional_position` is the portfolio-level target after instrument weighting and diversification scaling.

### `buffered position`

A buffered position is a no-trade range around the target position.

Instead of trading every small change in the target, the system allows the held position to remain within a band. Orders are only generated when the actual or recorded position moves outside that band.

### `instrument order`

An instrument order is an order at the instrument level, before choosing a specific futures contract.

It represents the required trade needed to move from the current recorded position to the desired target or buffered target. Only later is it translated into one or more contract-specific orders for execution.

## Forecast to order summary

The high-level transformation is:

`raw_forecast` -> `capped_forecast` -> `combined_forecast` -> `subsystem_position` -> `notional_position` -> buffered or optimal target position -> possible order

In words:

- A trading rule first produces a raw forecast.
- The system scales and caps that forecast so different rules can be combined consistently.
- The active rule forecasts are weighted into a combined forecast for the instrument.
- The combined forecast is converted into a volatility-scaled target position.
- Portfolio weights and diversification turn that into the notional portfolio target.
- The trading system compares the current recorded position with that target or its buffer range.
- Only the difference becomes an order, which is then translated from an instrument-level order into specific contract orders and broker orders.

## Portfolio performance

The output of `system.accounts.portfolio().stats()` is a summary of the portfolio account curve. In the introductory backtest, these statistics are computed from the portfolio-level P&L series produced by the accounts stage.

### `portfolio`

`portfolio` is the total account curve for the whole trading system after combining all instruments, weights, diversification effects, and costs.

This is the main series used to evaluate overall backtest performance.

### `min`

The smallest single-period return in the account curve.

### `max`

The largest single-period return in the account curve.

### `median`

The median single-period return in the account curve.

This is the midpoint return after ordering all single-period returns from lowest to highest.

### `mean`

The arithmetic average single-period return in the account curve.

### `std`

The standard deviation of single-period returns.

This is the basic measure of return variability at the curve's current frequency.

### `skew`

The skewness of single-period returns.

Negative skew means losses tend to be more extreme than gains. Positive skew means gains tend to be more extreme than losses.

### `ann_mean`

The annualized mean return.

This rescales the average single-period return into a per-year figure based on the frequency of the data.

### `ann_std`

The annualized standard deviation of returns.

This rescales return volatility into a per-year figure.

### `sharpe`

The Sharpe ratio, calculated here as annualized mean return divided by annualized standard deviation.

It measures return per unit of overall volatility.

### `sortino`

The Sortino ratio, calculated here as annualized mean return divided by annualized downside volatility.

Unlike Sharpe, it penalizes only negative return variability.

### `avg_drawdown`

The average drawdown over the account curve.

Drawdown measures how far the cumulative P&L is below its running peak. This statistic averages those drawdown values through time.

### `time_in_drawdown`

The fraction of observed periods spent below the previous cumulative peak.

For example, a value near `1.0` means the system spent most of its history below a prior high watermark.

### `calmar`

The Calmar ratio, calculated here as annualized mean return divided by the magnitude of the worst drawdown.

It measures return relative to the largest historical peak-to-trough loss.

### `avg_return_to_drawdown`

The annualized mean return divided by the magnitude of the average drawdown.

This is similar in spirit to Calmar, but uses average drawdown instead of worst drawdown.

### `avg_loss`

The average size of negative single-period returns.

### `avg_gain`

The average size of positive single-period returns.

### `gaintolossratio`

The average gain divided by the absolute value of the average loss.

Values above `1.0` mean the typical gain is larger than the typical loss.

### `profitfactor`

The sum of all gains divided by the absolute value of the sum of all losses.

Values above `1.0` mean total gains exceed total losses.

### `hitrate`

The proportion of non-zero-return periods that are gains rather than losses.

It does not measure gain size, only frequency.

### `t_stat`

The one-sample t-statistic for testing whether the mean return is different from zero.

Higher absolute values indicate stronger statistical evidence against a zero-mean return series.

### `p_value`

The p-value associated with the one-sample t-test on mean returns.

Smaller values indicate stronger evidence that the mean return differs from zero.

### `rolling_ann_std`

An auxiliary plot or series showing rolling annualized volatility through time.

It is useful for seeing whether the strategy risk level is stable.

### `drawdown`

An auxiliary plot or series showing the running drawdown through time.

### `curve`

An auxiliary plot or series showing cumulative P&L through time.

### `percent`

An alternate representation of the account curve in percentage-of-capital terms rather than value terms.

This is often the most intuitive way to compare performance across systems or capital sizes.

## References

1. [docs/data.md#L133](/Users/arthurvargas/dev/pysystemtrade/docs/data.md#L133) explains instrument configuration and identifies futures contract point size as core metadata.
2. [docs/data.md#L243](/Users/arthurvargas/dev/pysystemtrade/docs/data.md#L243) explains roll calendars, `carry_contract`, and how carry contracts are used to calculate forecasts for carry trading rules.
3. [docs/data.md#L742](/Users/arthurvargas/dev/pysystemtrade/docs/data.md#L742) defines the multiple-prices object and its contract columns, including `PRICE_CONTRACT` and `CARRY_CONTRACT`.
4. [docs/data.md#L750](/Users/arthurvargas/dev/pysystemtrade/docs/data.md#L750) explains adjusted prices and notes that they are created by a back-adjustment process from multiple prices.
5. [sysobjects/adjusted_prices.py#L40](/Users/arthurvargas/dev/pysystemtrade/sysobjects/adjusted_prices.py#L40) shows the implementation entry point for back-adjusting multiple prices using the Panama stitching method.
6. [systems/provided/rules/carry.py#L1](/Users/arthurvargas/dev/pysystemtrade/systems/provided/rules/carry.py#L1) contains the carry rule implementation used to turn carry data into a forecast.
7. [sysdata/sim/futures_sim_data.py#L182](/Users/arthurvargas/dev/pysystemtrade/sysdata/sim/futures_sim_data.py#L182) shows where point size is read from instrument metadata for simulation use.
8. [examples/introduction/basic_csv_backtest.py#L133](/Users/arthurvargas/dev/pysystemtrade/examples/introduction/basic_csv_backtest.py#L133) shows where `raw_forecast` is assigned in the example.
9. [examples/introduction/basic_csv_backtest.py#L134](/Users/arthurvargas/dev/pysystemtrade/examples/introduction/basic_csv_backtest.py#L134) shows where `capped_forecast` is assigned in the example.
10. [examples/introduction/basic_csv_backtest.py#L137](/Users/arthurvargas/dev/pysystemtrade/examples/introduction/basic_csv_backtest.py#L137) shows where `combined_forecast` is assigned in the example.
11. [examples/introduction/basic_csv_backtest.py#L138](/Users/arthurvargas/dev/pysystemtrade/examples/introduction/basic_csv_backtest.py#L138) shows where `subsystem_position` is assigned in the example.
12. [examples/introduction/basic_csv_backtest.py#L139](/Users/arthurvargas/dev/pysystemtrade/examples/introduction/basic_csv_backtest.py#L139) shows where `notional_position` is assigned in the example.
13. [systems/forecasting.py#L78](/Users/arthurvargas/dev/pysystemtrade/systems/forecasting.py#L78), [systems/forecast_scale_cap.py#L30](/Users/arthurvargas/dev/pysystemtrade/systems/forecast_scale_cap.py#L30), [systems/forecast_combine.py#L55](/Users/arthurvargas/dev/pysystemtrade/systems/forecast_combine.py#L55), [systems/positionsizing.py#L86](/Users/arthurvargas/dev/pysystemtrade/systems/positionsizing.py#L86), and [systems/portfolio.py#L178](/Users/arthurvargas/dev/pysystemtrade/systems/portfolio.py#L178) are the stage methods that produce those five values.
14. [systems/provided/futures_chapter15/futuresconfig.yaml#L75](/Users/arthurvargas/dev/pysystemtrade/systems/provided/futures_chapter15/futuresconfig.yaml#L75) shows the Chapter 15 forecast weights, confirming that the example’s `combined_forecast` is built from multiple active rules rather than only `ewmac16_64`.
15. [docs/production.md#L962](/Users/arthurvargas/dev/pysystemtrade/docs/production.md#L962) explains optimal positions and how they are stored as trading targets.
16. [docs/production.md#L991](/Users/arthurvargas/dev/pysystemtrade/docs/production.md#L991) explains how current positions are compared with optimal or buffered targets to generate instrument orders.
17. [docs/backtesting.md#L2740](/Users/arthurvargas/dev/pysystemtrade/docs/backtesting.md#L2740) shows the `portfolio().stats()` example output and explains that `stats()` lists summary statistics plus other useful plot and display methods.
18. [systems/accounts/curves/account_curve.py#L234](/Users/arthurvargas/dev/pysystemtrade/systems/accounts/curves/account_curve.py#L234) contains the implementations of `sharpe`, drawdown-based metrics, gain/loss metrics, hit rate, t-statistic, p-value, and `stats()`.
19. [docs/backtesting.md#L2810](/Users/arthurvargas/dev/pysystemtrade/docs/backtesting.md#L2810) explains auxiliary portfolio/account-curve views such as `rolling_ann_std`, `drawdown`, `curve`, and `percent`.