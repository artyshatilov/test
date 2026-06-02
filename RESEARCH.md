# Shared On-Chain Casino & Lottery Pool — Research & Business Model

*A first-principles teardown of a protocol that provides pooled liquidity, verifiable
RNG, and a game SDK so developers can ship casino/lottery games without their own
bankroll. Straightforward, not promotional. Where the idea is weak, this says so.*

Date: 2026-06-02 · Companion simulation: `simulation/casino_pool_sim.py`

---

## 0. TL;DR (read this if nothing else)

- **The product is real and has a live proof point.** Azuro already runs almost exactly
  this model for prediction/betting markets: one shared "Liquidity Tree" pool, an SDK,
  permissionless frontends that earn a cut of pool profit, and LPs earning stablecoin
  yield off the spread (it reports >95% of LP positions held >1 month are positive).
  Perp-DEX vaults (Hyperliquid HLP, GMX GLP) are the same primitive — a shared vault as
  the counterparty — and have done ~17–20% annualized, with rare brutal drawdowns.

- **LP yield is not "house edge." It is `edge × turnover × LP_share`.** Turnover (annual
  wagered volume ÷ TVL) is the dominant lever. A 2%-edge pool at 25× turnover (35% APY)
  beats a 4%-edge pool at 5× turnover (14% APY). **The business competes on capital
  velocity, not on taking a bigger rake.** Most operators get this backwards.

- **The pool is structurally short a lottery.** LPs collect small, steady yield and
  occasionally eat a large loss. Advertised APY is a mean over survivor paths; the honest
  metric is risk-adjusted return and max drawdown. This negative skew is a *volume*
  phenomenon — the pool is most fragile precisely when it is youngest and thinnest.

- **The hard problems are not technical.** They are (a) the two-sided cold-start, where
  the LP is the *riskier* side and gets bootstrapped with token emissions (= dilution, not
  yield); (b) **correlated tail risk** — shared liquidity means the pool is only as safe as
  its loosest payout cap and its buggiest integrated game contract; and (c) **regulation**
  — this is unlicensed gambling infrastructure in most jurisdictions.

- **The defensible asset is distribution (games + frontends), not liquidity.** Capital is a
  commodity that chases the highest risk-adjusted yield. Subsidize the demand side; price
  the LP tail honestly. If you starve LPs to win the growth race, they leave at the first
  drawdown — which is also the moment you can least afford it.

**Verdict:** viable as *infrastructure for high-frequency, low-multiplier, capped games on a
cheap chain*, monetized as a thin slice of GGR with LPs as a real-yield product. Not viable
as a one-pool-backs-everything casino *and* jackpot lottery — those have opposite risk
shapes and must run on different engines. The moat is a developer/distribution network, and
the binding constraints are regulation and the cost of honest LP risk premia.

---

## 1. The idea, stated precisely

Three primitives offered as shared infrastructure:

1. **Pooled bankroll.** LPs deposit capital into a vault that acts as the *house* — the
   counterparty to every bet. House edge accrues to the vault; losing streaks are drawn
   from it. (Cf. Edgeless: stakers form a decentralized bankroll, take 40% of surplus, and
   eat deficits; HLP/GLP: vault is the counterparty to traders.)
2. **Verifiable RNG.** Provably-fair randomness (Chainlink VRF or commit-reveal) so games
   can't be rigged and outcomes are auditable on-chain.
3. **Game SDK.** Developers integrate games/lotteries against the shared pool and RNG
   *without raising their own bankroll*. Frontends/operators bring players and take a cut.

**Who gets what:**
- *Players* — provably-fair games, instant on-chain settlement.
- *Developers/operators* — ship a casino with zero liquidity and no RNG infra; earn a share
  of the house edge their players generate (Azuro pays frontends a slice of pool profit).
- *LPs* — yield from house edge + fees, in exchange for bearing the gambling risk.
- *Protocol* — a thin take of gross gaming revenue (GGR) + token.

This is a **three-sided marketplace**: capital (LPs) ↔ infrastructure (protocol) ↔
distribution (devs/frontends/players). That framing matters for everything below.

---

## 2. Comparable products (what already exists)

