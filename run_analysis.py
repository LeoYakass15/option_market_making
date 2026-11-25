"""Avellaneda-Stoikov market making on a listed call option. Run: python run_analysis.py

Simulates 1,000 trading days for each strategy and saves charts and tables in results/.
"""
import os

import pandas as pd

from mm import plots
from mm.market_maker import run_days, simulate_day, summary

OUT = "results"
N_DAYS = 1000
pd.set_option("display.width", 160)
pd.set_option("display.precision", 1)
pd.set_option("display.max_columns", 10)
os.makedirs(OUT, exist_ok=True)

# 1. One day in detail
day = simulate_day(seed=3, keep_path=True)
day["path"].to_csv(f"{OUT}/sample_day.csv")
print(f"Sample day: {day['trades']} trades, P&L {day['pnl']:.0f} EUR, closing inventory {day['end_inventory']} lots")

# 2. Three strategies on the same 1,000 simulated days
runs = {
    "A-S + delta hedge": run_days(N_DAYS, skew=True, hedged=True),
    "Symmetric + delta hedge": run_days(N_DAYS, skew=False, hedged=True),
    "A-S, no hedge": run_days(N_DAYS, skew=True, hedged=False),
}
table = pd.DataFrame({name: summary(r) for name, r in runs.items()})
print("\n== Daily results, EUR (1 lot = 100 options) ==")
print(table)
table.to_csv(f"{OUT}/strategy_comparison.csv")

# 3. Risk aversion
gammas = [0.0005, 0.001, 0.003, 0.01, 0.03, 0.1]
risk = pd.DataFrame({g: summary(run_days(500, gamma=g)) for g in gammas}).T
risk.index.name = "gamma"
cols = ["Mean P&L per day", "St. dev. per day", "P&L / risk (daily)", "Trades per day",
        "Avg max |inventory| in the day (lots)"]
print("\n== Risk aversion (A-S + delta hedge, 500 days each) ==")
print(risk[cols])
risk[cols].to_csv(f"{OUT}/risk_aversion.csv")

# 4. Charts
plots.plot_sample_day(day["path"], f"{OUT}/01_sample_day.png")
plots.plot_skew(f"{OUT}/02_inventory_skew.png")
plots.plot_pnl_distribution(runs, f"{OUT}/03_pnl_distribution.png")
plots.plot_inventory({k: runs[k] for k in list(runs)[:2]}, f"{OUT}/04_closing_inventory.png")
plots.plot_pnl_split(table, f"{OUT}/05_pnl_split.png")
plots.plot_risk_aversion(risk, table["Symmetric + delta hedge"], f"{OUT}/06_risk_aversion.png")
print(f"\nCharts and tables saved in {OUT}/")
