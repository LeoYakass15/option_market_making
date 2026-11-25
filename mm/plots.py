"""Charts of the market making simulation (saved as PNG)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, GREY = "#52514e", "#c3c2b7"
plt.rcParams.update({
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": GREY, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.6,
    "axes.titleweight": "bold", "axes.titlesize": 11, "font.size": 9, "lines.linewidth": 1.6,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
})


def plot_sample_day(path, file):
    """Quotes, client trades and inventory over one simulated day."""
    p = path.copy()
    for c in ["mid", "bid", "ask"]:
        p[c] = p[c] / 100                                   # EUR per option
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(p.index, p["mid"], color=INK, lw=1.2, label="Fair value (Black-Scholes mid)")
    ax1.plot(p.index, p["bid"], color=BLUE, lw=1, label="Our bid")
    ax1.plot(p.index, p["ask"], color=ORANGE, lw=1, label="Our ask")
    buys, sells = p[p["fill"] > 0], p[p["fill"] < 0]
    ax1.scatter(buys.index, buys["bid"], s=14, color=BLUE, zorder=3, label="Client sells to us")
    ax1.scatter(sells.index, sells["ask"], s=14, color=ORANGE, zorder=3, label="Client buys from us")
    ax1.set_ylabel("Call price (EUR per option)")
    ax1.set_title("One simulated day: Avellaneda-Stoikov quotes on a 1-month ATM call")
    ax1.legend(loc="upper left", fontsize=8, frameon=False, ncol=2)
    ax2.step(p.index, p["inventory"], where="post", color=AQUA)
    ax2.axhline(0, color=GREY, lw=1)
    ax2.set_ylabel("Inventory (lots)")
    ax2.set_xlabel("Minutes since the open")
    fig.tight_layout()
    fig.savefig(file, dpi=150)
    plt.close(fig)


def plot_skew(file):
    """Theoretical A-S quotes around the mid, against the inventory (at the open)."""
    from mm.market_maker import SPOT, STOCK_VOL, MATURITY, option_risk, quotes
    sigma = option_risk(SPOT, STOCK_VOL, MATURITY / 252, hedged=True)
    q = np.arange(-6, 7)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for time_left, style, when in [(1.0, "-", "at the open"), (0.25, "--", "1h30 before the close")]:
        bid, ask = quotes(0.0, q, sigma, time_left)
        ax.plot(q, bid / 100, style, color=BLUE, marker="o", ms=4, label=f"Bid {when}")
        ax.plot(q, ask / 100, style, color=ORANGE, marker="o", ms=4, label=f"Ask {when}")
    ax.axhline(0, color=INK, lw=1)
    ax.text(-6, 0.004, "fair value (mid)", color=INK, fontsize=8)
    ax.set_xlabel("Inventory (lots): long options on the right")
    ax.set_ylabel("Quote minus mid (EUR per option)")
    ax.set_title("Inventory skew: when long, both quotes move down to sell more and buy less")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper right")
    fig.tight_layout()
    fig.savefig(file, dpi=150)
    plt.close(fig)


def plot_pnl_distribution(runs, file):
    """Histogram of daily P&L for each strategy."""
    colors = [BLUE, ORANGE, AQUA]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    allp = np.concatenate([r["pnl"].values for r in runs.values()])
    bins = np.linspace(allp.min(), allp.max(), 60)
    for (name, r), c in zip(runs.items(), colors):
        ax.hist(r["pnl"], bins=bins, color=c, histtype="step", lw=2, label=f"{name} (mean {r['pnl'].mean():.0f}, st. dev. {r['pnl'].std():.0f})")
    ax.axvline(0, color=INK, lw=1)
    ax.set_xlabel("P&L per day (EUR)")
    ax.set_ylabel("Number of days")
    ax.set_title("Daily P&L over 1,000 simulated days")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(file, dpi=150)
    plt.close(fig)


def plot_inventory(runs, file):
    """Distribution of the inventory left at the close."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for (name, r), c, shift in zip(runs.items(), [BLUE, ORANGE], [-0.2, 0.2]):
        counts = r["end_inventory"].value_counts().sort_index()
        ax.bar(counts.index + shift, counts.values, width=0.4, color=c, label=name)
    ax.set_xlabel("Inventory at the close (lots)")
    ax.set_ylabel("Number of days")
    ax.set_title("The inventory skew keeps the book close to flat")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(file, dpi=150)
    plt.close(fig)


def plot_risk_aversion(table, sym, file):
    """Mean vs standard deviation of daily P&L for several risk aversions."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(table["St. dev. per day"], table["Mean P&L per day"], "-o", color=BLUE, ms=6,
            label="Avellaneda-Stoikov, different risk aversions")
    for g, row in table.iterrows():
        ax.annotate(f"γ = {g:g}", (row["St. dev. per day"], row["Mean P&L per day"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=8, color=INK)
    ax.scatter([sym["St. dev. per day"]], [sym["Mean P&L per day"]], s=60, color=ORANGE, zorder=3,
               label="Symmetric quotes (no skew)")
    ax.set_xlabel("Risk: st. dev. of daily P&L (EUR)")
    ax.set_ylabel("Mean P&L per day (EUR)")
    ax.set_title("Risk aversion: a little cuts risk for free, too much kills the profit")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(file, dpi=150)
    plt.close(fig)


def plot_pnl_split(table, file):
    """Where the money comes from: spread captured, inventory, hedging."""
    parts = ["Spread captured per day", "Inventory P&L per day", "Hedging cost per day", "Mean P&L per day"]
    labels = ["Spread captured", "Inventory (incl. adverse selection)", "Delta hedging cost", "Total P&L"]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = np.arange(len(table.columns))
    for i, (part, lab, c) in enumerate(zip(parts, labels, [AQUA, ORANGE, BLUE, INK])):
        ax.bar(x + (i - 1.5) * 0.2, table.loc[part], width=0.18, color=c, label=lab)
    ax.axhline(0, color=GREY, lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(table.columns)
    ax.set_ylabel("EUR per day (average)")
    ax.set_title("Where the P&L comes from")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(file, dpi=150)
    plt.close(fig)
