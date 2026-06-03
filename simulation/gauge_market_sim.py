"""
veHOUSE gauge & bribe-market simulation
=======================================
Models the second token-demand engine: lock $HOUSE -> veHOUSE -> vote to direct
LP-incentive emissions and bet-capacity to specific games. Game operators/devs
BRIBE veHOUSE voters to win that direction (Curve/Convex dynamic), because deeper
incentivised liquidity = more bet capacity = more volume = more of their revenue.

Outputs:
  1) veHOUSE yield decomposition + the EQUILIBRIUM lock rate (how much supply gets
     locked, hence how much float/sell-pressure is removed -> feeds the flip date).
  2) The bribe market: bribe efficiency, what bribes add to locker APR, and the
     briber's break-even (when is paying a bribe +EV for a game operator?).

Run:  python3 gauge_market_sim.py   (writes figures/07_gauge.png)
"""
from __future__ import annotations
import numpy as np
from tokenomics_sim import SUPPLY, circulating_at

# ------------------------------ assumptions --------------------------------
EDGE, TURNOVER     = 0.02, 18
PROTOCOL_TAKE      = 0.15
VE_FEE_SHARE       = 0.20      # 20% of protocol take (the non-buyback slice) -> veHOUSE
EMIT_TO_LOCKERS_YR = 0.06      # 6% of supply/yr emitted to veHOUSE lockers (yr ~2-3 rate)
TARGET_VE_APR      = 0.20      # capital locks until APR compresses to ~20%
BRIBE_EFFICIENCY   = 1.4       # $ of emissions a briber can direct per $1 of bribe (Curve-like)


def section_ve_yield_and_lockrate():
    print("=" * 80)
    print("1) veHOUSE LOCK RATE — and how much of it is REAL vs reflexive emissions")
    print("=" * 80)
    print(f"  Locker rewards = REAL fee share ({VE_FEE_SHARE:.0%} of protocol take) +")
    print(f"  emissions ({EMIT_TO_LOCKERS_YR:.0%}/yr of supply) + bribes. Capital locks until")
    print(f"  veHOUSE APR compresses to ~{TARGET_VE_APR:.0%}. We split the lock by SOURCE.\n")
    print(f"  {'TVL':>9}{'FDV(8x)':>10}{'fee$/yr':>9}{'emit$/yr':>10}{'bribe$/yr':>11}"
          f"{'%FDV lock(real)':>16}{'%FDV lock(total)':>17}")
    print("  " + "-" * 82)
    for tvl in [50e6, 200e6, 500e6]:
        ggr   = EDGE * TURNOVER * tvl
        fdv   = 8 * ggr
        price = fdv / circulating_at(30)
        fee   = VE_FEE_SHARE * PROTOCOL_TAKE * ggr            # real yield (sustainable)
        emit  = EMIT_TO_LOCKERS_YR * SUPPLY * price           # emissions (reflexive)
        bribe = 0.3e6 * (tvl / 50e6)                          # thin, see section 2
        lock_real  = fee / TARGET_VE_APR
        lock_total = (fee + emit + bribe) / TARGET_VE_APR
        print(f"  {'$'+f'{tvl/1e6:.0f}M':>9}{'$'+f'{fdv/1e6:.0f}M':>10}"
              f"{'$'+f'{fee/1e6:.1f}M':>9}{'$'+f'{emit/1e6:.1f}M':>10}"
              f"{'$'+f'{bribe/1e6:.1f}M':>11}{lock_real/fdv*100:>14.0f}%"
              f"{min(100,lock_total/fdv*100):>16.0f}%")
    print()
    print("  INSIGHT: the headline 'lots of supply locked' is mostly EMISSIONS-driven —")
    print("  i.e. you lock to earn inflation, which is reflexive and evaporates when")
    print("  emissions taper. The SUSTAINABLE lock (funded by real fee share) is only a")
    print("  few % of FDV until GGR is large, because gambling fee share per $ of FDV is")
    print("  thin. veHOUSE removes float and helps the flip date, but do not mistake")
    print("  emissions-bought locks for durable demand — re-underwrite them at lower")
    print("  emissions and check the lock survives. Only the 'real' column is yours to keep.")
    print()