| Product | What it is | Relevance | Reported economics |
|---|---|---|---|
| **Azuro** | Shared "Liquidity Tree" pool for prediction/betting + SDK + permissionless frontends | **Closest analog.** 4+ yrs on-chain, 40+ apps. Frontends earn % of pool profit; LPs earn stablecoin yield off the spread | ">95% of LP positions held >1mo are positive" |
| **Hyperliquid HLP** | Community vault that is the counterparty/market-maker for a perp DEX | Canonical "shared vault as house" | ~17–20% annualized typical; survived an adversarial whale-induced multi-$M drawdown (Mar 2025) |
| **GMX GLP** | Passive LP basket that is the counterparty to perp traders | Pure "LPs win when users lose" | Direct inverse of trader PnL |
| **Edgeless** | Early on-chain casino; EDG stakers form bankroll | Direct: bankroll staking with deficit risk | Distributes 40% of bankroll surplus to stakers |
| **Rollbit / FUN** | Crypto casino w/ token revenue-share / vaults | Token-monetized house | "Diamond Vault" anecdote ~28% over 9mo (largely token revenue-share, not pure edge) |
| **PoolTogether** | No-loss prize lottery: principal kept, yield funds prizes | **The correct lottery pattern** — house never risks ruin | ~$195M TVL, >$100k/wk prizes, funded by DeFi yield |

**Two things this table tells you.** First, the casino-half of the idea is validated by
Azuro/HLP/GLP/Edgeless — a shared vault can earn real, double-digit, risk-bearing yield.
Second, the **lottery-half should not be bankroll-backed at all.** PoolTogether shows the
dominant on-chain lottery design funds prizes *from yield on preserved principal*, so the
house literally cannot go bankrupt. A jackpot lottery backed by LP capital is selling deep
out-of-the-money options for pennies — see §4 and §6.

---

## 3. Unit economics from first principles

Model a bet as a unit stake returning the player `M` (the top multiplier) with probability
`p`, else 0. Define house edge `h`; then `RTP = p·M = 1 − h`, so `p = (1−h)/M`.

House profit per unit staked `X = 1 − R`:
- **Mean:** `E[X] = h` (the edge).
- **Variance:** `Var[X] = (1−h)·(M − (1−h)) ≈ (1−h)(M−1)`. Call this the **variance index**.
  It grows ~linearly in `M`, the top multiplier.

**The number that drives capital requirements is `M`, not the average bet.**

### 3.1 LP yield identity

Over a year with wagered volume `V` against TVL `B`:
```
Gross house revenue (GGR) = h · V
LP APY ≈ h · (V/B) · LP_share − cost_drag
       = house_edge × turnover × LP_share − costs
```
`turnover = V/B` is **capital velocity**. This single identity is the whole revenue model.

| edge \ turnover | 2× | 5× | 10× | 25× | 50× | 100× |
|---|---|---|---|---|---|---|
| **1.0%** | 1.4% | 3.5% | 7.0% | 17.5% | 35.0% | 70.0% |
| **2.0%** | 2.8% | 7.0% | 14.0% | 35.0% | 70.0% | 140.0% |
| **4.0%** | 5.6% | 14.0% | 28.0% | 70.0% | 140.0% | 280.0% |

*(LP_share = 70% of GGR.)* See `figures/01_yield_vs_turnover.png`.

### 3.2 Capital requirement (gambler's ruin)

With positive drift, `P(pool ever drawn down by B) ≈ exp(−2·h·B / (b·var_index))`, giving
the minimum bankroll as a multiple of the **max bet** `b` to hold ruin risk ≤ 1%:
```
B/b  ≥  (var_index / 2h) · ln(1/RoR)
```

| Game | edge | top mult | var index | min B / max bet |
|---|---|---|---|---|
| Dice / coin-flip | 1.0% | 2 | 1 | **230×** |
| Roulette-like | 2.7% | 36 | 34 | **2,906×** |
| Slots (1,000×) | 4.0% | 1,000 | 959 | **55,209×** |
| Crash (10,000×) | 3.0% | 10,000 | 9,699 | **744,430×** |
| Lottery (1,000,000×) | 30% | 1,000,000 | 700,000 | **5,372,695×** |

See `figures/02_bankroll_vs_variance.png`. **Read this as a capacity ceiling.** To let a
whale bet `$X` on a 1,000× slot, the pool must hold ~55,000·`$X`. The multiplier doesn't
blow up *yearly* LP variance *if* you cap payout to a pool fraction — instead it caps how
big a bet the book can accept. The tax is paid in **foregone volume**, which is exactly the
turnover the yield depends on. A jackpot lottery is simply un-bankrollable this way.

---

## 4. Simulation findings (the non-obvious parts)

