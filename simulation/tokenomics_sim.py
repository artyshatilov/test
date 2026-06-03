"""
Tokenomics simulation for $HOUSE — the token of a shared on-chain casino/lottery
liquidity protocol. Models the three value-accrual pillars and their honest
failure modes, in the spirit of (and explicitly benchmarked against) HYPE.

PILLAR A  Fair launch + retroactive airdrop  -> distribution / float schedule
PILLAR B  GGR buyback-and-burn flywheel       -> "buyback yield" vs HYPE's ~7%
PILLAR C  $HOUSE as the FIRST-LOSS BACKSTOP    -> senior/junior tranche waterfall
          (the bit that makes the token productive collateral, like HLP is to HYPE)

Plus the part most token designs hide: REFLEXIVITY / WRONG-WAY RISK — in a bad
run the backstop is slashed AND buybacks fall AND the token falls, all at once.

Run:  python3 tokenomics_sim.py        (writes charts to figures/)
Reuses the gambling engine from casino_pool_sim.py.
"""
from __future__ import annotations
import numpy as np
from casino_pool_sim import Game, GAMES, simulate_year

rng = np.random.default_rng(11)
HYPE_BUYBACK_YIELD = 0.07   # ~7% of mcap/yr, our benchmark to beat


# ---------------------------------------------------------------------------
# PILLAR B — GGR buyback flywheel.  buyback$ = buyback_share * protocol_take * GGR
#            GGR = house_edge * turnover * TVL.   "buyback yield" = buyback$/FDV.
# ---------------------------------------------------------------------------
def section_buyback_flywheel():
    print("=" * 80)
    print("PILLAR B) GGR BUYBACK FLYWHEEL — 'buyback yield' vs HYPE (~7% of mcap/yr)")
    print("=" * 80)
    edge, turnover = 0.02, 20
    protocol_take = 0.15        # protocol keeps 15% of GGR
    buyback_share = 0.80        # 80% of that buys+burns $HOUSE (rest = ops/compliance)
    print(f"  Assumes: edge {edge:.0%}, turnover {turnover}x  -> GGR = {edge*turnover:.0%} of TVL/yr")
    print(f"  Protocol take {protocol_take:.0%} of GGR; {buyback_share:.0%} of take -> buyback+burn.")
    print(f"  buyback$ = {buyback_share*protocol_take:.1%} of GGR = "
          f"{buyback_share*protocol_take*edge*turnover*100:.2f}% of TVL per year.\n")
    tvls = [50e6, 200e6, 500e6]            # bankroll TVL
    fdvs = [100e6, 300e6, 1e9, 3e9]        # token FDV
    print(f"  Annual buyback as % of FDV  ('buyback yield'):")
    label = "TVL \\ FDV"
    print(f"  {label:>14}" + "".join(f"{'$'+f'{f/1e6:.0f}M':>11}" for f in fdvs))
    print("  " + "-" * (14 + 11 * len(fdvs)))
    for tvl in tvls:
        ggr = edge * turnover * tvl
        buyback = buyback_share * protocol_take * ggr
        row = f"  {'$'+f'{tvl/1e6:.0f}M':>13}"
        for f in fdvs:
            y = buyback / f
            flag = "*" if y >= HYPE_BUYBACK_YIELD else " "
            row += f"{y*100:>9.1f}%{flag}"
        print(row)
    print("\n  ('*' = beats HYPE's ~7%/yr buyback rate.)")
    print("  INSIGHT: buyback yield is buyback$/FDV. It is high only when FDV is")
    print("  disciplined relative to real GGR. A $3B FDV on $50M TVL gives a 0.1%")
    print("  'yield' — a meme, not a flywheel. HYPE's 7% is impressive BECAUSE fees are")
    print("  enormous vs mcap. Do not ship a 1B-supply token into thin GGR and call the")
    print("  buyback a flywheel; it only works if you keep FDV honest until volume exists.")
    print()


