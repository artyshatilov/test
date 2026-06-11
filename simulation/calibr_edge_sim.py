"""
Calibr — Prediction-Market Edge & Calibration Simulation
========================================================

Companion to CALIBR.md. Quantifies the uncomfortable core claim of the concept:
in a prediction market, your realized edge is your *calibration*, and a plausible
"5-cent edge" is fragile to miscalibration, spread, and resolution risk.

We model a binary market priced by the book at q (YES), with a TRUE probability
pi. A strategy holds a *view* p and buys YES when p - q exceeds a threshold.

  realized edge per $1 contract = pi - q
  what the strategy THINKS it earns = p - q
  the gap (p - pi) is the calibration error, paid straight out of the edge.

We then layer real frictions (effective spread, resolution/oracle risk, capital
lockup) and show fractional-Kelly growth on a TRUE edge vs a FAKE (miscalibrated)
edge — the latter sizes you into the loss.

Run:  python3 calibr_edge_sim.py
All numbers are illustrative but internally consistent; tune the CONFIG block.
"""

from __future__ import annotations
import math
import numpy as np

rng = np.random.default_rng(11)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
N_MARKETS   = 200_000      # Monte-Carlo markets per scenario
STATED_EDGE = 0.05         # p - q : the edge the strategy believes it has (5 cents)
EFF_SPREAD  = 0.02         # effective half-spread haircut when you cross the book
RESOLVE_P   = 0.03         # prob a "won" position is lost to a bad/disputed resolution
HOLD_MONTHS = 3.0          # average capital lockup until resolution


def per_contract_pnl(p, q, pi, eff_spread=0.0, resolve_risk=0.0):
    """Expected $ PnL per $1 YES contract bought at q, paying 1 if event occurs.
    You pay q + spread; you receive 1 on a TRUE-and-cleanly-resolved outcome."""
    entry = q + eff_spread
    # event happens with prob pi; even then, resolve_risk wipes the payout
    win_prob = pi * (1.0 - resolve_risk)
    return win_prob * 1.0 - entry          # E[payout] - cost


# ---------------------------------------------------------------------------
# 1. The core identity: realized edge = stated edge - calibration error
# ---------------------------------------------------------------------------
def section_calibration():
    print("=" * 78)
    print("1. REALIZED EDGE = STATED EDGE - CALIBRATION ERROR  (per $1 contract)")
    print("=" * 78)
    print("Strategy believes p - q = +{:.0%}. We vary how wrong p is vs the truth pi.".format(STATED_EDGE))
    print(f"(no frictions yet)\n")
    q = 0.50
    p = q + STATED_EDGE                      # the view: 0.55
    print(f"  market q = {q:.2f}   stated view p = {p:.2f}   (stated edge = {p-q:+.2f})\n")
    print(f"  {'calib error (p-pi)':>20} | {'true pi':>8} | {'realized edge (pi-q)':>20} | verdict")
    print("  " + "-" * 74)
    for calib_err in (-0.03, 0.00, 0.02, 0.05, 0.08):
        pi = p - calib_err                   # if you're overconfident, pi < p
        realized = pi - q
        verdict = "edge survives" if realized > 0 else "EDGE FLIPS NEGATIVE"
        print(f"  {calib_err:>+20.2f} | {pi:>8.2f} | {realized:>+20.2f} | {verdict}")
    print("\n  Read: a +5c stated edge is erased by a 5-point overconfidence (p-pi=0.05),")
    print("  and goes negative beyond it. Overconfident models don't just earn less.\n")


# ---------------------------------------------------------------------------
# 2. Add real frictions: spread + resolution risk
# ---------------------------------------------------------------------------
def section_frictions():
    print("=" * 78)
    print("2. WHAT'S LEFT AFTER SPREAD + RESOLUTION RISK")
    print("=" * 78)
    q = 0.50
    p = q + STATED_EDGE
    print(f"  market q={q:.2f}, view p={p:.2f}, eff_spread={EFF_SPREAD:.2f}, "
          f"resolve_risk={RESOLVE_P:.0%}\n")
    print(f"  {'true pi':>8} | {'gross edge':>11} | {'- spread':>9} | {'- resolve':>10} | {'net/contract':>13}")
    print("  " + "-" * 70)
    for pi in (0.55, 0.53, 0.51, 0.50):
        gross = pi - q
        net_spread = (pi) - (q + EFF_SPREAD)
        net = per_contract_pnl(p, q, pi, EFF_SPREAD, RESOLVE_P)
        print(f"  {pi:>8.2f} | {gross:>+11.3f} | {net_spread:>+9.3f} | "
              f"{net:>+10.3f} | {net:>+13.3f}")
    # annualization sanity
    best = per_contract_pnl(p, q, 0.55, EFF_SPREAD, RESOLVE_P)
    apr = (best / (q + EFF_SPREAD)) * (12.0 / HOLD_MONTHS)
    print(f"\n  If well-calibrated (pi=0.55): net ≈ {best:+.3f}/contract on {q+EFF_SPREAD:.2f} risked")
    print(f"  → ~{best/(q+EFF_SPREAD):+.1%} per trade, ~{apr:+.0%} APR at {HOLD_MONTHS:.0f}-mo lockup (GROSS of fails).")
    print("  Spread + resolution risk routinely halve a headline edge.\n")


