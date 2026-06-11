# Calibr — Prediction-Market Strategies as Code (a "Remotion for trading")

*A product concept for a declarative, AI-native framework + CLI that turns a
prediction-market (Polymarket-first) or crypto trading strategy into a
versioned code artifact you can backtest, paper-trade, and deploy from one
command — and that an AI agent (Claude Code) can author and iterate on.*

This doc is written in the same spirit as the rest of this repo: first
principles, no flattery, and the hard truths stated where the idea is weak.
The companion simulation is `simulation/calibr_edge_sim.py`.

Date: 2026-06-11

---

## 0. TL;DR (read this if nothing else)

- **The analogy.** Remotion took *video* — historically a GUI timeline — and made
  it **code**: declarative React, versioned in git, rendered from a CLI,
  programmatically composable. Calibr does the same to a *trading/forecasting
  strategy*: it stops being a clicked-together bot config or a 2,000-line Python
  framework, and becomes a small declarative artifact that renders to an
  **equity curve + a calibration report**.

- **Why now, and why this is AI-native, not "AI-flavored."** The actual unlock
  is the authoring loop. You tell Claude Code *"write a strategy that fades
  Polymarket election markets when the YES+NO sum drifts below 0.98, backtest it
  over 2025, show me Brier score and max drawdown"* — and the agent writes a
  `.strat.ts` file, runs the deterministic backtest, **reads a real number**, and
  iterates. The framework's #1 design constraint is therefore *legibility to an
  agent*: deterministic, reproducible, and structurally hard to fool yourself
  with (see §6, look-ahead bias).