All from `simulation/casino_pool_sim.py` (Monte Carlo; jackpot counts drawn exactly as
`Binomial(N, p)`; typical bet = 25% of the cap-implied max bet, the cap protecting the tail).

### Insight 1 — Yield is velocity, not rake
Doubling the house edge is the lazy lever and it kills volume (players route to cheaper
games; this is a transparent, composable market). Raising turnover is the real lever, and
it's a *product* problem (more games, more frontends, deeper bet capacity), not a pricing
one. **Lower the edge to win volume; the yield math still works at higher turnover.**

### Insight 2 — Variance is a capacity tax, not (only) a ruin risk
Once you cap every payout at a fraction of the pool, the top multiplier stops driving
end-of-year LP variance and instead constrains *max bet size*. High-multiplier games can't
accept whale-sized bets until TVL is large. **So TVL is not just a safety buffer — it is a
product feature (bet capacity).** Bigger pool → bigger allowed bets → whales come →
turnover rises → yield rises → more TVL. The flywheel couples the two sides through the cap.

### Insight 3 — The pool is short a lottery, and it's most fragile when young
Same game, two life stages (payout capped at 1% of pool):

| Game @ stage | mean | median | p1 | P(losing year) | worst |
|---|---|---|---|---|---|
| Roulette · cold (2× turnover) | 3.8% | 3.9% | −7.5% | **21.0%** | −18.2% |
| Roulette · mature (40×) | 75.6% | 75.6% | 25.5% | 0.0% | −14.0% |
| Slots · cold (2×) | 5.6% | 5.6% | −5.8% | **12.2%** | −16.3% |
| Slots · mature (40×) | 111.9% | 112.0% | 61.4% | 0.0% | +4.9% |
| Crash · cold (2×) | 4.2% | 4.2% | −7.2% | **18.8%** | −18.0% |
| Crash · mature (40×) | 84.0% | 84.0% | 33.1% | 0.0% | −11.9% |

The honest risk metric is **`N·p`, the expected number of top-prize hits**, not headline
APY. When `N·p` is small (low volume = cold start, or extreme multiplier = lottery), a
handful of unlucky jackpots produces a deeply negative year. At scale the law of large
numbers smooths it. **The riskiest moment is exactly when TVL is thin and you're paying
emissions to attract it.** Corollary: couple the max-payout cap to *live* TVL, never to a
fixed dollar number. See `figures/03_lp_return_distributions.png`.

### Insight 4 — Verifiable RNG is a regressive tax that dictates your chain
Break-even bet = `VRF_cost / house_edge`. Below it, every bet *loses* money despite a
positive edge:

| RNG venue | h=1% | h=2% | h=4% |
|---|---|---|---|
| Ethereum L1 (~$3–8/req) | **$500** | $250 | $125 |
| Generic L2 (~$0.05–0.30) | $15 | $7.50 | $3.75 |
| App-L3 / batched (~$0.002) | $0.20 | $0.10 | $0.05 |

A 1%-edge dice game on L1 needs a **$500 minimum bet** just to cover RNG — economically
impossible. Verifiable RNG therefore *forces* the product onto a cheap L2/L3 or onto
commit-reveal / off-chain-signed RNG, which trades away some decentralization. It also means
**micro-stakes are a loss leader**; the house only makes money on rake-per-bet above the
break-even. This is a major reason "tier-1 crypto casinos" are migrating to app-specific
L2/L3s.

### Insight 5 — Shared liquidity is shared tail risk (contagion)
A disciplined book caps every payout at 1% of pool. Loosen one game's cap (lax governance,
a "high-margin feature," or a bug) and the whole shared bankroll inherits the tail
(gross house-year PnL, TVL $1M, 20× turnover):

| Book | mean | p1 | P(losing year) | worst |
|---|---|---|---|---|
| Disciplined: all payouts ≤1% | 36.1% | −7.0% | 2.5% | −54% |
| Slots cap loosened to 10% | 36.2% | −29.5% | **9.7%** | −91% |
| + crash game cap at 20% | 38.2% | −45.8% | **13.9%** | −134% (insolvent) |

Mean barely moves; the left tail explodes. **Deep shared liquidity is also a single
correlated point of failure** — the pool is only as safe as its loosest cap and its
buggiest integrated SDK contract. This is the on-chain analog of HLP's March 2025
whale-induced drawdown. Mitigations: per-variance-class sub-pools, per-game caps enforced
in *protocol* (not governance), a per-game security/audit budget, and circuit breakers.

