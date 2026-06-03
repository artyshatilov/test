# $HOUSE — Tokenomics Design

*Token design for a shared on-chain casino/lottery liquidity protocol (see
[`RESEARCH.md`](./RESEARCH.md)). The brief: make it as interesting and attractive as
HYPE. This does that by copying the three things that actually make HYPE work — and
then adds one mechanism HYPE doesn't have, because a casino has a risk shape a perp DEX
doesn't. It also says plainly where the model is weaker than HYPE. Companion model:
[`simulation/tokenomics_sim.py`](./simulation/tokenomics_sim.py).*

Date: 2026-06 · Benchmark token: HYPE (Hyperliquid)

---

## 0. What actually makes HYPE attractive (so we copy the right things)

Not the price action — the *mechanics*:

1. **No-VC fair launch + a 31% genesis airdrop** to 94k real users; ~70%+ of supply is
   community-aligned. No private round to dump on retail → goodwill, distribution, and no
   structural sell overhang.
2. **An aggressive, automated buyback funded by real fees.** The Assistance Fund spends
   **97–99% of protocol fees** buying HYPE on the open market (~$1M/day, ~$65M/month,
   >$1.3B cumulative), running at **~7% of mcap per year** — plus committed burns. The token
   captures real cash flow, mechanically.
3. **The token is wired into the core, not bolted on.** HYPE is the **gas token** of its L1
   and the asset that secures consensus; the **HLP vault** (the protocol's risk-bearing
   counterparty) is the heart of the product. Value accrual is structural, not a governance
   fig-leaf.

**The honest gap:** HYPE's buyback is impressive *because perp fees are enormous relative to
mcap, in a bull market, with no licensing constraint.* Gambling GGR is real but smaller,
spikier, and one regulator can zero a jurisdiction. So we copy the mechanics but **must not**
copy the FDV-to-revenue ratio on faith. More on this in §3 and §7.

---

## 1. Design in one picture

```
            players wager  ──►  GGR (house edge)  ─── 15% protocol take ──┐
                 ▲                    │                                    │
                 │              85% to capital                     80% of take
        games/frontends         (tranched, below)                        │
        (SDK, earn a cut)             │                          ┌────────▼────────┐
                                      ▼                          │  HOUSE FUND     │
   ┌──────────────── BANKROLL ──────────────────┐               │  buy $HOUSE on  │
   │  SENIOR  ~75%  stablecoin LPs  ~10% capped  │               │  open market,   │
   │          protected from the tail           │               │  burn a slice   │
   │  JUNIOR  ~25%  STAKED $HOUSE  first-loss,   │◄── slashed ──┐ └───────┬─────────┘
   │          levered yield + emissions          │  on tail     │         │ buy pressure
   └─────────────────────────────────────────────┘              │         ▼
                                                                 └──── $HOUSE token ──► veHOUSE
                                                                           (gauges, gas, fee tiers)
```

Three value-accrual pillars (A: distribution, B: buyback, C: backstop), one cross-cutting
risk (reflexivity). Each is simulated; numbers below are from `tokenomics_sim.py`.

---

## 2. Pillar A — Supply & distribution (fair launch, HYPE-style)

**Total supply: 1,000,000,000 $HOUSE.** Community-aligned ≈ **78%**. No VC round (or a small,
publicly-disclosed strategic allocation on the same terms as the community — default zero).

| Bucket | % | Cliff | Vest | @TGE | Purpose |
|---|---|---|---|---|---|
| **Genesis airdrop** (LPs / players / devs, retroactive) | 35% | — | — | 100% | Distribution + goodwill (HYPE did 31%) |
| **Community / LP & backstop emissions** | 30% | — | 60m | 0% | CAC for liquidity & backstop (the risky bucket) |
| **Team & early contributors** | 15% | 12m | 36m | 0% | Alignment, cliffed |
| **DAO treasury** | 8% | — | 48m | 10% | Grants, ops, audits |
| **Backstop / insurance seed (protocol-owned)** | 5% | — | — | 100% | First-loss reserve the protocol itself owns |
| **Ecosystem / liquidity / MM** | 7% | — | 24m | 30% | Exchange liquidity, integrations |