# ---------------------------------------------------------------------------
# PILLAR C — $HOUSE staked as FIRST-LOSS BACKSTOP (junior tranche).
#   Total bankroll = senior (stablecoin LPs, protected, capped coupon) +
#   junior (staked $HOUSE, absorbs the first loss, gets the upside + emissions).
#   This pays SOMEBODY for the negative-skew tail (the gap the prior research found)
#   and makes the token productive collateral wired into the core risk engine.
# ---------------------------------------------------------------------------
def tranche_waterfall(game, tvl=200e6, turnover=12, junior_frac=0.25,
                      senior_coupon=0.10, protocol_take=0.15,
                      junior_emissions=0.08, n_paths=300_000):
    """Returns (senior_return[], junior_return[]) annual, per path."""
    gross_roc = simulate_year(game, tvl=tvl, turnover=turnover, lp_share=1.0,
                              kelly_cap=0.01, n_paths=n_paths)   # house PnL / TVL
    realized = gross_roc * tvl
    senior_cap = tvl * (1 - junior_frac)
    junior_cap = tvl * junior_frac
    protocol_cut = np.maximum(0.0, realized) * protocol_take
    distributable = realized - protocol_cut
    coupon = senior_cap * senior_coupon

    senior_pnl = np.full(n_paths, coupon)            # senior gets coupon by default
    junior_pnl = distributable - coupon              # junior takes the residual (+/-)
    # if junior is wiped, senior eats the remainder beyond the junior buffer:
    wiped = junior_pnl < -junior_cap
    senior_pnl = np.where(wiped, coupon + (junior_pnl + junior_cap), coupon)
    junior_pnl = np.where(wiped, -junior_cap, junior_pnl)

    senior_ret = senior_pnl / senior_cap
    junior_ret = junior_pnl / junior_cap + junior_emissions   # emissions paid in token
    return senior_ret, junior_ret


def _row(label, r):
    return (f"  {label:30}{r.mean()*100:>9.1f}%{np.median(r)*100:>9.1f}%"
            f"{np.percentile(r,5)*100:>9.1f}%{(r<0).mean()*100:>10.1f}%{r.min()*100:>10.1f}%")


def section_backstop_tranche():
    print("=" * 80)
    print("PILLAR C) $HOUSE AS FIRST-LOSS BACKSTOP — senior/junior tranche waterfall")
    print("=" * 80)
    print("  Bankroll = 75% senior (stable LPs, ~10% capped coupon, protected) + 25%")
    print("  junior (staked $HOUSE, first-loss, gets residual + 8% emissions). TVL $200M, 12x.")
    print()
    print(f"  {'tranche / game':30}{'mean':>9}{'median':>9}{'p5':>9}{'P(loss)':>10}{'worst':>10}")
    print("  " + "-" * 78)
    for key in ["roulette", "slots"]:
        g = GAMES[key]
        s, j = tranche_waterfall(g)
        print(_row(f"SENIOR · {g.name.split(' (')[0]}", s))
        print(_row(f"JUNIOR($HOUSE) · {g.name.split(' (')[0]}", j))
    print()
    print("  INSIGHT: the token tranche manufactures a clean two-sided product. SENIOR")
    print("  stablecoin LPs get a near-bond-like ~10% with P(loss)≈0 -> sticky, scalable,")
    print("  risk-averse capital. JUNIOR $HOUSE stakers get a LEVERED, emissions-boosted")
    print("  yield in exchange for eating the fat left tail (occasional -100% slashing).")
    print("  This finally PAYS someone for the negative skew, and ties the token to the")
    print("  core risk engine the way HLP is core to HYPE — not a bolt-on governance coin.")
    print()


