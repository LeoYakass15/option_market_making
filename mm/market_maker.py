"""One trading day of a market maker quoting a 1-month at-the-money call.

Everything is per lot of 100 options. The market maker:
- quotes a bid and an ask around the option's fair value (Black-Scholes mid),
- gets hit at random: the further its quote from the mid, the fewer trades
  (Poisson arrivals, intensity A * exp(-k * distance)),
- can delta-hedge its option inventory with the stock after every trade,
- suffers adverse selection: after a client buys, implied vol ticks up (and
  down after a client sells), so part of the spread is lost straight away.

Quotes follow Avellaneda and Stoikov (2008):
    reservation price  r = mid - q * gamma * sigma^2 * (T - t)
    total spread         = gamma * sigma^2 * (T - t) + (2 / gamma) * ln(1 + gamma / k)
q = inventory in lots, gamma = risk aversion, sigma = volatility of the option
price (EUR per lot per day) for the risk the market maker still carries.
"""
import numpy as np
import pandas as pd

from mm.black_scholes import call_delta, call_price, call_vega

LOT = 100                # options per lot
SPOT = 100.0             # stock price at the open
STRIKE = 100.0           # at-the-money call
MATURITY = 21            # option maturity in trading days (1 month)
STOCK_VOL = 0.20         # realised and implied vol, 20%
VOL_OF_VOL = 1.5         # implied vol moves by 1.5 vol points per day (1 st. dev.)
STEPS = 390              # one step per minute over a 6.5 hour day
A = 150.0                # trades per day on each side for a quote at the mid
K = 0.2                  # fill decay per EUR of distance to the mid (per lot)
GAMMA = 0.01             # risk aversion
ADVERSE = 0.1            # implied vol moves 0.1 pt against us after each client trade
HEDGE_COST = 0.0001      # 1 bp of the stock amount traded for each delta hedge


def option_risk(spot, vol, t_years, hedged):
    """Daily volatility of the option price per lot (EUR) left after hedging."""
    vega = call_vega(spot, STRIKE, vol, t_years) * LOT
    vega_risk = vega * VOL_OF_VOL
    if hedged:
        return vega_risk
    delta_risk = call_delta(spot, STRIKE, vol, t_years) * LOT * spot * STOCK_VOL / np.sqrt(252)
    return np.sqrt(vega_risk ** 2 + delta_risk ** 2)


def quotes(mid, q, sigma, time_left, gamma=GAMMA, k=K, skew=True):
    """Avellaneda-Stoikov bid and ask. skew=False keeps the same spread centred on the mid."""
    spread = gamma * sigma ** 2 * time_left + (2 / gamma) * np.log(1 + gamma / k)
    centre = mid - q * gamma * sigma ** 2 * time_left if skew else mid
    return centre - spread / 2, centre + spread / 2


def simulate_day(seed, gamma=GAMMA, skew=True, hedged=True, keep_path=False):
    """Simulate one day. Returns a dict of results (and the minute-by-minute path)."""
    rng = np.random.default_rng(seed)
    dt = 1 / STEPS                           # in days
    spot, vol = SPOT, STOCK_VOL
    q, cash, shares = 0, 0.0, 0.0            # option lots, EUR, stocks held
    spread_pnl, hedge_cost, trades = 0.0, 0.0, 0
    path = []
    inventory_seen = [0]

    for i in range(STEPS):
        t_years = (MATURITY - i * dt) / 252
        mid = call_price(spot, STRIKE, vol, t_years) * LOT
        sigma = option_risk(spot, vol, t_years, hedged)
        bid, ask = quotes(mid, q, sigma, 1 - i * dt, gamma, K, skew)

        # Clients trade with us at random (same random numbers for every strategy)
        u_bid, u_ask = rng.random(2)
        fill = 0
        if u_bid < A * np.exp(-K * (mid - bid)) * dt:   # a client sells to us
            q += 1
            cash -= bid
            spread_pnl += mid - bid
            trades += 1
            fill += 1
            vol -= ADVERSE / 100                         # sellers push vol down
        if u_ask < A * np.exp(-K * (ask - mid)) * dt:   # a client buys from us
            q -= 1
            cash += ask
            spread_pnl += ask - mid
            trades += 1
            fill -= 1
            vol += ADVERSE / 100                         # buyers push vol up

        inventory_seen.append(q)

        # Delta hedge: hold -delta shares per option we own
        if hedged:
            target = -q * LOT * call_delta(spot, STRIKE, vol, t_years)
            cash -= (target - shares) * spot
            cost = abs(target - shares) * spot * HEDGE_COST
            cash -= cost
            hedge_cost += cost
            shares = target

        if keep_path:
            path.append({"minute": i, "spot": spot, "vol": vol * 100, "mid": mid,
                         "bid": bid, "ask": ask, "fill": fill, "inventory": q})

        # Market moves: stock (lognormal) and implied vol (random walk)
        z_spot, z_vol = rng.standard_normal(2)
        spot *= np.exp(-0.5 * STOCK_VOL ** 2 * dt / 252 + STOCK_VOL * np.sqrt(dt / 252) * z_spot)
        vol += VOL_OF_VOL / 100 * np.sqrt(dt) * z_vol

    # End of day: mark the book at the close
    t_years = (MATURITY - 1) / 252
    close_mid = call_price(spot, STRIKE, vol, t_years) * LOT
    pnl = cash + q * close_mid + shares * spot
    out = {"pnl": pnl, "spread_pnl": spread_pnl, "hedge_cost": -hedge_cost,
           "inventory_pnl": pnl - spread_pnl + hedge_cost,
           "trades": trades, "end_inventory": q,
           "max_inventory": max(abs(x) for x in inventory_seen)}
    if keep_path:
        out["path"] = pd.DataFrame(path).set_index("minute")
    return out


def run_days(n_days, gamma=GAMMA, skew=True, hedged=True, first_seed=0):
    """Simulate n_days independent days. Seed d gives the same market for every strategy."""
    rows = [simulate_day(first_seed + d, gamma, skew, hedged) for d in range(n_days)]
    return pd.DataFrame(rows)


def summary(days):
    """Daily P&L statistics of a run, in EUR."""
    pnl = days["pnl"]
    return pd.Series({
        "Mean P&L per day": pnl.mean(),
        "St. dev. per day": pnl.std(),
        "P&L / risk (daily)": pnl.mean() / pnl.std(),
        "Worst day": pnl.min(),
        "Spread captured per day": days["spread_pnl"].mean(),
        "Hedging cost per day": days["hedge_cost"].mean(),
        "Inventory P&L per day": days["inventory_pnl"].mean(),
        "Trades per day": days["trades"].mean(),
        "Avg |inventory| at close (lots)": days["end_inventory"].abs().mean(),
        "Avg max |inventory| in the day (lots)": days["max_inventory"].mean(),
        "Losing days (%)": 100 * (pnl < 0).mean(),
    })
