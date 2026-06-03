# Shared On-Chain Casino & Lottery Pool — Research

First-principles research and a business-model simulation for a protocol that provides
**shared liquidity + verifiable RNG + a game SDK**, so developers can ship casino/lottery
games without raising their own bankroll, LPs stake liquidity for yield, and the pool earns
from house edge and fees.

## Contents
- **[`LITEPAPER.md`](./LITEPAPER.md)** — one-page shareable summary (problem, product,
  economics, `$HOUSE` token, and the honest risks). **Read this first for the overview.**
- **[`RESEARCH.md`](./RESEARCH.md)** — the full report: idea, live comparables (Azuro,
  Hyperliquid HLP, GMX GLP, Edgeless, PoolTogether), unit economics, simulation findings,
  business model, risks, and a no-flattery verdict.
- **[`TOKENOMICS.md`](./TOKENOMICS.md)** — `$HOUSE` token design, benchmarked against HYPE:
  fair-launch distribution, a GGR buyback flywheel, and the token-as-first-loss-backstop
  tranche (plus the reflexivity/wrong-way risk most designs hide).
- **Simulations** (`simulation/`):
  - `casino_pool_sim.py` — pool economics: yield identity, variance/capacity tax, tail risk,
    RNG cost, contagion, real-yield-vs-emissions, fee waterfall.
  - `tokenomics_sim.py` — buyback yield vs HYPE, senior/junior tranche waterfall, reflexivity.
  - `cashflow_model.py` — monthly buyback-vs-emissions, the net-flow **flip date**, scenarios.
  - `gauge_market_sim.py` — veHOUSE lock rate (real vs reflexive) and the bribe-market ROI.
- `simulation/*_output.txt` — captured run output.
- `simulation/figures/` — 7 charts.

## Run
```bash
pip install -r requirements.txt
python3 simulation/casino_pool_sim.py
```

## The one-line model
**LP APY ≈ house_edge × turnover × LP_share − costs**, where `turnover = annual wagered
volume / TVL`. Yield is driven by *capital velocity*, not by the size of the rake — and the
pool is structurally *short a lottery* (steady yield, occasional large loss). See
`RESEARCH.md §0` for the TL;DR.
