## Redesign Notes: Domain Models and Storage Split

This note captures the redesign discussion for building a cleaner separate system around SQLAlchemy and Redis.

## Is `Instrument` plus `FuturesContract` a sensible first step?

Yes. It is a sensible starting point, but it is not sufficient on its own.

Those two concepts are the minimum stable domain backbone:

1. `Instrument` represents the tradable market at the strategy level.
2. `FuturesContract` represents one dated listed contract for that instrument.

That split is already implicit in the current codebase, even though the implementation is more file- and pipeline-oriented than domain-model-oriented. You can see pieces of it in [../../sysobjects/multiple_prices.py](../../sysobjects/multiple_prices.py), [../../sysobjects/adjusted_prices.py](../../sysobjects/adjusted_prices.py), and [../../sysdata/sim/futures_sim_data.py](../../sysdata/sim/futures_sim_data.py).

What those two models give you immediately is:

1. a place for static instrument metadata,
2. a place for contract identifiers, expiries, and lifecycle metadata,
3. a clean foreign-key backbone for price and carry observations.

That is the right first step because almost every other futures object hangs off one of those two levels.

## Why those two models are not enough

The current backtest logic relies on several distinct data representations that should stay distinct in a redesign.

In this repo, those representations are partly blurred together by loader classes and derived pandas objects. For example:

1. [../../data/futures/multiple_prices_csv](../../data/futures/multiple_prices_csv) stores contract-aware named series.
2. [../../data/futures/adjusted_prices_csv](../../data/futures/adjusted_prices_csv) stores derived continuous adjusted series.
3. [../../sysdata/data_blob.py](../../sysdata/data_blob.py#L14) aggregates storage access.
4. [../../sysdata/sim/futures_sim_data.py](../../sysdata/sim/futures_sim_data.py#L68) treats adjusted prices as the backtest “raw price”.

If you model only `Instrument` and `FuturesContract`, you still have nowhere explicit to represent:

1. raw observed contract prices,
2. the named-contract state used for roll and carry logic,
3. derived adjusted continuous series,
4. roll configuration and roll schedule decisions.

That usually leads to one of two bad outcomes:

1. derived objects get shoved back into the contract table, or
2. business logic leaks into ad hoc service code without clear storage boundaries.

## Proposed domain model split

The cleaner design is to separate static entities, raw observations, roll state, and derived series.

### Core entities

1. `Instrument`
   Strategy-level market identity, tick value, currency, exchange, sector, trading metadata, and configuration defaults.
2. `FuturesContract`
   One listed contract for one instrument, with contract code, expiry, first notice date, last trade date, multiplier overrides if needed, and status.

### Observed market data

3. `ContractPriceObservation`
   Timestamped observed prices for a specific `FuturesContract`. This is the canonical raw market-data table.
4. `FxRateObservation`
   Timestamped FX observations for valuation and P&L conversion.

### Roll-state / named series layer

5. `InstrumentRollState`
   For each timestamp, identify which contract is the current priced contract, forward contract, and carry contract for an instrument.
6. `InstrumentNamedPriceObservation`
   Timestamped values for `PRICE`, `FORWARD`, and `CARRY`, each tied to the specific contract that supplied it.

This layer is the database equivalent of what the current code stores in multiple-prices files.

### Derived series layer

7. `AdjustedPriceObservation`
   Timestamped continuous adjusted price series for an instrument.
8. `CarryObservation` or `CarryMetricObservation`
   Timestamped derived carry metrics used by forecasting logic.
9. `VolatilityObservation`
   Cached or materialized volatility measures if you decide they are expensive enough to persist.

### Configuration / control layer

10. `RollRule` or `RollConfiguration`
    Instrument-level rules for how to select priced, forward, and carry contracts.
11. `BacktestDataSnapshot` or `DerivedSeriesVersion`
    Optional versioning entity if you want reproducible regeneration of adjusted series and other derived artifacts.

## Why this split is better

This keeps each layer semantically narrow:

1. raw tables tell you what was observed,
2. roll-state tables tell you which contracts were active in each role,
3. derived-series tables tell you what was computed from that state,
4. config tables tell you why the computation selected those contracts.

That separation matters because adjusted prices are not raw facts. They are model outputs.

Once you preserve that boundary, it becomes much easier to:

1. recompute adjusted prices after changing roll rules,
2. compare alternative adjustment methods,
3. debug a surprising carry or roll decision,
4. backfill missing contract data without corrupting derived history.

## SQLAlchemy guidance

Use SQLAlchemy models for persistence structure, not as the home for time-series transformations.

A good division is:

1. ORM models define schema, relations, keys, and constraints.
2. Repository or gateway objects fetch and persist domain data.
3. Service-layer code performs stitching, roll selection, carry derivation, and daily normalization.
4. Strategy/backtest code consumes already-structured domain services.

That avoids fat ORM classes full of pandas logic and keeps the derivation pipeline testable outside the database layer.

## Redis guidance

Redis is useful, but it should sit on top of the domain split rather than replace it.

Good Redis use cases here are:

1. caching adjusted series by `(instrument, version)`,
2. caching roll-state lookups,
3. caching expensive forecast inputs such as precomputed volatility or carry transforms,
4. short-lived memoization for repeated backtest reads.

Less good Redis use cases are:

1. storing the only copy of canonical raw market data,
2. mixing raw and derived series without explicit versioning,
3. using cache keys as the only definition of business meaning.

The database should remain the source of truth. Redis should accelerate repeated reads of derived or query-heavy objects.

## Suggested build order

If you are building this as a fresh system, a sensible implementation order is:

1. define `Instrument` and `FuturesContract`,
2. add raw contract price observations,
3. add roll configuration,
4. add named-contract series equivalent to today’s multiple prices,
5. add adjusted-price derivation and persistence,
6. add daily normalization and backtest-facing read services,
7. add Redis caching only after the derivation and query boundaries are stable.

That ordering lets you prove the domain model before you optimize it.

## Practical recommendation

If you want a cleaner system than this repo, do not model the redesign around “whatever pandas object the current backtest happens to consume.”

Model it around these questions instead:

1. What is a raw market fact?
2. What is a roll-state decision?
3. What is a derived continuous series?
4. What must be versioned for reproducibility?

`Instrument` and `FuturesContract` are the right foundation, but the first complete design should also make explicit room for raw observations, named-contract roll state, and derived adjusted series.