# ---------------------------------------------------------------------------
# 3. Fractional Kelly: true edge vs fake (miscalibrated) edge
# ---------------------------------------------------------------------------
def kelly_growth(p_true, q, kelly_frac, n_bets, n_paths=4000):
    """Simulate bankroll compounding when sizing by fractional Kelly on a binary
    YES bet at price q, true win prob p_true. Stake fraction f* = edge/odds * frac."""
    b = (1.0 - q) / q                        # net odds received on a win
    edge_for_kelly = (q + STATED_EDGE)       # we SIZE as if p = q+stated edge ...
    p_believed = min(0.999, edge_for_kelly)
    f_star = max(0.0, (p_believed * (b + 1) - 1) / b)   # Kelly using BELIEVED p
    f = f_star * kelly_frac
    f = min(f, 0.5)                           # never stake >50% (sanity cap)

    wealth = np.ones(n_paths)
    for _ in range(n_bets):
        win = rng.random(n_paths) < p_true    # outcomes use the TRUE prob
        # bet fraction f of bankroll; win pays b*f, loss costs f
        wealth *= np.where(win, 1 + f * b, 1 - f)
    return wealth, f


def section_kelly():
    print("=" * 78)
    print("3. FRACTIONAL KELLY: A TRUE EDGE COMPOUNDS, A FAKE EDGE SIZES INTO RUIN")
    print("=" * 78)
    q = 0.50
    n_bets = 100
    print(f"  q={q:.2f}, sizing as if p={q+STATED_EDGE:.2f} (believed +{STATED_EDGE:.0%}), "
          f"100 sequential bets, 1/4 Kelly\n")
    print(f"  {'scenario':>26} | {'true p':>7} | {'stake f':>8} | {'median x':>9} | {'P(down 50%)':>11}")
    print("  " + "-" * 74)
    scenarios = [
        ("genuine +5% edge",      q + 0.05),
        ("half-real (+2.5%)",     q + 0.025),
        ("no edge (efficient)",   q + 0.00),
        ("anti-edge (overconf.)", q - 0.02),
    ]
    for name, p_true in scenarios:
        wealth, f = kelly_growth(p_true, q, kelly_frac=0.25, n_bets=n_bets)
        med = np.median(wealth)
        p_ruin = float(np.mean(wealth < 0.5))
        print(f"  {name:>26} | {p_true:>7.3f} | {f:>8.3f} | {med:>9.2f} | {p_ruin:>11.1%}")
    print("\n  Same sizing logic; only calibration differs. Kelly rewards a real edge and")
    print("  punishes a believed-but-false one — sizing is only as good as your view.\n")


# ---------------------------------------------------------------------------
# 4. Portfolio Monte-Carlo: a believable strategy across many markets
# ---------------------------------------------------------------------------
def section_portfolio():
    print("=" * 78)
    print("4. PORTFOLIO MONTE-CARLO  (many markets, a realistic mixed book)")
    print("=" * 78)
    print("  Each market: q ~ U(0.2,0.8); the strat's view p = q + signal. We test a")
    print("  GOOD forecaster (small real edge, well-calibrated) vs an OVERCONFIDENT one.\n")
    print(f"  {'forecaster':>16} | {'mean/contract':>13} | {'win rate':>9} | {'% markets +EV':>13}")
    print("  " + "-" * 64)

    q = rng.uniform(0.2, 0.8, N_MARKETS)
    signal = rng.normal(0.0, 0.06, N_MARKETS)          # the strat's claimed edge per market
    p = np.clip(q + signal, 0.01, 0.99)

    for name, calib_bias, noise in [
        ("well-calibrated", 0.00, 0.03),               # pi ≈ p, small noise
        ("overconfident",   0.04, 0.03),               # pi systematically below p
    ]:
        pi = np.clip(p - calib_bias - rng.normal(0, noise, N_MARKETS), 0.01, 0.99)
        # only TAKE markets where believed edge clears threshold + costs
        take = (p - q) > (EFF_SPREAD + 0.01)
        entry = q[take] + EFF_SPREAD
        outcome = (rng.random(take.sum()) < pi[take]) & (rng.random(take.sum()) > RESOLVE_P)
        pnl = outcome.astype(float) - entry
        mean = pnl.mean()
        winr = outcome.mean()
        ev_pos = float(np.mean((pi[take] - (q[take] + EFF_SPREAD)) > 0))
        print(f"  {name:>16} | {mean:>+13.4f} | {winr:>9.1%} | {ev_pos:>13.1%}")
    print("\n  Same signals, same selection rule. A 4-point calibration bias turns a")
    print("  profitable book into a losing one — even though the strategy 'looks' identical.\n")


def main():
    print("\nCALIBR — PREDICTION-MARKET EDGE & CALIBRATION SIMULATION")
    print("Companion to CALIBR.md §5-§6. All figures illustrative; tune CONFIG.\n")
    section_calibration()
    section_frictions()
    section_kelly()
    section_portfolio()
    print("=" * 78)
    print("TAKEAWAY: realized edge = calibration, not confidence. Spread + resolution")
    print("risk halve headline edges, and Kelly sizing amplifies whichever you actually")
    print("have. The product's job is to MEASURE this honestly, not to promise alpha.")
    print("=" * 78)


if __name__ == "__main__":
    main()