**Circulating schedule** (`figures/05_supply_schedule.png`):

| Month | Circulating | % of supply |
|---|---|---|
| 0 (TGE) | 429M | 42.9% |
| 12 | 532M | 53.1% |
| 24 | 684M | 68.4% |
| 36 | 812M | 81.2% |
| 60 | 1,000M | 100% |

**Airdrop must be earned by *net GGR contributed*, not raw volume.** This is the one place a
gambling airdrop differs from HYPE's: if you award points for *wagered volume*, wash-betting
to farm the airdrop is +EV for farmers and **drains the house edge** that funds everyone
else. Score LPs by capital-weighted time, players by *net* losses (= GGR they generated), and
devs/frontends by GGR their integration produced. Reward the people who made the house money,
not the people who cycled volume.

---

## 3. Pillar B — The GGR buyback flywheel (the HYPE analog)

Protocol takes **15% of GGR**; **80% of that** (= **12% of GGR**) goes to the **House Fund**,
which buys $HOUSE on the open market and **burns a portion**. The remaining 20% of the take
funds ops/compliance (gambling has licensing costs HYPE doesn't — pretending otherwise is
dishonest). With edge 2% and turnover 20×, buyback = **4.8% of TVL/year**.

**"Buyback yield" = buyback$ / FDV.** This is the number to compare to HYPE's ~7%:

| TVL \ FDV | $100M | $300M | $1B | $3B |
|---|---|---|---|---|
| $50M | 2.4% | 0.8% | 0.2% | 0.1% |
| $200M | **9.6%** | 3.2% | 1.0% | 0.3% |
| $500M | **24.0%** | **8.0%** | 2.4% | 0.8% |

**The uncomfortable lesson (and the most important one in this doc):** a buyback only *is* a
flywheel when **FDV is disciplined relative to real GGR.** A $3B FDV on $50M TVL yields a
0.1% buyback — a meme, not a flywheel. HYPE's 7% is earned by enormous fees vs mcap, not by
the *existence* of a buyback. **Do not launch a 1B-supply token into thin GGR and call the
buyback a flywheel.** The mechanism is identical to HYPE's; whether it *matters* depends
entirely on keeping launch FDV honest until volume exists.

---

## 4. Pillar C — $HOUSE as the first-loss backstop (the part HYPE doesn't have)

This is the design's actual innovation and the answer to "make it interesting." The prior
research found a structural hole: **the bankroll is short a negative-skew tail, and in the
naïve design nobody is paid to bear it — so LPs flee at the first drawdown.** $HOUSE fills
that hole and becomes *productive collateral wired into the core risk engine*, the way HLP is
core to HYPE.

**Mechanism — tranche the bankroll:**
- **Senior (~75%): stablecoin LPs.** Capped ~10% coupon, **protected from the tail**. This is
  near-bond-like, so it attracts large, sticky, risk-averse capital → cheap depth → more bet
  capacity → more volume → more GGR.
- **Junior (~25%): staked $HOUSE.** Takes the **first loss**, earns the **levered residual +
  emissions**, and is **slashed** when a tail year exceeds the senior coupon. Staking $HOUSE =
  buying the equity tranche of a profitable casino.

**Simulated outcomes** (TVL $200M, turnover 12×; `figures/04_tranche_returns.png`):

| Tranche · game | mean | median | p5 | P(losing yr) | worst |
|---|---|---|---|---|---|
| **SENIOR** · roulette | 10.0% | 10.0% | 10.0% | **0.0%** | −20% (only if junior fully wiped) |
| **JUNIOR $HOUSE** · roulette | 88% | 88% | −6% | 6.1% | −92% (slashed) |
| **SENIOR** · slots | 10.0% | 10.0% | 10.0% | **0.0%** | −9% |
| **JUNIOR $HOUSE** · slots | 141% | 141% | 46% | 0.7% | −92% |

