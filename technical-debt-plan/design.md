# Design

## Concerns

### `Config` exposes mutable nested dictionaries directly

Definition of terms in this codebase:

- `Config`: the object defined in `sysdata/config/configdata.py` that stores top-level configuration values as attributes, for example `config.instrument_div_multiplier` or `config.volatility_calculation`.
- Nested config value: a value inside a top-level config attribute that is itself structured, for example the dictionary stored in `config.volatility_calculation`.
- Direct exposure: external code mutates the real nested dictionary object instead of going through a dedicated `Config` API.

Observation:

The mixed usage pattern in the docs is confusing:

```python
config.volatility_calculation = dict(days=20)
config.volatility_calculation['days'] = 20
```

Minor docs issue: `config.volatility_calculation = {'days': 20}` is clearer than `dict(days=20)`.

Larger design issue: `Config` stores nested sections as plain dictionaries and exposes them directly. That forces callers to mix `config.foo` with `config.foo['bar']`. The awkward API comes from the implementation, not just the docs.

Why this may be technical debt:

- Replacing a nested section can drop expected keys and interfere with defaults merging.
- The interface mixes attribute access at the top level with raw dictionary mutation below that.
- Callers need to understand internal storage details to change config safely, which is weak encapsulation.

Concrete code behavior behind the observation:

- In `sysdata/config/configdata.py`, `_create_config_from_dict()` assigns raw dictionary values directly with `setattr(self, keyname, config_object[keyname])`.
- Nested sections such as `volatility_calculation` remain plain dictionaries.
- Downstream code such as `systems/rawdata.py` expects a dictionary and uses dictionary operations like `.pop()`.

Assessment:

The observation is substantially correct. The API is lightweight, but that flexibility comes from exposing internal mutable state rather than encapsulating nested config sections.

Possible design directions:

- Keep the current dictionary-based model, but document it explicitly as a lightweight attribute bag.
- Wrap nested sections in a small config-section object so callers can use a consistent access style, for example `config.volatility_calculation.days`.
- Prevent whole-object reassignment for known structured sections, or require controlled updates through `Config` methods.

### Saving config is split across `Config` and file path utilities

Definition of terms in this codebase:

- Config serialization: turning a `Config` object into plain YAML data.
- Path resolution: converting project-specific names such as `private.this_system_name.config.yaml` into a real filesystem path.

Observation:

The docs show config saving like this:

```python
filename = resolve_path_and_filename_for_package("private.this_system_name.config.yaml")
with open(filename, 'w') as outfile:
	outfile.write(yaml.dump(my_config, default_flow_style=True))
```

But `Config` already has a `save(filename)` method in `sysdata/config/configdata.py`, and the codebase uses it in places such as `sysproduction/data/backtest.py`.

Why this may be technical debt:

- The public behavior of "save this config to YAML" is split between `Config` and `syscore.fileutils`.
- Callers have to know both how to serialize the object and how to resolve project-style filenames.
- The docs bypass the class API and rely on generic `yaml.dump(my_config)`, even though `Config` is not a dictionary and already knows how to save itself.

Assessment:

This looks like a real design inconsistency, not just a docs issue. Centralized path resolution can make sense at the project level, but `Config.save()` should probably accept the same filename formats that `Config(...)` already accepts and resolve them internally.

Possible design directions:

- Make `Config.save()` accept project-style dotted paths and call `resolve_path_and_filename_for_package()` internally.
- Update docs to use `my_config.save(...)` instead of manually opening files and calling `yaml.dump()`.
- Keep path resolution centralized, but move that detail behind the `Config` save API.

## Notes

## Possible Next Steps

- Review whether `Config` is intended to be a thin data bag or a real encapsulating object, and document that choice clearly.
- If the current design is kept, update docs to explain that nested sections are plain dictionaries by design.
- If the design is changed, identify a migration path for code that currently expects dictionary methods such as `.pop()` on nested config sections.
