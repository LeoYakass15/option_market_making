"""Unit tests (pytest). Run with: python -m pytest -q"""
import numpy as np

from mm.black_scholes import call_delta, call_price, call_vega
from mm.market_maker import quotes, simulate_day


def test_black_scholes_atm_call():
    # ATM call, 20% vol, 1 year: about 0.4 * S * vol = 7.97
    assert np.isclose(call_price(100, 100, 0.2, 1.0), 7.9656, atol=1e-3)
    assert 0.5 < call_delta(100, 100, 0.2, 1.0) < 0.6


def test_vega_matches_a_one_point_bump():
    bump = call_price(100, 100, 0.21, 0.25) - call_price(100, 100, 0.20, 0.25)
    assert np.isclose(call_vega(100, 100, 0.2, 0.25), bump, rtol=0.01)


def test_flat_book_quotes_are_centred_on_the_mid():
    bid, ask = quotes(200.0, 0, sigma=10.0, time_left=1.0)
    assert np.isclose(200 - bid, ask - 200)


def test_long_book_moves_both_quotes_down():
    bid0, ask0 = quotes(200.0, 0, 10.0, 1.0)
    bid, ask = quotes(200.0, 5, 10.0, 1.0)
    assert bid < bid0 and ask < ask0
    assert np.isclose(ask - bid, ask0 - bid0)          # the skew does not change the spread


def test_spread_is_wider_when_risk_is_higher():
    b1, a1 = quotes(200.0, 0, 10.0, 1.0)
    b2, a2 = quotes(200.0, 0, 50.0, 1.0)
    assert a2 - b2 > a1 - b1


def test_pnl_split_adds_up_and_is_reproducible():
    d1 = simulate_day(seed=1)
    d2 = simulate_day(seed=1)
    assert d1["pnl"] == d2["pnl"]
    assert np.isclose(d1["spread_pnl"] + d1["hedge_cost"] + d1["inventory_pnl"], d1["pnl"])