# ---------------------------------------------------------------------------
# REFLEXIVITY / WRONG-WAY RISK — the part most designs hide.
# In a bad run: volume falls -> GGR & buyback fall; pool draws down -> junior
# slashed; token price falls -> the USD buffer the junior provided shrinks,
# exactly when it is needed. Three correlated hits at once.
# ---------------------------------------------------------------------------
def section_reflexivity():
    print("=" * 80)
    print("REFLEXIVITY / WRONG-WAY RISK — why the token backstop can fail when needed")
    print("=" * 80)
    tvl = 200e6
    junior_frac = 0.25
    junior_usd_normal = tvl * junior_frac          # nominal backstop
    # Stress: a bad gambling run + risk-off market hit simultaneously.
    pool_drawdown = 0.18                            # 18% of TVL lost in the bad year
    token_price_drop = 0.60                         # $HOUSE -60% (beta to GGR + sentiment)
    print(f"  Nominal junior backstop: {junior_frac:.0%} of ${tvl/1e6:.0f}M = "
          f"${junior_usd_normal/1e6:.0f}M.")
    print(f"  Stress year: pool loses {pool_drawdown:.0%} of TVL "
          f"(${pool_drawdown*tvl/1e6:.0f}M) AND $HOUSE falls {token_price_drop:.0%}.\n")
    loss = pool_drawdown * tvl
    effective_buffer = junior_usd_normal * (1 - token_price_drop)   # buffer in $ after crash
    print(f"  Tail loss to cover:                 ${loss/1e6:>6.0f}M")
    print(f"  Backstop value AFTER token crash:   ${effective_buffer/1e6:>6.0f}M   "
          f"(was ${junior_usd_normal/1e6:.0f}M)")
    print(f"  Coverage ratio (buffer / loss):     {effective_buffer/loss:>6.2f}x   "
          f"{'-> SENIOR PROTECTED' if effective_buffer>=loss else '-> SENIOR HIT (backstop fails)'}")
    print()
    print("  INSIGHT: a token-denominated backstop is WORTH LEAST exactly when it is")
    print("  needed MOST — its price is correlated to the same volume/GGR that drives")
    print("  the loss. A 25% junior buffer that looks like $50M is only ~$20M after a")
    print("  60% drawdown, and may not cover an 18% pool loss. Mitigations: (1) size")
    print("  junior on STRESSED token value, not spot; (2) hold part of the backstop in")
    print("  stablecoins / protocol-owned reserve (not just staked token); (3) hard")
    print("  per-game payout caps so the tail can't exceed the stressed buffer. Do NOT")
    print("  market token TVL as 'real' bankroll 1:1 — discount it for reflexivity.")
    print()


# ---------------------------------------------------------------------------
# PILLAR A — supply, distribution, float & emissions schedule (6-yr, HYPE-like).
# ---------------------------------------------------------------------------
SUPPLY = 1_000_000_000
ALLOCATION = {   # bucket: (pct, cliff_months, vest_months, unlocked_at_tge_pct_of_bucket)
    "Genesis airdrop (LPs/players/devs)": (0.35, 0, 0, 1.00),
    "Community/LP & backstop emissions":  (0.30, 0, 60, 0.0),
    "Team & early contributors":          (0.15, 12, 36, 0.0),
    "DAO treasury":                       (0.08, 0, 48, 0.10),
    "Backstop / insurance seed (PoL)":    (0.05, 0, 0, 1.00),
    "Ecosystem / liquidity":              (0.07, 0, 24, 0.30),
}

def circulating_at(month):
    total = 0.0
    for pct, cliff, vest, tge in ALLOCATION.values():
        bucket = SUPPLY * pct
        unlocked = bucket * tge
        if month >= cliff and vest > 0:
            prog = min(1.0, (month - cliff) / vest)
            unlocked += (bucket - bucket * tge) * prog
        elif vest == 0 and month >= cliff:
            unlocked = bucket            # fully unlocked after cliff
        total += min(bucket, unlocked)
    return total


def section_supply_schedule():
    print("=" * 80)
    print("PILLAR A) SUPPLY & DISTRIBUTION — fair-launch, community-heavy (HYPE-style)")
    print("=" * 80)
    community = sum(p for k,(p,*_ ) in ALLOCATION.items()
                    if k.startswith(("Genesis","Community","DAO","Backstop")))
    print(f"  Total supply: {SUPPLY:,.0f} $HOUSE.  Community-aligned ≈ {community:.0%} "
          f"(HYPE was ~70%+, 31% airdrop).")
    print(f"  {'bucket':38}{'%':>6}{'cliff':>7}{'vest':>7}{'@TGE':>7}")
    print("  " + "-" * 65)
    for k,(p,cliff,vest,tge) in ALLOCATION.items():
        print(f"  {k:38}{p*100:>5.0f}%{cliff:>6}m{vest:>6}m{tge*100:>6.0f}%")
    print()
    print(f"  {'month':>6}{'circulating':>14}{'% of supply':>13}")
    print("  " + "-" * 33)
    for m in [0, 6, 12, 24, 36, 48, 60, 72]:
        c = circulating_at(m)
        print(f"  {m:>5}m{c:>14,.0f}{c/SUPPLY*100:>12.1f}%")
    print()
    print("  INSIGHT: float at TGE ~38% (airdrop + seed + some ecosystem), team cliffed")
    print("  12mo. The risk is the 30% emissions bucket: it is CAC for liquidity, and if")
    print("  monthly emission $ exceeds monthly buyback $, the token net-inflates and the")
    print("  'flywheel' runs backwards. Emissions must taper INTO rising GGR, not ahead of")
    print("  it. Track one number: net flow = buyback$ - sold_emissions$ (see below).")
    print()