This manufactures a **clean two-sided product**: a safe yield for stable capital and a
high-octane, emissions-boosted, tail-bearing yield for the token. It *pays someone for the
negative skew*, which the plain design never did — and it gives $HOUSE a real, mechanical
reason to be staked beyond governance. The senior tranche's safety is precisely what lets it
scale, and its scale is what drives the buyback that supports the token. The pillars compound.

**Why this is more interesting than HYPE's staking:** HYPE staking mostly secures consensus
and shares some fees. $HOUSE staking *is the protocol's risk capital* — its yield is the
house edge itself, levered, and its risk is the house's risk. The token holder becomes the
house. That's a sharper, more legible pitch than "stake for a fee cut."

---

## 5. Token utility — the demand sinks

| Sink | What it does | Why it creates real demand |
|---|---|---|
| **Backstop staking** | Junior tranche (§4) | Levered house-edge yield; the core sink |
| **veHOUSE gauges** | Lock to direct LP-incentive emissions & bet-capacity boosts to specific games | **Curve-wars dynamic**: devs/operators buy & lock $HOUSE to boost *their* game's pool depth and rewards → persistent lock-up + buy pressure from the demand side |
| **Gas** (if app-chain) | $HOUSE is gas on the gaming L2/L3 | Structural per-transaction demand, like HYPE on HyperEVM |
| **Player fee tiers / rakeback** | Stake for lower house edge / rakeback / lottery-ticket multipliers | Converts player volume into token demand (carefully — see farming risk) |
| **Governance** | Per-game caps, tranche ratio, fee splits, new-game risk approval | Controls the parameters that gate the shared tail risk |

The **veHOUSE gauge** is the second non-obvious lever: it makes the *demand side*
(game developers and frontends) want to acquire and lock the token to win liquidity and
capacity for their game — turning the distribution moat from §RESEARCH into token demand.

---

## 6. Reflexivity / wrong-way risk — the part most token designs hide

A token-funded backstop has a fatal-if-ignored property: **it is worth least exactly when it
is needed most**, because the token price is correlated to the same volume/GGR that produces
the loss. Three correlated hits land together in a bad run:

1. Volume falls → GGR falls → **buyback falls**.
2. The pool draws down → **junior is slashed**.
3. $HOUSE price falls → **the USD value of the backstop shrinks**.

**Simulated stress** (`tokenomics_sim.py`): nominal junior backstop 25% of $200M = **$50M**.
A bad year where the pool loses 18% of TVL ($36M) *and* $HOUSE falls 60%:

| | |
|---|---|
| Tail loss to cover | **$36M** |
| Backstop value *after* the token crash | **$20M** (was $50M) |
| Coverage ratio | **0.56× → senior gets hit; the backstop fails** |

**Mitigations (mandatory, not optional):**
- **Discount token-backstop for stress.** Count junior capacity at a *stressed* price (e.g.
  40–50% haircut), never at spot. Never market "$50M backstop" when it's ~$20M in the state
  that matters.
- **Hold part of the first-loss reserve in stablecoins** (the protocol-owned 5% seed +
  retained GGR), so a floor of the buffer is *uncorrelated* with the token.
- **Hard per-game payout caps tied to live TVL**, so the worst-case tail can't exceed the
  stressed buffer (this is the §RESEARCH risk-engine discipline, now load-bearing for the
  token).
- **Senior caps growth to a multiple of stressed junior.** Senior can only scale as fast as
  *credibly-stressed* junior backstop — otherwise you're selling unbacked safety.

This is the single most important slide and the one a HYPE-style pitch will be tempted to
omit. Don't.

---

## 7. Net token flow — the only question that matters early

A buyback flywheel runs *backwards* if emissions sold exceed buybacks. At $0.50 and 50% of
emissions sold:

| Year | TVL | GGR | buyback$ | emissions sold$ | **net $/yr** |
|---|---|---|---|---|---|
| 1 | $40M | $16M | $1.9M | $25.6M | **−$23.7M** |
| 2 | $120M | $48M | $5.8M | $38.1M | **−$32.4M** |
| 3 | $300M | $120M | $14.4M | $32.0M | **−$17.6M** |
| 4 | $500M | $200M | $24.0M | $32.0M | **−$8.0M** |

**Years 1–2 are net-negative — the token is paying to bootstrap liquidity. That's real
dilution, not a flywheel.** The flywheel is a **year-3+ phenomenon, conditional on hitting
volume.** Underwrite it that way; present it that way. Treat emissions as CAC with an explicit
payback, taper them *into* rising GGR (gauge-controlled, volume-gated), and publish the
`buyback$ − sold_emissions$` number every month so the market can see when it flips positive.

---

## 8. Why this is attractive — and where it's honestly weaker than HYPE

**Attractive (the HYPE-grade hooks):**
- Fair launch, no VC dump, big retroactive airdrop to the people who built the GGR.
- A mechanical buyback from *real* cash flow, with burns — same engine as HYPE.
- A token that *is* the protocol's risk capital (junior tranche) — a sharper "own the house"
  pitch than HYPE's staking, and it solves a real structural problem (paying for the tail).
- A veHOUSE gauge that turns the developer/distribution moat into token demand.
- Real sinks: backstop, gas, gauges, fee tiers — not governance theater.

**Weaker than HYPE — stated plainly:**
- **Smaller, spikier, regulated revenue.** Gambling GGR < perp fees, and a token that earns
  house profits *and* bears losses is an even clearer security than a governance token.
  Jurisdictional risk is existential in a way it isn't for HYPE.
- **Wrong-way backstop (§6).** HYPE's value accrual isn't load-bearing for solvency; here the
  token *is* part of the bankroll, so token weakness and protocol stress are correlated. This
  must be capitalized conservatively, which *caps* how aggressive the tokenomics can be.
- **Reflexivity cuts both ways.** The same buyback that looks magical in a bull market
  reverses in a drawdown, exactly when the backstop is slashed. HYPE has this too; here it
  stacks with the solvency risk.
- **Farming risk on the airdrop/fee-tier sinks** (wash-wagering drains the edge) — must score
  on net GGR, not volume.

**Bottom line:** the mechanics that make HYPE attractive port cleanly, and the backstop
tranche makes $HOUSE arguably *more* interesting than a pure fee-buyback token because the
token holder literally becomes the house. But the honest version of this design is
*conservatively capitalized* — disciplined launch FDV, stress-discounted backstop, a
stablecoin floor under the first-loss layer, and emissions gated on real volume. Ship the
reflexive, over-levered version and the first bad run takes out the senior tranche, the
buyback, and the token in one correlated move. Ship the disciplined version and you have a
token that captures real cash flow *and* pays people, legibly, to be the house.

---

### Reproduce
```bash
pip install -r requirements.txt
python3 simulation/tokenomics_sim.py     # prints all tables; writes figures/04,05
```
Tune supply buckets, `protocol_take`, `buyback_share`, tranche `junior_frac`/`senior_coupon`,
and the stress assumptions at the top of each section.

### Sources (HYPE benchmark)
- Distribution / no-VC / 31% airdrop: https://tokenomics.com/articles/hyperliquid-tokenomics-how-hype-captures-65m-monthly-in-holder-revenue · https://audit.tokenomics.com/tokenomics/hyperliquid
- Assistance Fund buyback (97–99% of fees, ~7% of mcap, $1.3B+): https://www.dlnews.com/articles/defi/hyperliquid-hype-token-buyback-1bn-but-is-it-sustainable/ · https://crypto.news/why-hype-is-different-inside-hyperliquids-buyback/ · https://moneycheck.com/hyperliquid-has-used-nearly-all-trading-fee-revenue-over-1-16b-to-buy-back-hype
- Supply schedule / utility (gas, staking): https://www.buildix.trade/blog/hype-tokenomics-explained-buyback-burn-staking-supply-2026
