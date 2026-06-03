# The House — Litepaper (one page)

**Shared on-chain liquidity, verifiable RNG, and an SDK so anyone can ship a casino or
lottery without raising a bankroll. Stake to become the house.**

*This is a condensed version of [`RESEARCH.md`](./RESEARCH.md) and
[`TOKENOMICS.md`](./TOKENOMICS.md). Every number is reproducible in [`simulation/`](./simulation).*

---

### The problem
A developer who wants to launch an on-chain casino game needs three things that have nothing
to do with their game: **a bankroll** to pay winners, **provably-fair randomness**, and
**liquidity deep enough to accept real bets**. Raising and risk-managing a bankroll is harder
than building the game. So games don't get built, and the liquidity that exists is fragmented
across operators who each under-capitalize.

### The product
One protocol provides all three as shared infrastructure:
- **Pooled bankroll** — LPs stake capital; the pool is the counterparty (the "house").
- **Verifiable RNG** — Chainlink VRF / commit-reveal, auditable on-chain.
- **Game SDK** — developers integrate against the shared pool + RNG with zero liquidity.

Players get provably-fair games. Developers/frontends ship in days and earn a cut of the house
edge their players generate. LPs earn yield from the house edge. *(Live proof points: Azuro
runs this for betting; Hyperliquid HLP / GMX GLP are the same "vault-as-counterparty" primitive.)*

### The economics (one equation)
> **LP yield ≈ house_edge × turnover × LP_share**, where **turnover = annual wagered volume ÷ TVL.**

Yield is driven by **capital velocity, not the size of the rake.** A 2%-edge pool at 25×
turnover (35% APY) beats a 4%-edge pool at 5× (14%). So we compete on volume and bet-capacity,
and keep the edge low. Three hard truths the simulations make explicit:
1. **Variance is a capacity tax.** Required bankroll scales with the *top multiplier*, not the
   average bet (a 1,000× slot needs ~55,000× the max bet in reserves). High-multiplier games
   are constrained by TVL, so **TVL is a product feature (bet capacity), not just a buffer.**
2. **The pool is short a lottery.** Steady yield, occasional large loss; the pool is most
   fragile when youngest (low volume → few jackpots → fat left tail). Honest risk metric is
   expected big-hits `N·p`, not headline APY.
3. **Lotteries don't belong in a shared bankroll.** Use a yield-funded (PoolTogether-style) or
   parimutuel prize so the house is ruin-proof. Casino games and jackpots run on *different*
   engines.

### Revenue
Protocol takes **~15% of GGR**. Most of it funds a **buyback-and-burn** of the token; the rest
funds ops/compliance and a stablecoin first-loss reserve. LPs and game developers get the
majority of GGR — because **distribution is the moat, and liquidity is a commodity.**

---

## The token — $HOUSE (designed against HYPE)

We copy the three things that make HYPE work, and add one a casino can have that a perp DEX can't.

**A · Fair launch.** 1B supply, ~78% community-aligned, **35% retroactive airdrop** (HYPE: 31%),
no VC dump, team cliffed 12 months. Airdrop scored on **net GGR contributed, not volume** —
otherwise wash-betting farms the drop and drains the edge.

**B · Buyback flywheel.** 15% protocol take → 80% buys & burns $HOUSE. "Buyback yield" =
buyback$/FDV; it beats HYPE's ~7%/yr **only if launch FDV is disciplined vs real GGR** ($3B FDV
on thin GGR = a 0.1% buyback = a meme). The mechanism is identical to HYPE; whether it matters
is entirely about not over-pricing the launch.

**C · The token *is* the backstop (the interesting part).** Tranche the bankroll:
- **Senior (~75%) stablecoin LPs** — capped ~10%, **0% loss probability** → sticky, scalable capital.
- **Junior (~25%) staked $HOUSE** — first-loss, earns the **levered residual + emissions**
  (~88% mean on roulette), slashed in tail years. **Staking $HOUSE = owning the equity of a
  profitable casino**, and it finally *pays someone* for the negative-skew tail. This wires the
  token into the core risk engine the way HLP is core to HYPE — not a governance fig-leaf.

**Demand sinks:** backstop staking · veHOUSE gauges (lock to direct emissions/capacity to
games) · gas (if app-chain) · player fee tiers · governance over risk params.

---

## What we refuse to hide (the honest column)

- **Reflexivity / wrong-way risk.** A token-funded backstop is worth least exactly when needed
  most. A nominal $50M junior buffer is ~$20M after a 60% token drawdown — may not cover an 18%
  pool loss (coverage 0.56×). Fix: size backstop on *stressed* token value, keep a **stablecoin
  floor** under first-loss, hard per-game caps.
- **The flywheel is a year-3+ phenomenon.** Monthly cash-flow model: with a 12%-of-GGR buyback
  and the base emission schedule, buyback **never outruns emission sell-pressure in 5 years**
  (−$188M cumulative). It only flips with **disciplined launch FDV + veHOUSE locking** (flip ~month
  27, +$22M). Years 1–2 are token-subsidized growth; say so.
- **The gauge/bribe market is weaker than Curve's.** A casino operator captures only
  `edge × op_share (~0.5%)` of the volume that incentivized depth enables, so naive single-game
  bribing earns ~0.13×/yr — *not* +EV. veHOUSE works mainly as a real-fee + governance sink;
  don't model a Curve-sized bribe economy onto a 2% edge.
- **Regulation is the #1 binding constraint.** This is unlicensed gambling infrastructure; an
  LP that earns house profits and bears losses looks like a security. Geofencing, licensing, or
  a no-loss/parimutuel framing are partial, costly mitigations.

---

## Verdict
The casino half is a real, proven primitive with a clean revenue identity and a token design
that's arguably *more* interesting than a pure buyback coin — the holder becomes the house. But
the **honest** version is **conservatively capitalized**: disciplined FDV, stress-discounted
backstop, a stablecoin floor, volume-gated emissions, and lotteries on a separate ruin-proof
engine. The technology is the easy part; this is won or lost on **regulation, distribution, and
the honesty of the risk pricing.**

*Charts & models: [`simulation/`](./simulation) → `python3 simulation/casino_pool_sim.py`,
`tokenomics_sim.py`, `cashflow_model.py`, `gauge_market_sim.py`.*