def section_bribe_market():
    print("=" * 80)
    print("2) THE BRIBE MARKET — when is bribing +EV for a game operator?")
    print("=" * 80)
    print(f"  Bribe efficiency: $1 of bribe directs ~${BRIBE_EFFICIENCY:.1f} of emissions to")
    print(f"  the briber's pool. Directed emissions deepen the pool -> more bet capacity ->")
    print(f"  more volume -> more operator revenue. Operator keeps a share of GGR.\n")
    op_ggr_share = 0.25                       # operator/frontend keeps 25% of the GGR it drives
    capacity_to_volume = 1.0                  # $1 extra incentivised depth -> $1*turnover extra annual volume (capped)
    print(f"  {'bribe $':>9}{'emissions directed':>20}{'extra depth':>13}"
          f"{'extra volume/yr':>17}{'op revenue/yr':>15}{'ROI':>8}")
    print("  " + "-" * 82)
    for bribe in [0.1e6, 0.5e6, 1e6, 2e6]:
        directed = bribe * BRIBE_EFFICIENCY              # emissions $ -> LP incentive -> depth
        depth = directed                                 # incentivised depth ~ emissions value
        extra_vol = depth * TURNOVER * capacity_to_volume
        op_rev = extra_vol * EDGE * op_ggr_share         # operator's slice of the new GGR
        roi = op_rev / bribe
        print(f"  {'$'+f'{bribe/1e6:.1f}M':>9}{'$'+f'{directed/1e6:.1f}M':>20}"
              f"{'$'+f'{depth/1e6:.1f}M':>13}{'$'+f'{extra_vol/1e6:.0f}M':>17}"
              f"{'$'+f'{op_rev/1e6:.2f}M':>15}{roi:>7.1f}x")
    print()
    roi = BRIBE_EFFICIENCY * TURNOVER * EDGE * op_ggr_share
    print(f"  Annual bribe ROI = efficiency x turnover x edge x op_share")
    print(f"                   = {BRIBE_EFFICIENCY} x {TURNOVER} x {EDGE} x {op_ggr_share}"
          f" = {roi:.2f}x  per year.")
    print()
    print("  INSIGHT (uncomfortable): naive single-game bribing is NOT +EV here — an")
    print("  operator recoups only ~0.13x of the bribe per year, because it captures just")
    print("  edge x op_share (~0.5%) of the volume the depth enables. This is the key way a")
    print("  CASINO gauge differs from Curve: a Curve briber wants deep liquidity for peg/")
    print("  strategic reasons and LPs capture full trading fees; a casino operator captures")
    print("  a thin rake slice, so the bribe math doesn't close on fees alone. The bribe")
    print("  market only works if you (a) bundle the operator's FULL stack (frontend + dev")
    print("  + house share, raising op_share to 50-70%), (b) make capacity STRATEGIC (a game")
    print("  literally can't accept whales without directed depth), or (c) keep bribes small")
    print("  and treat veHOUSE mainly as a real-fee + governance sink. Don't model a Curve-")
    print("  sized bribe economy onto a 2% edge — the capture rate isn't there.")
    print()


def make_chart():
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(chart skipped: {e})"); return
    tvls = np.linspace(20e6, 600e6, 60)
    pct_locked = []
    price = 8 * (EDGE*TURNOVER*tvls) / circulating_at(30)
    for tvl, p in zip(tvls, price):
        ggr = EDGE*TURNOVER*tvl; fdv = 8*ggr
        fee = VE_FEE_SHARE*PROTOCOL_TAKE*ggr
        emit = EMIT_TO_LOCKERS_YR*SUPPLY*p
        bribe = emit / BRIBE_EFFICIENCY
        locked_val = (fee+emit+bribe)/TARGET_VE_APR
        pct_locked.append(min(100, locked_val/fdv*100))
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(tvls/1e6, pct_locked, color="purple", lw=2)
    ax.fill_between(tvls/1e6, 0, pct_locked, color="purple", alpha=0.12)
    ax.set_xlabel("bankroll TVL ($M)")
    ax.set_ylabel("% of FDV locked as veHOUSE (equilibrium @20% APR)")
    ax.set_title("veHOUSE: real fees + bribes sponge float into locks as the protocol scales")
    ax.grid(alpha=0.3); fig.tight_layout()
    fig.savefig("figures/07_gauge.png", dpi=120); plt.close(fig)
    print("Chart -> figures/07_gauge.png")


def main():
    print("\nveHOUSE GAUGE & BRIBE-MARKET SIMULATION\n")
    section_ve_yield_and_lockrate()
    section_bribe_market()
    make_chart()


if __name__ == "__main__":
    main()