### Insight 6 — Most "GambleFi APY" is emissions, not earnings
At cold start, real yield (`edge × turnover × share`) is tiny, so a 30% headline APY is
mostly token emissions:

| Phase | real yield | emissions | % real |
|---|---|---|---|
| Cold start (2× turnover) | 2.8% | 27.2% | **9%** |
| Traction (10×) | 14.0% | 16.0% | 47% |
| Scale (30×) | 42.0% | 0% | 140% |

Emissions are mercenary capital that leaves when rewards taper — right when a drawdown is
most likely (Insight 3). **Underwrite the model on real yield; treat emissions as customer
acquisition cost (CAC) for capital, with an explicit payback.** The "10–30% APY" you see
advertised across GambleFi tokens is largely revenue-share + burns + emissions, not pure
house PnL — don't confuse the two.

### Insight 7 — LP is the residual claimant *and* the tail bearer
Per $100 wagered at 2% edge → $2.00 GGR. A plausible waterfall: RNG/gas off the top ($0.10),
protocol 15% ($0.30), dev+frontend 25% ($0.50), **LP residual $1.10 (55% of GGR)**. LPs are
paid *last* and absorb *100%* of the negative-skew losses. If you over-reward the demand
side to win the growth race, LP comp drops below the tail-risk premium and LPs exit at the
first crash. **LP must clear `risk-free + tail premium` (≈15–25% real) before you fund
distribution.**

---

## 5. Business model & revenue

**Protocol revenue = a thin slice of GGR + token.** Concretely:
- Take **10–20% of GGR** at protocol level (the "infrastructure rake").
- Route **40–60% of GGR to LPs** (must clear their hurdle, §Insight 7).
- Route **20–35% of GGR to game devs + frontends** (the demand-side subsidy / moat).
- RNG/gas paid off the top.

**Why a thin GGR rake, not a fat one:** developers will route to whichever pool offers the
best terms (capital and edge-splits are transparent and forkable). Rake is a race to the
bottom; **distribution and bet-capacity are the only durable moats.** This mirrors Azuro's
choice to pay frontends out of pool profit rather than maximizing protocol take.

**Three engines, not one** (this is the key architectural call):
1. **High-frequency, low-multiplier, capped games** (dice, blackjack, roulette, low-vol
   slots) → bankroll-backed shared pool, variance-tranched. This is the core, and it works.
2. **High-multiplier games** (jackpot slots, crash) → *isolated* sub-pools with their own
   LPs who price the tail, OR reinsured / payout-capped hard. Never commingled with (1).
3. **Lotteries / jackpots** → **yield-funded prize model (PoolTogether-style)**, not
   bankroll-backed. Principal stays; prize = yield generated. The house cannot go bankrupt;
   the only knob is prize size = yield. This neatly sidesteps the un-bankrollable variance
   of §3.2 and is *also* a softer regulatory profile ("no-loss savings game").

**TAM / sizing sanity check.** Crypto gambling GGR is already in the multiple-$B/yr range
and growing; even a small infrastructure rake on a few percent of that volume is a
meaningful business. But realistic on-chain turnover is ~5–50× TVL/yr, so a $50M-yield LP
business implies hundreds of $M of TVL *and* the volume to recycle it. Volume, not TVL, is
the scarce input — which is why the demand side is the whole game.

---

## 6. Why lotteries specifically don't fit a shared bankroll

A jackpot lottery is, financially, the protocol **writing a deep out-of-the-money option**
and collecting a tiny premium. §3.2 shows a 1,000,000× lottery would need a bankroll
~5.4M× the max ticket to be safe — absurd. One jackpot hit wipes years of edge. This is the
worst possible asset to put in a *shared* pool that also backs dice, because the dice LPs
unknowingly subsidize the lottery's tail (Insight 5). The correct designs:
- **Yield-funded prize (recommended):** principal preserved, prize = aggregated yield. House
  ruin-proof by construction (PoolTogether). Caps prize at yield, but that's a feature.
- **Parimutuel:** prize pool = ticket sales minus rake; winners split it. The house takes a
  guaranteed rake and bears *zero* payout risk. Also ruin-proof.
- **Reinsured fixed-jackpot:** if you insist on a fixed jackpot, lay off the tail to a
  separate reinsurance tranche priced as an option. Now someone is actually paid for the
  risk — which means the economics rarely close.

---

## 7. Risks & failure modes (ranked)

