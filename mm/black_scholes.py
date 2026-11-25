"""Black-Scholes price and greeks of a European call (no rates, no dividends)."""
from math import erf, sqrt, log, exp, pi


def norm_cdf(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def norm_pdf(x):
    return exp(-0.5 * x * x) / sqrt(2 * pi)


def d1(spot, strike, vol, t):
    return (log(spot / strike) + 0.5 * vol ** 2 * t) / (vol * sqrt(t))


def call_price(spot, strike, vol, t):
    a = d1(spot, strike, vol, t)
    b = a - vol * sqrt(t)
    return spot * norm_cdf(a) - strike * norm_cdf(b)


def call_delta(spot, strike, vol, t):
    return norm_cdf(d1(spot, strike, vol, t))


def call_vega(spot, strike, vol, t):
    """Change in price for +1 vol point (0.01)."""
    return spot * norm_pdf(d1(spot, strike, vol, t)) * sqrt(t) * 0.01