- **Why Polymarket specifically.** In a prediction market the entire edge reduces
  to **one skill: being better *calibrated* than the market** (lower Brier / log
  loss). Outcomes are *semantic events* ("will X win the election", "will the Fed
  cut in March") — exactly the surface where an LLM's read of news and narrative
  can plausibly beat a thin order book, and where a pure-quant shop has *less*
  structural advantage than it does in microstructure-dominated crypto perps.
  That is the wedge.

- **The honest core.** A prediction market price *is already a forecast*, and a
  reasonably liquid one is hard to beat. Calibr does not manufacture edge — it
  **measures whether you have any**, ruthlessly, and sizes it (Kelly) when you do.
  Most of the product's value is *negative*: killing strategies that only looked
  good because of look-ahead bias, survivorship in resolved markets, fee/slippage
  drag, and an LLM confidently asserting a 65% when the true frequency is 55%.
  An edge of "I think it's 60% and the market says 55%" is worth roughly
  **5¢ per $1 contract before costs** — and evaporates if your 60% is really 56%
  (see §5 and the simulation). The tool that tells you this honestly is more
  valuable, and rarer, than the tool that promises alpha.

- **Verdict (preview).** Strong as **infrastructure and an authoring/measurement
  loop**; weak the moment it implies easy alpha. The defensible asset is the
  *backtest integrity + AI authoring ergonomics + a marketplace of forkable,
  track-recorded strategies*, not any single signal. Monetize the rails (live
  execution, data, hosting, marketplace take), never a promised return.

---

## 1. The Remotion analogy, stated precisely

| | Remotion | Calibr |
|---|---|---|
| The artifact | A React component describing a video | A TS/Python module describing a strategy |
| Parameterized over | Frame / time `t` | Market tick / time `t` |
| The "render" | Frames → an `.mp4` | Historical ticks → an **equity curve + calibration report** |
| Determinism | Same code + inputs → identical video | Same code + data snapshot → identical backtest (non-negotiable) |
| Composition | `<Sequence>`, `<Composition>` | Sub-strategies composed into a portfolio with shared risk limits |
| CLI | `remotion render` | `calibr backtest \| paper \| live` |
| Why it mattered | Creative work became an engineering artifact (diffable, testable, programmable) | A strategy becomes an engineering artifact (diffable, testable, agent-authorable) |

The transferable insight is not "video, but trading." It is: **when a fuzzy,
GUI-trapped, hard-to-version craft becomes deterministic code, you unlock the
entire software toolchain on top of it — git, code review, CI, and now an AI
author.** Trading strategies are exactly such a craft.

---

## 2. The idea, stated precisely

A strategy is a declarative module. Everything that affects a trade is a pure-ish
function of *information available at time `t`* — the framework enforces that the
data layer cannot hand you the future (§6).

```ts
// strategies/yesno-arb.strat.ts
export default defineStrategy({
  universe: polymarket.category("politics", { minLiquidity: 25_000 }),

  // A "signal" is a pure function of the snapshot at tick t.
  signals: {
    // YES + NO should price to ~1; a deep discount is a (small, rare) arb.
    sumEdge: (m) => 1 - (m.yes.bestAsk + m.no.bestAsk),
  },

  // A "view" is YOUR probability. For a model-driven strat it can call an LLM,
  // a regression, or a hand rule. It is logged so calibration can be scored.
  view: (m, ctx) => ctx.model.estimate(m),     // returns p in [0,1]

  enter:  ({ sumEdge, view, market }) => sumEdge > 0.02 || edgeVsMarket(view, market) > 0.04,
  size:   kelly({ fraction: 0.25, cap: 0.02 }), // fractional Kelly, capped at 2% of bankroll
  exit:   ({ market }) => market.resolved || market.daysToResolution < 1,

  risk:   { maxExposurePerMarket: 0.02, maxCategoryExposure: 0.15, maxDrawdownStop: 0.20 },
  costs:  { takerFeeBps: 0, gasUsd: 0.02, slippageModel: "bookWalk" }, // Polymarket: maker/taker ~0, gas on Polygon
})
```

```bash
calibr backtest yesno-arb --from 2024-06 --to 2026-06   # deterministic replay → equity + Brier
calibr calib    yesno-arb                                # calibration plot: stated p vs realized freq
calibr paper    yesno-arb --live                         # live data, simulated fills, real-time PnL
calibr live     yesno-arb --wallet $WALLET --max 5000    # real orders, hard caps enforced in code
```

Two object types do the work:

1. **`signal`** — a pure function of the market snapshot (price, book depth,
   volume, time-to-resolution, on-chain flow). Deterministic, cheap, replayable.
2. **`view`** — *your probability estimate*, the thing you're betting is better
   than the market's. It may be a rule, a regression, or an **LLM call**. Crucially
   it is **logged every tick**, so after the fact Calibr scores your calibration
   (were your 70%s right 70% of the time?). This is the feature a generic trading
   bot does not have and a prediction-market tool must.

---

## 3. Architecture

```
            ┌──────────────────────────────────────────────────────────┐
            │                     calibr CLI / SDK                       │
            └──────────────────────────────────────────────────────────┘
   data plane                 strategy plane                 execution plane
 ┌──────────────┐        ┌────────────────────┐         ┌───────────────────┐
 │ Polymarket    │        │  signals  (pure)   │         │ backtest (replay) │
 │ CLOB + Gamma  │──tick─▶│  view     (model)  │──order─▶│ paper (sim fills) │
 │ on-chain (POL)│ snaps  │  size     (Kelly)  │ intents │ live  (CLOB+EVM)  │
 │ news/oracles  │        │  risk     (limits) │         │  hard caps in code│
 └──────────────┘        └────────────────────┘         └───────────────────┘
        │                          │                              │
        └────────── deterministic snapshot store (the "no future" guarantee) ──┘
                                   │
                       ┌───────────────────────┐
                       │  Claude Code skill /   │  author • backtest • read result • iterate
                       │  MCP server (AI loop)  │
                       └───────────────────────┘
```

- **Data plane.** Polymarket has a public CLOB API (order book, trades) and the
  Gamma markets API (metadata, resolution); settlement is on Polygon, so on-chain
  flow is readable too. The hard, valuable engineering is the **point-in-time
  snapshot store**: for every market and tick, what was knowable *then* — including
  the resolution status, which is the easiest thing to leak (§6).
- **Strategy plane.** The four primitives from §2. `view` is where an LLM plugs
  in; everything else is deterministic.
- **Execution plane.** One interface, three backends: `backtest` (replay),
  `paper` (live data, simulated fills against the real book), `live` (real orders
  via CLOB + EVM signing). Risk limits are enforced in the same code path for all
  three, so paper and live cannot silently diverge in their guardrails.
- **AI loop.** A Claude Code skill + MCP server exposing `author`, `backtest`,
  `calib`, `paper`. The agent writes a strat, runs it, reads structured results
  (equity, Brier, drawdown, trade log), and iterates — the Remotion-style "code →
  render → look → fix" loop, but the render is a backtest.

---

## 4. Why Polymarket is the right wedge (and crypto is the expansion)

| | Polymarket (prediction) | Crypto CEX/DEX (expansion) |
|---|---|---|
| Price *is* | a probability in [0,1] | a price level |
| Edge comes from | **calibration on semantic events** | microstructure, funding, basis, flow |
| LLM structural fit | **high** — news/narrative reasoning is the input | low–moderate — quants dominate microstructure |
| Competition | thin books, retail-heavy, event-driven | deep books, HFT, well-capitalized quants |
| The metric | Brier / log loss / ROI per edge-cent | Sharpe, funding capture |
| Settlement | UMA optimistic oracle on Polygon | exchange / chain |

The thesis: **an LLM agent's comparative advantage is reasoning over events
described in language, not racing a matching engine.** Prediction markets price
exactly such events, in books thin enough that a well-reasoned, well-*calibrated*
view can matter. That is a far better first beachhead for an AI-native trading
tool than competing with Jump in perp microstructure. Crypto is the *expansion*
SKU (same primitives, different data adapter) — it widens TAM and lets one
portfolio object span "will ETH ETF be approved" (Polymarket) and the ETH perp
that reprices on the same news. But lead with Polymarket.

---

## 5. Unit economics — where the edge is, and how small it is

Model a binary market. The market prices YES at `q`; your view is `p`. Buy YES at
`q`, it pays `1` if the event happens (true probability `π`), else `0`.

- **Expected profit per $1 contract** (ignoring fees): `E[profit] = π − q`.
- You *think* it's `p − q`. The gap `(p − π)` is **your calibration error**, and it
  comes straight out of your edge. This is the whole game in one line:

```
realized edge per contract  =  (π − q)  =  (p − q)  −  (p − π)
                                ▲ what you bet      ▲ how wrong you are
```

So a "5-cent edge" (`p − q = 0.05`) is **completely erased by a 5-point
miscalibration** (`p − π = 0.05`). Overconfident models — and LLMs are
famously overconfident on hard event questions — don't just earn less, they can
flip the sign. The simulation makes this concrete.

**Costs and frictions that eat the rest:**
- *Spread/slippage.* Thin books mean the price you wanted isn't the price you get;
  walking the book on size is a real haircut. A 5¢ edge against a 2¢ effective
  spread is a 3¢ edge.
- *Resolution risk.* Polymarket resolves via UMA's optimistic oracle. Ambiguous
  questions, disputes, and slow/contested resolution are a real, fat-tailed cost
  (e.g. several high-profile disputed resolutions). Your "win" isn't a win until
  it resolves your way.
- *Capital lockup.* Money is tied up until resolution — weeks to months. Annualized
  return divides your edge by holding time; a 5% edge held 3 months is ~20% APR
  *gross*, before the above.
- *Capacity.* Edge exists in size only where the book is deep. Most Polymarket
  markets are small; a strategy that's great at $500/market may be untradeable at
  $50k. Capacity, not edge, is usually the binding constraint.

**The Kelly point.** Given a *true* edge, fractional Kelly (¼–½) sizing maximizes
long-run growth without ruinous variance. Given a *fake* edge (miscalibration),
Kelly sizes you *into* the loss faster. So sizing is only as good as calibration —
which is why Calibr's headline output is the **calibration report**, not the APY.
That honesty is the product.

---

## 6. The integrity problem (this is the actual moat)

Backtests lie by default. A prediction-market backtester has *specific* ways to
fool you, and **building the framework so they can't is the defensible work** — far
more than any signal:

1. **Resolution leakage / look-ahead.** The single biggest one. If your snapshot
   store lets a strategy at tick `t` see the eventual outcome (or a field that
   correlates with it, like "market closed"), every backtest is a fantasy.
   Calibr's snapshot store is point-in-time by construction; resolution is a
   *future* fact the replay physically cannot serve early.
2. **Survivorship.** Backtesting only on markets that *resolved* (and that the API
   still returns) drops voided/relisted/illiquid ones and flatters results. The
   universe must be reconstructed as it existed then, including the duds.
3. **Fill realism.** Assuming you trade at the mid, or at unlimited size, invents
   returns. Paper and backtest fills walk the *historical book*; size has impact.
4. **Multiple-comparisons / overfitting.** Let an agent try 500 strategy variants
   and some will look great by chance. Calibr tracks the number of variants
   evaluated and reports deflated/holdout metrics, so "the agent found alpha" is
   distinguishable from "the agent found noise."
5. **LLM overconfidence as a *measured* quantity.** Because `view` is logged every
   tick, calibration is scored out-of-sample. A model whose 70%s happen 55% of the
   time is flagged, not trusted. This turns "the LLM is confident" into a number.

A trading-strategy tool that is *honest by construction* is rare, and it's exactly
what an AI authoring loop needs — because an over-eager agent will otherwise
cheerfully optimize the backtest into a lie.

---

## 7. Competitive landscape

| Tool | What it is | Gap Calibr fills |
|---|---|---|
| **Nautilus Trader / backtrader / vectorbt** | Serious quant backtesting frameworks (crypto/equities) | No prediction-market primitives, no calibration scoring, not AI-authorable, heavy |
| **Freqtrade / Hummingbot** | Open-source crypto trading/MM bots | Crypto-only, config/strategy-class heavy, no event/calibration model, no AI loop |
| **3Commas / Cryptohopper** | GUI bot SaaS | Closed, GUI not code, no backtest integrity story, no Polymarket |
| **Polymarket agent demos / open bots** | Scripts that hit the CLOB API; some LLM "agents" | One-off, no deterministic backtest, no calibration discipline, no point-in-time data |
| **Manifold / Metaculus tooling** | Forecasting + bots | Play-money or non-tradeable; great calibration culture, no real-money execution rails |

**The whitespace:** nobody pairs (a) a *prediction-market-native* declarative
strategy model, (b) *integrity-first* point-in-time backtesting with calibration
scoring, and (c) an *AI-native* authoring loop. Each exists separately. The
defensible combination is all three plus a track-recorded strategy marketplace.

---

## 8. Business model

Charge for the rails, never for a promised return (the casino-pool doc's lesson:
distribution and infrastructure are the moat; "alpha" is not a sellable promise
and inviting that liability is a mistake).

- **Open-core.** The framework, CLI, and backtester are open source (this is how
  you win developer/agent mindshare, à la Remotion's free core). 
- **Hosted execution & data** — paid: low-latency point-in-time data, a managed
  paper/live runner, alerting, and the snapshot store (the expensive part to
  self-host). This is the Remotion Lambda / hosted-render analog.
- **Strategy marketplace** — a take on a marketplace of *forkable, track-recorded*
  strategies. Track records are produced by Calibr's own honest engine, so the
  marketplace's credibility is the integrity story from §6. (Note the regulatory
  edge here — see §9; lean toward signal-sharing/tooling, not pooled funds.)
- **Team/enterprise** — collaboration, audit logs, compliance controls for funds
  and prop desks.

Crucially: **do not run a pooled fund or sell signals as investment advice** as
the default business — that's a regulated-investment-adviser / commodity-pool
problem, not a software business. Sell the tool.

---

## 9. Risks & failure modes (ranked, no flattery)

1. **There may be no edge, and the tool's honesty will prove it.** A liquid
   prediction market is an efficient forecast. Calibr's value proposition partly
   *depends on* most users discovering they can't beat it — which is true and good
   but is a hard thing to sell. Frame the product as *measurement and tooling*, not
   alpha, or it dies on the first honest backtest.
2. **Regulation.** Polymarket itself has a fraught US regulatory history (CFTC
   settlement; geofencing of US users; the broader event-contract/CFTC fight is
   live in 2025–26). A *tool* is far safer than an *operator/fund*, but anything
   that looks like pooling capital, selling signals as advice, or facilitating US
   access to a restricted venue carries real exposure. Stay on the software/tooling
   side; geofence; don't custody.
3. **Resolution/oracle risk is a fat tail you don't control.** UMA disputes,
   ambiguous questions, and slow resolution can turn a "winning" position into a
   loss or a months-long lockup. This is exogenous and must be modeled as a cost,
   not assumed away.
4. **Capacity ceiling.** The markets thin enough to be inefficient are also thin
   enough to be uninvestable at size. Edge that doesn't scale past a few $k/market
   is a hobby, not a business — be honest about which strategies have capacity.
5. **AI authoring amplifies overfitting.** The very loop that makes Calibr special
   (an agent trying many variants fast) is a multiple-comparisons machine. If §6's
   deflation/holdout discipline isn't airtight, the product becomes an
   alpha-hallucination factory. The integrity engine is not a feature; it's the
   whole ballgame.
6. **Data dependence on Polymarket APIs.** A single venue's API/ToS changes can
   break the data plane. Multi-venue adapters (Kalshi, crypto) reduce but don't
   remove this.

---

## 10. What a credible v1 looks like

- **Scope:** Polymarket only. One data adapter (CLOB + Gamma + Polygon), done
  *correctly* with a point-in-time snapshot store — depth over breadth.
- **The four primitives** (`signal` / `view` / `size` / `risk`) and three execution
  backends sharing one risk path.
- **Integrity first:** no-look-ahead snapshot store, survivorship-correct universe
  reconstruction, book-walk fills, variant-count tracking with holdout metrics.
  Ship the *calibration report* as the headline output, APY as secondary.
- **AI loop:** a Claude Code skill + MCP server for author→backtest→read→iterate.
- **Two flagship example strats** that are *honestly* modest: (a) a `YES+NO`
  mispricing/arb scanner (mechanical, real but tiny and capacity-limited), and
  (b) an LLM-`view` news strategy on one well-defined category, shipped *with* its
  calibration plot so users see exactly how good (or not) it is.
- **Open-core repo + hosted data/runner waitlist.** Win the agent/developer loop
  first; monetize the rails second.
- **Explicitly NOT in v1:** pooled capital, signal-selling, US onboarding, crypto
  perps, a token. Each adds regulatory or trust liability without proving the core.

---

## 11. Bottom line (no flattery)

The Remotion analogy is *real* and the wedge is *right*: a strategy genuinely
should be a deterministic, diffable, agent-authorable code artifact, and
prediction markets are the one place an LLM's event-reasoning has a structural
shot — so leading with Polymarket is correct. The durable asset is the **backtest
integrity engine + calibration scoring + AI authoring ergonomics + a
track-recorded marketplace**, not any signal; signals are commodities and most of
them are noise. The product's deepest, most uncomfortable feature is that it will
*honestly tell most users they have no edge* — and that honesty, sold as tooling
rather than alpha and kept clear of fund/advice regulation, is exactly why it's
defensible. Build the measuring instrument, not the slot machine.

---

### Reproduce
```
pip install -r requirements.txt
python3 simulation/calibr_edge_sim.py     # prints all tables; writes figures/
```
The simulation quantifies §5–§6: how a stated edge survives (or doesn't) once you
add miscalibration, spread, and resolution risk, and how fractional Kelly behaves
on a true edge vs a fake one.

### Sources (verify before relying)
- Polymarket CLOB & Gamma APIs / on-chain settlement (Polygon): https://docs.polymarket.com
- UMA optimistic oracle (how Polymarket resolves): https://docs.uma.xyz
- Polymarket CFTC settlement & US geofencing background: https://www.cftc.gov/PressRoom/PressReleases/8478-22
- Calibration / Brier score / proper scoring rules: https://en.wikipedia.org/wiki/Brier_score
- Kelly criterion: https://en.wikipedia.org/wiki/Kelly_criterion
- Remotion (the structural analogy — code-as-video): https://www.remotion.dev
- Quant frameworks for comparison: https://nautilustrader.io · https://www.freqtrade.io
