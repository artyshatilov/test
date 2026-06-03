# Shared On-Chain Casino & Lottery Pool — Research

First-principles research and a business-model simulation for a protocol that provides
**shared liquidity + verifiable RNG + a game SDK**, so developers can ship casino/lottery
games without raising their own bankroll, LPs stake liquidity for yield, and the pool earns
from house edge and fees.

## Contents
- **[`RESEARCH.md`](./RESEARCH.md)** — the full report: idea, live comparables (Azuro,
  Hyperliquid HLP, GMX GLP, Edgeless, PoolTogether), unit economics, simulation findings,
  business model, risks, and a no-flattery verdict. **Start here.**
- **[`TOKENOMICS.md`](./TOKENOMICS.md)** — `$HOUSE` token design, benchmarked against HYPE:
  fair-launch distribution, a GGR buyback flywheel, and the token-as-first-loss-backstop
  tranche (plus the reflexivity/wrong-way risk most designs hide).
- **[`simulation/casino_pool_sim.py`](./simulation/casino_pool_sim.py)** — Monte Carlo +
  closed-form model of the pool economics. Prints all tables; writes charts.
- **[`simulation/tokenomics_sim.py`](./simulation/tokenomics_sim.py)** — token model:
  buyback yield vs HYPE, senior/junior tranche waterfall, reflexivity stress, supply schedule.
- `simulation/sim_output.txt`, `simulation/tokenomics_output.txt` — captured run output.
- `simulation/figures/` — charts (yield vs turnover, capital-vs-variance, LP return skew,
  tranche returns, supply schedule).

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