1. **Regulation.** This is unlicensed online gambling infrastructure. US (Wire Act, UIGEA,
   state law), plus AML/KYC and securities questions on the LP token (an LP "earning house
   profits" looks like an unregistered security in several regimes). This is the #1 binding
   constraint, above any math here. Geofencing, licensing, or a no-loss/parimutuel framing
   are partial mitigations; none are free.
2. **Correlated smart-contract / RNG exploit.** Shared liquidity = shared blast radius. A
   single mispriced game, oracle manipulation, or RNG bias drains *every* game's backing.
   Needs per-game isolation, formal verification of the RNG path, and a security budget that
   scales with integrations.
3. **Cold-start, LP side is the riskier side.** Two-sided (really three-sided) bootstrap
   where the side you most need (capital) faces the fattest tail at the thinnest TVL
   (Insight 3) and is paid mostly in emissions (Insight 6). Most projects die here.
4. **Adverse selection by skilled/bot players.** On-chain transparency lets bots find any
   mispriced edge or +EV promo and drain it at scale. The edge must be robust to a
   fully-informed, automated adversary — "house always wins" assumes the house priced
   correctly, which on-chain is continuously tested.
5. **Mercenary liquidity flight.** Emissions-driven TVL leaves on a drawdown or when a fork
   offers better terms, exactly when the pool needs depth.
6. **Commoditization / forkability.** The contracts are forkable; only distribution,
   licenses, brand, and integrations are not.

---

## 8. What a credible v1 looks like

- **Chain:** an app-specific L2/L3 (or a cheap L2) so verifiable RNG break-even is sub-cent
  and micro-stakes are profitable (Insight 4).
- **Games:** high-frequency, low-multiplier, hard payout caps tied to live TVL. No jackpot
  lottery in the bankroll pool.
- **Pools:** variance-tranched / isolated sub-pools; per-game payout caps enforced in
  protocol; circuit breakers; a security budget per integration.
- **LP product:** real-yield-first, transparent risk dashboard (show drawdown distribution
  and `N·p`, not just APY), short lockups with queue, emissions disclosed as CAC with a
  payback schedule. Senior/junior tranches let risk-averse capital take a capped, lower yield
  while junior capital absorbs the tail for a premium.
- **Lottery product:** separate, yield-funded or parimutuel — ruin-proof and
  regulation-friendlier.
- **Go-to-market:** treat **game developers and frontends as the customer.** Best SDK, best
  docs, fastest integration, generous and *durable* (non-emission) revenue share. Liquidity
  follows volume; volume follows distribution. Subsidize the demand side; price the LP tail
  honestly.

---

## 9. Bottom line (no flattery)

The casino half is a real, proven primitive (Azuro/HLP/GLP/Edgeless) with a clean revenue
identity — `edge × turnover × LP_share` — and double-digit real yield *is* achievable, but
only at genuine scale and only if you (a) compete on velocity not rake, (b) pay LPs for a
fat, negatively-skewed tail, and (c) contain correlated risk with per-game caps and tranched
pools. The lottery half does **not** belong in the same bankroll and should be yield-funded
or parimutuel. The technology is the easy part; the business is won or lost on **regulation,
distribution, and the honesty of your LP risk pricing** — and most projects paper over the
last one with token emissions until the first drawdown exposes it.

---

### Reproduce
```
pip install numpy matplotlib
python3 simulation/casino_pool_sim.py     # prints all tables; writes figures/
```
Tune the `CONFIG`/`GAMES` blocks to your own edge, turnover, cap, and split assumptions.

### Sources
- Azuro — shared liquidity, SDK, frontends: https://gem.azuro.org/knowledge-hub/introduction/what-is-azuro · https://gem.azuro.org/knowledge-hub/how-azuro-works/protocol-actors/liquidity-providers
- Hyperliquid HLP vault & drawdown: https://www.datawallet.com/crypto/hyperliquid-hlp-explained · https://www.onchaintimes.com/perp-dex-vaults-a-look-under-the-hood/
- Edgeless / GambleFi staking bankroll: https://web.ourcryptotalk.com/blog/gamblefi-decentralized-gambling-defi · https://staking.edgelessgroup.io/
- Crypto-casino liquidity pools & house edge: https://bittokennest.com/liquidity-pools-and-house-edge-in-crypto-casinos-advanced-guide/
- Chainlink VRF billing / cost: https://docs.chain.link/vrf/v2/estimating-costs · https://docs.chain.link/vrf
- PoolTogether no-loss lottery model: https://decrypt.co/resources/what-is-pooltogether-the-no-loss-crypto-lottery-explained · https://pooltogether.com/