def section_net_flow():
    print("=" * 80)
    print("NET TOKEN FLOW — does the buyback outrun the emissions? (the only question)")
    print("=" * 80)
    edge, turnover, protocol_take, buyback_share = 0.02, 20, 0.15, 0.80
    price = 0.50                          # assumed $HOUSE price for the illustration
    sell_through = 0.50                   # 50% of emitted tokens get sold
    print(f"  Assume $HOUSE = ${price:.2f}, {sell_through:.0%} of emissions sold. "
          f"Buyback = {buyback_share*protocol_take:.1%} of GGR.\n")
    print(f"  {'year':>5}{'TVL':>9}{'GGR':>9}{'buyback$':>11}{'emit(tok)':>12}"
          f"{'sold$':>10}{'net$/yr':>11}")
    print("  " + "-" * 67)
    for yr, tvl in [(1, 40e6), (2, 120e6), (3, 300e6), (4, 500e6)]:
        ggr = edge * turnover * tvl
        buyback = buyback_share * protocol_take * ggr
        emit_tokens = (circulating_at(yr*12) - circulating_at((yr-1)*12))
        sold = emit_tokens * price * sell_through
        net = buyback - sold
        print(f"  {yr:>4}y{'$'+f'{tvl/1e6:.0f}M':>9}{'$'+f'{ggr/1e6:.1f}M':>9}"
              f"{'$'+f'{buyback/1e6:.1f}M':>11}{emit_tokens/1e6:>10.0f}M"
              f"{'$'+f'{sold/1e6:.1f}M':>10}{('$'+f'{net/1e6:+.1f}M'):>11}")
    print()
    print("  INSIGHT: early years are net-NEGATIVE (emissions >> buyback) — this is the")
    print("  bootstrapping subsidy, and it is real dilution. The model only inverts once")
    print("  TVL/GGR scale. Be honest in the deck: years 1-2 are paid for by the token,")
    print("  the flywheel is a YEAR-3+ phenomenon, and it is conditional on hitting volume.")
    print()


def make_charts():
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(charts skipped: {e})"); return

    # Chart: tranche return distributions (senior vs junior)
    s, j = tranche_waterfall(GAMES["roulette"])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(j*100, bins=80, alpha=0.5, color="firebrick", label="JUNIOR $HOUSE (first-loss)")
    ax.hist(s*100, bins=80, alpha=0.7, color="steelblue", label="SENIOR stable LP")
    ax.axvline(0, color="black", lw=1)
    ax.set_xlabel("annual return on capital (%)"); ax.set_ylabel("paths")
    ax.set_title("Tranching: senior gets a bond, $HOUSE stakers get the levered tail")
    ax.legend(); ax.grid(alpha=0.3); fig.tight_layout()
    fig.savefig("figures/04_tranche_returns.png", dpi=120); plt.close(fig)

    # Chart: circulating supply schedule
    months = np.arange(0, 73)
    circ = np.array([circulating_at(m) for m in months]) / 1e6
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(months, circ, color="darkgreen", lw=2)
    ax.fill_between(months, 0, circ, color="darkgreen", alpha=0.12)
    ax.set_xlabel("months since TGE"); ax.set_ylabel("circulating supply (M $HOUSE)")
    ax.set_title("$HOUSE circulating supply — 6-yr emission, 12-mo team cliff")
    ax.grid(alpha=0.3); fig.tight_layout()
    fig.savefig("figures/05_supply_schedule.png", dpi=120); plt.close(fig)
    print("Charts -> figures/: 04_tranche_returns.png, 05_supply_schedule.png")


def main():
    print("\n$HOUSE TOKENOMICS — SIMULATION (benchmarked vs HYPE)\n")
    section_supply_schedule()
    section_buyback_flywheel()
    section_backstop_tranche()
    section_reflexivity()
    section_net_flow()
    make_charts()


if __name__ == "__main__":
    main()
