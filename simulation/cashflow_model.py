"""
$HOUSE monthly cash-flow & dilution model
=========================================
Month-by-month simulation that ties together TVL growth, GGR, the buyback, the
emission schedule, an ENDOGENOUS price (FDV tracks trailing GGR, so price falls
when volume is thin), and the resulting net token flow. Answers one question:

    when does  buyback$  outrun  sold-emissions$  ?   (the "flip date")

and shows the reflexive trap: thin GGR -> low FDV -> emissions are dilutive AND
the buyback is weak at the same time.

Run:  python3 cashflow_model.py   (writes figures/06_net_flow.png)
"""
from __future__ import annotations
import numpy as np
from tokenomics_sim import circulating_at, SUPPLY

# ------------------------------ assumptions --------------------------------
HORIZON_M     = 60
EDGE          = 0.02
TURNOVER      = 18          # mature annual wagered volume / TVL
TVL_START     = 10e6
TVL_TARGET    = 600e6       # logistic ceiling
TVL_GROWTH    = 0.13        # logistic monthly rate
PROTOCOL_TAKE = 0.15
BUYBACK_SHARE = 0.80        # of protocol take -> on-market buyback + burn
FDV_TO_GGR    = 8.0         # FDV = multiple of annualized GGR run-rate (endogenous price)
FDV_FLOOR     = 30e6        # speculative/airdrop floor so price isn't 0 at t0
SELL_THROUGH  = 0.50        # fraction of newly-emitted tokens sold each month
LOCK_RELIEF   = 0.0         # set >0 if veHOUSE locking removes sell pressure (see gauge sim)


def tvl_path():
    tvl = np.empty(HORIZON_M)
    x = TVL_START
    for m in range(HORIZON_M):
        x = x + TVL_GROWTH * x * (1 - x / TVL_TARGET)
        tvl[m] = x
    return tvl


def run(buyback_share=BUYBACK_SHARE, lock_relief=LOCK_RELIEF,
        fdv_to_ggr=FDV_TO_GGR, sell_through=SELL_THROUGH):
    tvl = tvl_path()
    rows = []
    flip = None
    cum_buyback = cum_sold = 0.0
    prev_circ = circulating_at(0)
    for m in range(HORIZON_M):
        annual_ggr = EDGE * TURNOVER * tvl[m]
        ggr_m      = annual_ggr / 12
        buyback_m  = buyback_share * PROTOCOL_TAKE * ggr_m
        circ       = circulating_at(m + 1)
        emit_tok   = max(0.0, circ - prev_circ)
        prev_circ  = circ
        fdv        = max(FDV_FLOOR, fdv_to_ggr * annual_ggr)
        price      = fdv / circ
        sold       = emit_tok * price * sell_through * (1 - lock_relief)
        net        = buyback_m - sold
        cum_buyback += buyback_m
        cum_sold    += sold
        if flip is None and net > 0:
            flip = m
        rows.append((m, tvl[m], annual_ggr, price, buyback_m, sold, net, fdv))
    return rows, flip, cum_buyback, cum_sold


def scenarios():
    print("  SCENARIO COMPARISON — what actually pulls the flip date earlier:")
    print(f"  {'scenario':46}{'flip month':>12}{'5yr net $M':>12}")
    print("  " + "-" * 70)
    cases = [
        ("Base (buyback 80%, no locking, FDV 8x)", dict()),
        ("+ veHOUSE locking removes 60% sell-through", dict(lock_relief=0.60)),
        ("+ aggressive buyback 95% of take (HYPE-like)", dict(lock_relief=0.60, buyback_share=0.95)),
        ("+ cheaper launch FDV (4x GGR)", dict(lock_relief=0.60, buyback_share=0.95, fdv_to_ggr=4.0)),
    ]
    for label, kw in cases:
        _, flip, cb, cs = run(**kw)
        fl = f"~m{flip}" if flip is not None else "never (5y)"
        print(f"  {label:46}{fl:>12}{(cb-cs)/1e6:>+11.0f}M")
    print()


