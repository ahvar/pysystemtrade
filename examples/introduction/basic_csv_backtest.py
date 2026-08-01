"""A guided, reproducible backtest using pysystemtrade's bundled CSV data.

Run this example from the repository root:

    envs/bin/python examples/introduction/basic_csv_backtest.py

Optionally save the portfolio account curve:

    envs/bin/python examples/introduction/basic_csv_backtest.py \
        --plot-file /tmp/pysystemtrade-account-curve.png

The example deliberately constructs the data, configuration, and system
separately.  That is a little more verbose than simply calling
``futures_system()``, but makes their responsibilities easier to see.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from sysdata.config.configdata import Config
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from systems.provided.futures_chapter15.basesystem import futures_system

CONFIG_FILE = "systems.provided.futures_chapter15.futuresconfig.yaml"
INSTRUMENT = "SOFR"


def print_section(title: str) -> None:
    """Print a readable section heading without adding another dependency."""
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def show_source_map() -> None:
    """Point from the important runtime objects to their definitions."""
    print_section("1. Essential objects and their definitions")
    print(
        "The Chapter 15 factory wires data, config, and stages into a System:\n"
        "  systems/provided/futures_chapter15/basesystem.py  futures_system()\n\n"
        "Core containers:\n"
        "  sysdata/sim/csv_futures_sim_data.py              csvFuturesSimData\n"
        "  sysdata/config/configdata.py                     Config\n"
        "  systems/basesystem.py                            System\n\n"
        "Backtest stages, in calculation order:\n"
        "  systems/rawdata.py                               RawData\n"
        "  systems/forecasting.py                           Rules\n"
        "  systems/forecast_scale_cap.py                    ForecastScaleCap\n"
        "  systems/forecast_combine.py                      ForecastCombine\n"
        "  systems/positionsizing.py                        PositionSizing\n"
        "  systems/portfolio.py                             Portfolios\n"
        "  systems/accounts/accounts_stage.py               Account\n\n"
        "The System constructor attaches each stage using its stage name, which is\n"
        "why the objects are accessed as system.rawdata, system.rules,\n"
        "system.forecastScaleCap, system.combForecast, system.positionSize,\n"
        "system.portfolio, and system.accounts."
    )


def show_csv_inputs() -> None:
    """Describe the CSV collections consumed by csvFuturesSimData."""
    print_section("2. CSV inputs")
    print(
        "csvFuturesSimData combines these bundled data collections:\n"
        "  data/futures/adjusted_prices_csv/  back-adjusted price per instrument\n"
        "  data/futures/multiple_prices_csv/  price/carry contracts for carry rules\n"
        "  data/futures/csvconfig/instrumentconfig.csv  point size and currency\n"
        "  data/futures/csvconfig/spreadcosts.csv      transaction-cost input\n"
        "  data/futures/csvconfig/rollconfig.csv       futures roll conventions\n"
        "  data/futures/fx_prices_csv/                 conversion to base currency"
    )


def load_and_show_data() -> csvFuturesSimData:
    """Load the default CSV data object and perform basic integrity checks."""
    print_section("3. Load and inspect CSV data")
    data = csvFuturesSimData()
    instruments = data.get_instrument_list()
    prices = data.daily_prices(INSTRUMENT)

    if not instruments:
        raise RuntimeError("The bundled CSV data contains no instruments")
    if prices.empty:
        raise RuntimeError(f"No daily prices were loaded for {INSTRUMENT}")

    print(f"CSV data object: {data}")
    print(f"Available adjusted-price instruments: {len(instruments)}")
    print(f"First ten: {instruments[:10]}")
    print(f"\nLatest {INSTRUMENT} daily prices:\n{prices.tail(3)}")
    return data


def load_and_show_config() -> Config:
    """Load Chapter 15 YAML and display the settings most useful to beginners."""
    print_section("4. Load and inspect configuration")
    print(
        "Precedence is: backtest YAML, then private/private_config.yaml, then "
        "sysdata/config/defaults.yaml. Lower-priority sources only fill missing "
        "values. A missing private config is harmless in simulation mode."
    )

    config = Config(CONFIG_FILE)
    print(f"\nConfiguration source: {CONFIG_FILE}")
    print("Project-wide fallback values: sysdata/config/defaults.yaml")
    print(f"Trading rules defined: {list(config.trading_rules)}")
    print(f"Rules used by forecast_weights: {list(config.forecast_weights)}")
    print(f"Forecast weights: {config.forecast_weights}")
    print(f"Forecast diversification multiplier: {config.forecast_div_multiplier}")
    print(f"Notional capital: {config.notional_trading_capital:,.0f}")
    print(f"Annual percentage volatility target: {config.percentage_vol_target}%")
    print(f"Base currency: {config.base_currency}")
    print(f"Instrument weights: {config.instrument_weights}")
    print(f"Instrument diversification multiplier: {config.instrument_div_multiplier}")
    return config


def run_backtest(data: csvFuturesSimData, config: Config):
    """Build the system and expose representative results from every stage."""
    print_section("5. Construct the System and inspect its calculation chain")
    system = futures_system(data=data, config=config)
    instruments = system.get_instrument_list()

    expected = set(config.instrument_weights)
    if set(instruments) != expected:
        raise RuntimeError(
            f"System instruments {instruments} do not match configured weights {expected}"
        )

    daily_prices = system.rawdata.get_daily_prices(INSTRUMENT)
    raw_forecast = system.rules.get_raw_forecast(INSTRUMENT, "ewmac16_64")
    capped_forecast = system.forecastScaleCap.get_capped_forecast(
        INSTRUMENT, "ewmac16_64"
    )
    combined_forecast = system.combForecast.get_combined_forecast(INSTRUMENT)
    subsystem_position = system.positionSize.get_subsystem_position(INSTRUMENT)
    notional_position = system.portfolio.get_notional_position(INSTRUMENT)

    for label, value in (
        ("daily prices", daily_prices),
        ("raw forecast", raw_forecast),
        ("scaled and capped forecast", capped_forecast),
        ("combined forecast", combined_forecast),
        ("subsystem position", subsystem_position),
        ("notional position", notional_position),
    ):
        if value.empty:
            raise RuntimeError(f"The {label} result is empty")

    print(f"System universe: {instruments}")
    print(
        "Calculation flow: raw data -> rule forecast -> scale/cap -> combine -> "
        "position size -> portfolio -> account P&L"
    )
    print(f"\n{INSTRUMENT} daily prices:\n{daily_prices.tail(3)}")
    print(f"\n{INSTRUMENT} raw EWMAC forecast:\n{raw_forecast.dropna().tail(3)}")
    print(
        f"\n{INSTRUMENT} scaled and capped EWMAC forecast:\n"
        f"{capped_forecast.dropna().tail(3)}"
    )
    print(f"\n{INSTRUMENT} combined forecast:\n{combined_forecast.dropna().tail(3)}")
    print(
        "This combined forecast is not just ewmac16_64. In the Chapter 15 config, "
        "SOFR combines the active weighted forecasts ewmac16_64, ewmac32_128, "
        "ewmac64_256, and carry."
    )
    print(
        f"\n{INSTRUMENT} volatility-scaled subsystem position:\n{subsystem_position.tail(3)}"
    )
    print(
        f"\n{INSTRUMENT} portfolio-weighted notional position:\n{notional_position.tail(3)}"
    )

    print_section("6. Account stage: portfolio performance")
    portfolio = system.accounts.portfolio()
    stats = portfolio.stats()
    stats_text = str(stats).lower()
    if "sharpe" not in stats_text or "drawdown" not in stats_text:
        raise RuntimeError("Portfolio statistics lack Sharpe or drawdown measures")
    print(stats)

    return system, portfolio


def save_account_curve(portfolio, plot_file: Path | None) -> None:
    """Save, rather than interactively block on, an optional account-curve plot."""
    if plot_file is None:
        return

    plot_file = plot_file.expanduser().resolve()
    plot_file.parent.mkdir(parents=True, exist_ok=True)
    axes = portfolio.curve().plot(title="pysystemtrade Chapter 15 account curve")
    axes.set_xlabel("Date")
    axes.set_ylabel("Cumulative P&L")
    axes.figure.tight_layout()
    axes.figure.savefig(plot_file)
    print(f"\nSaved account curve to {plot_file}")


def main(
    plot_file: Annotated[
        Path | None,
        typer.Option(help="Optional PNG/PDF/SVG path for the portfolio account curve."),
    ] = None,
) -> None:
    """Run a guided Chapter 15 backtest using the bundled futures CSV files."""
    # pysystemtrade defaults to DEBUG simulation logging. Keep this teaching
    # example readable while retaining warnings and errors.
    logging.getLogger().setLevel(logging.WARNING)

    show_source_map()
    show_csv_inputs()
    data = load_and_show_data()
    config = load_and_show_config()
    _, portfolio = run_backtest(data, config)
    save_account_curve(portfolio, plot_file)


if __name__ == "__main__":
    typer.run(main)
