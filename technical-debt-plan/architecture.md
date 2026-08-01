# Architecture

## Concerns

### Partial decoupling between simulation-facing data APIs and storage-specific assembly

Definition of terms in this codebase:

- Simulation-facing data API: the `simData` inheritance tree that the rest of the backtesting system is expected to call. For futures simulations in this repo, that path is `simData -> futuresSimData -> genericBlobUsingFuturesSimData -> csvFuturesSimData` or `dbFuturesSimData`.
- Storage-specific data classes: classes such as `csvFuturesAdjustedPricesData`, `parquetFuturesAdjustedPricesData`, and `mongoSpreadCostData` that know how to load a particular kind of data from a particular source.
- Composition layer: `dataBlob`, which instantiates storage-specific classes, wires them together, and exposes renamed attributes such as `db_futures_adjusted_prices`.

Observation:

The repo does have an abstraction boundary between simulation code and storage implementations, but the boundary is only partial. The simulation-facing API is relatively source-neutral once a `simData` object exists, yet the construction of that object is tightly coupled to storage source conventions.

Concrete examples:

- `csvFuturesSimData` explicitly chooses CSV-backed storage classes in its constructor.
- `dataBlob` decides how to instantiate classes by inspecting source prefixes such as `csv`, `mongo`, `parquet`, and `ib`.
- `dataBlob` relies on class naming conventions to rename storage-specific classes to neutral-looking attributes such as `db_futures_adjusted_prices`.

Why this may be technical debt:

- High-level simulation code is insulated from storage details only after the correct source-specific classes have already been selected.
- Adding a new source is not just a matter of implementing an interface; it also depends on naming conventions and `dataBlob` resolution rules.
- The system is therefore not fully decoupled from the data layer. It is better described as source-abstracted at the usage point, but source-aware at the composition point.

Clarification on inheritance:

If simulation data objects are thought of as specializations of a more general data object, that is accurate here. `csvFuturesSimData` does inherit from a parent chain: `csvFuturesSimData -> genericBlobUsingFuturesSimData -> futuresSimData -> simData`.

Documentation/API note:

The `csv_data_paths` API expects a dictionary whose keys are class names and whose values are project-style path strings. Example: `dict(csvFuturesAdjustedPricesData="private.system_name.adjusted_price_data")`.

If documentation or examples use a placeholder such as `key_name`, that is potentially misleading because `key_name` is not a meaningful key for this API. The actual key must be the concrete storage class name. The path belongs in the value position.

## Notes

## Possible Next Steps

- Check whether the current architecture should move from prefix-based source resolution toward explicit registration of storage providers.
- Review docs for `csv_data_paths` examples and replace generic placeholders with valid class-name keys.