def main():
    print("\n$HOUSE MONTHLY CASH-FLOW & DILUTION MODEL\n")
    print(f"  edge {EDGE:.0%}, turnover {TURNOVER}x, TVL {TVL_START/1e6:.0f}M -> "
          f"{TVL_TARGET/1e6:.0f}M (logistic), FDV = {FDV_TO_GGR:.0f}x annual GGR,")
    print(f"  buyback = {BUYBACK_SHARE*PROTOCOL_TAKE:.0%} of GGR, {SELL_THROUGH:.0%} of "
          f"emissions sold.\n")
    rows, flip, cum_b, cum_s = run()
    print(f"  {'mo':>4}{'TVL':>9}{'annGGR':>9}{'price':>8}{'FDV':>8}"
          f"{'buyback$/mo':>13}{'sold$/mo':>11}{'net$/mo':>11}")
    print("  " + "-" * 73)
    for (m, tvl, ggr, price, b, s, net, fdv) in rows:
        if m % 6 == 0 or m == flip:
            tag = "  <- FLIP" if m == flip else ""
            print(f"  {m:>4}{'$'+f'{tvl/1e6:.0f}M':>9}{'$'+f'{ggr/1e6:.1f}M':>9}"
                  f"{'$'+f'{price:.2f}':>8}{'$'+f'{fdv/1e6:.0f}M':>8}"
                  f"{'$'+f'{b/1e6:.2f}M':>13}{'$'+f'{s/1e6:.2f}M':>11}"
                  f"{('$'+f'{net/1e6:+.2f}M'):>11}{tag}")
    print()
    if flip is not None:
        print(f"  >>> NET-FLOW FLIP at month {flip} (~year {flip/12:.1f}): buyback first")
        print(f"      exceeds sold emissions. Before this, the token is SUBSIDIZING growth.")
    else:
        print("  >>> Buyback NEVER outruns emissions in horizon — emissions too hot or "
              "GGR too thin.")
    print(f"  Cumulative over {HORIZON_M}mo:  buyback ${cum_b/1e6:.0f}M  vs  "
          f"sold emissions ${cum_s/1e6:.0f}M   (net ${ (cum_b-cum_s)/1e6:+.0f}M)")
    print(f"  Buyback offsets {cum_b/cum_s*100:.0f}% of cumulative emission sell-pressure.")
    print()
    print("  INSIGHT: the flip date is the whole ballgame. It is LATE and reflexive —")
    print("  thin early GGR means low FDV, so emitted tokens are worth little (small $")
    print("  sold) BUT the buyback is also tiny, and you are diluting a large % of supply.")
    print("  Levers that pull the flip earlier: lower year-1 emissions, higher turnover,")
    print("  and veHOUSE LOCKING (removes sell-through — see gauge_market_sim.py). Publish")
    print("  this curve; it is the single most honest token-health metric you have.")
    print()
    scenarios()
    make_chart(rows, flip)


def make_chart(rows, flip):
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(chart skipped: {e})"); return
    m   = [r[0] for r in rows]
    b   = [r[4]/1e6 for r in rows]
    s   = [r[5]/1e6 for r in rows]
    net = np.cumsum([r[6] for r in rows]) / 1e6
    fig, ax1 = plt.subplots(figsize=(7.5, 4.5))
    ax1.bar([x-0.2 for x in m], b, width=0.4, color="green", alpha=0.7, label="buyback $/mo")
    ax1.bar([x+0.2 for x in m], s, width=0.4, color="firebrick", alpha=0.6, label="sold emissions $/mo")
    ax1.set_xlabel("month since TGE"); ax1.set_ylabel("$M / month")
    ax2 = ax1.twinx()
    ax2.plot(m, net, color="black", lw=2, label="cumulative net flow ($M)")
    ax2.axhline(0, color="grey", ls="--", lw=1)
    if flip is not None:
        ax1.axvline(flip, color="blue", ls=":", lw=1.5)
        ax1.text(flip+0.5, max(b)*0.9, f"flip ~m{flip}", color="blue", fontsize=9)
    ax2.set_ylabel("cumulative net flow ($M)")
    l1,la1 = ax1.get_legend_handles_labels(); l2,la2 = ax2.get_legend_handles_labels()
    ax1.legend(l1+l2, la1+la2, loc="upper left", fontsize=8)
    ax1.set_title("Buyback vs emission sell-pressure: the flip date")
    fig.tight_layout(); fig.savefig("figures/06_net_flow.png", dpi=120); plt.close(fig)
    print("\nChart -> figures/06_net_flow.png")


if __name__ == "__main__":
    main()
