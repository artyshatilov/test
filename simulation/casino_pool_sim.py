"""
Shared On-Chain Casino/Lottery Liquidity Pool — Business-Model Simulation
========================================================================

This models the economics of a protocol that provides, as shared infrastructure:
  (1) a pooled bankroll (LPs stake capital; the pool is the counterparty/"house"),
  (2) verifiable RNG (e.g. Chainlink VRF), and
  (3) an SDK so 3rd-party developers ship games/lotteries WITHOUT their own capital.

We derive the unit economics from first principles and stress-test them with
Monte Carlo, then quantify the non-obvious tensions:

  - LP yield identity:        APY ≈ house_edge × turnover × LP_share − cost_drag
  - Variance is a capital tax: required bankroll scales with MAX PAYOUT, not avg bet
  - Negative skew:            the pool is SHORT a lottery -> mean APY != median APY
  - RNG is a regressive tax:  fixed per-bet RNG cost kills the edge on small bets
  - Shared-pool contagion:    one high-variance game raises ruin risk for ALL LPs

Run:  python3 casino_pool_sim.py
All numbers are illustrative but internally consistent; tune the CONFIG block.
"""

from __future__ import annotations
import math
import numpy as np

rng = np.random.default_rng(7)

# ----------------------------------------------------------------------------
# Game model
# ----------------------------------------------------------------------------
# A "game" is abstracted as a binary bet (this captures the variance that
# matters for bankroll risk; multi-outcome games reduce to the same first two
# moments). A unit stake returns the player `M` (the max multiplier) with prob
# p, else 0. RTP (return to player) = p*M = 1 - h, so p = (1-h)/M.
#
# Profit to the HOUSE per unit staked:  X = 1 - R,  R in {M (prob p), 0}
#   E[X]   = h                          (the edge)
#   Var[X] = (1-h)*(M - (1-h)) ≈ (1-h)*(M-1)   -> the "variance index", grows with M
#
# => The single number that drives capital requirements is M, the top multiplier.

class Game:
    def __init__(self, name, house_edge, max_multiplier):
        self.name = name
        self.h = house_edge
        self.M = max_multiplier
        self.p = (1 - self.h) / self.M           # win prob for the player
        self.var_index = (1 - self.h) * (self.M - (1 - self.h))  # Var[X] per unit stake

    def variance_index(self):
        return self.var_index

    def sample_house_profit(self, n, unit=1.0):
        """House profit per `unit` stake, n samples. +unit*(loss) when player loses."""
        win = rng.random(n) < self.p
        # player gets M*unit on win, 0 on loss; house profit = unit - payout
        payout = np.where(win, self.M * unit, 0.0)
        return unit - payout


# Representative on-chain game archetypes (max multiplier = the tail that hurts)
GAMES = {
    "dice_2x":      Game("Dice / coin-flip (2x)",      house_edge=0.010, max_multiplier=2),
    "roulette":     Game("Roulette-like (36x)",        house_edge=0.027, max_multiplier=36),
    "slots":        Game("Slots (1,000x jackpot)",     house_edge=0.040, max_multiplier=1_000),
    "crash_hi":     Game("Crash / high-mult (10,000x)",house_edge=0.030, max_multiplier=10_000),
    "lottery":      Game("Lottery (1,000,000x)",       house_edge=0.300, max_multiplier=1_000_000),
}


# ----------------------------------------------------------------------------
# 1) LP YIELD IDENTITY  — yield is edge x TURNOVER x share, not edge alone
# ----------------------------------------------------------------------------
def lp_apy(house_edge, turnover, lp_share, cost_drag=0.0):
    """turnover = annual wagered volume / TVL (capital velocity)."""
    return house_edge * turnover * lp_share - cost_drag


def section_yield_identity():
    print("=" * 78)
    print("1) LP YIELD IDENTITY:  APY ≈ house_edge × turnover × LP_share")
    print("=" * 78)
    print("   turnover = annual_wagered_volume / TVL  (how many times capital is recycled)")
    print()
    lp_share = 0.70
    edges = [0.01, 0.02, 0.04]
    turns = [2, 5, 10, 25, 50, 100]
    header = "  edge \\ turnover |" + "".join(f"{t:>8}x" for t in turns)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for e in edges:
        row = f"  h={e*100:>4.1f}%        |"
        for t in turns:
            row += f"{lp_apy(e, t, lp_share)*100:>8.1f}%"
        print(row)
    print(f"\n  (LP_share = {lp_share:.0%} of gross gaming revenue; rest -> protocol + game devs)")
    print("  INSIGHT: a 2%-edge pool at 25x turnover (35% APY) beats a 4%-edge pool")
    print("  at 5x turnover (14% APY). The lever is CAPITAL VELOCITY, not a bigger rake.")
    print()


# ----------------------------------------------------------------------------
# 2) VARIANCE IS A CAPITAL TAX — required bankroll scales with MAX PAYOUT
# ----------------------------------------------------------------------------
# Gambler's-ruin (with positive drift) approximation for the house:
#   Prob(pool ever drawn down by B from a max-bet stream) ≈ exp(-2*mu*B / sigma^2)
# Per bet of size b:  mu = h*b ,  sigma^2 = b^2 * var_index
#   => RoR ≈ exp(-2*h*B / (b*var_index))
#   => B/b ≥ (var_index / (2h)) * ln(1/RoR)
# Because var_index ≈ M, capital needed per unit of MAX BET grows linearly in M.
def required_bankroll_multiple(game: Game, target_ror=0.01):
    return game.variance_index() / (2 * game.h) * math.log(1 / target_ror)


def section_variance_tax():
    print("=" * 78)
    print("2) VARIANCE IS A CAPITAL TAX:  bankroll need ∝ MAX PAYOUT, not avg bet")
    print("=" * 78)
    print("   Min bankroll B (in multiples of the MAX BET) to hold ruin risk ≤ 1%:")
    print("   B/b ≥ (variance_index / 2h) · ln(1/RoR)")
    print()
    print(f"  {'game':32}{'edge':>6}{'maxX':>10}{'var_index':>11}{'B / maxbet':>13}")
    print("  " + "-" * 70)
    for g in GAMES.values():
        mult = required_bankroll_multiple(g, 0.01)
        print(f"  {g.name:32}{g.h*100:>5.1f}%{g.M:>10,}{g.variance_index():>11,.0f}{mult:>12,.0f}x")
    print()
    print("  INSIGHT: read this as a CAPACITY ceiling, not a ruin risk. To let a whale")
    print("  bet $X on a 1,000x slot, the pool must hold ~55,000·$X; on a 10,000x crash,")
    print("  ~744,000·$X. With a pool-fraction payout cap the multiplier does NOT blow up")
    print("  yearly LP variance — it caps how big a bet the book can accept. The variance")
    print("  tax is paid in FOREGONE VOLUME (small max bets -> whales go elsewhere), which")
    print("  is exactly the turnover that LP yield depends on. A jackpot lottery is simply")
    print("  un-bankrollable this way and needs a different engine (see report, §lottery).")
    print()


# ----------------------------------------------------------------------------
# 3) NEGATIVE SKEW IS A VOLUME PHENOMENON — the pool is most fragile when youngest
# ----------------------------------------------------------------------------
# Exact draw of the only thing that matters for the tail: how many TOP-PRIZE hits
# land this year.  With every payout capped at `kelly_cap` of the pool, a single
# bet can never ruin the pool; the left tail comes entirely from the random COUNT
# of big wins, W ~ Binomial(N, p).  Skew is large only when the expected number of
# big hits (N*p) is small — i.e. low volume (cold start) or extreme multiplier.
# Typical bet is a fraction of the max bet the cap allows (whales hit the cap,
# most flow is far below it). The cap protects the TAIL; this fraction sets the
# everyday variance. 0.25 is deliberately conservative (high) for retail flow.
BET_FRACTION = 0.25

def simulate_year(game: Game, tvl=1_000_000, turnover=20, lp_share=0.70,
                  kelly_cap=0.01, n_paths=200_000):
    """Returns array of LP annual return-on-capital across paths.
    Typical bet = BET_FRACTION * (cap-implied max bet); wins pay M * that bet."""
    annual_volume = tvl * turnover
    typ_bet = BET_FRACTION * kelly_cap * tvl / game.M
    n_bets = max(1, int(round(annual_volume / typ_bet)))
    W = rng.binomial(n_bets, game.p, size=n_paths)         # exact count of big wins
    house_profit = annual_volume - W * (game.M * typ_bet)  # = V - W*payout
    return (house_profit * lp_share) / tvl


def _stats_row(label, r):
    return (f"  {label:34}{r.mean()*100:>9.1f}%{np.median(r)*100:>8.1f}%"
            f"{np.percentile(r,1)*100:>9.1f}%{(r<0).mean()*100:>11.1f}%"
            f"{r.min()*100:>10.1f}%")


def section_negative_skew():
    print("=" * 78)
    print("3) NEGATIVE SKEW IS A VOLUME PHENOMENON: the pool is most fragile when young")
    print("=" * 78)
    print("   With every payout capped at 1% of the pool, no single bet can ruin it.")
    print("   The left tail comes from the random COUNT of big wins (N·p). Same game,")
    print("   two life stages: cold-start (turnover 2x) vs mature (turnover 40x).")
    print()
    print(f"  {'game @ life-stage':34}{'mean':>9}{'median':>8}{'p1':>9}{'P(loss)':>11}{'worst':>10}")
    print("  " + "-" * 80)
    results = {}
    for key in ["roulette", "slots", "crash_hi"]:
        g = GAMES[key]
        cold = simulate_year(g, turnover=2)
        mature = simulate_year(g, turnover=40)
        results[key] = mature
        short = g.name.split(" (")[0]
        print(_stats_row(f"{short}  · cold (2x)", cold))
        print(_stats_row(f"{short}  · mature (40x)", mature))
    print()
    print("  INSIGHT: the SAME game is dangerous when young and tame when scaled. At cold")
    print("  start a high-multiplier book can post a deeply negative year from a handful")
    print("  of unlucky jackpots; at scale the law of large numbers smooths it. So the")
    print("  honest risk metric is N·p (expected big-hits), not headline APY — and the")
    print("  riskiest moment is precisely when TVL is thin and you're paying emissions to")
    print("  attract it. Couple the max-payout cap to live TVL; never to a fixed number.")
    print()
    return results


# ----------------------------------------------------------------------------
# 4) RNG IS A REGRESSIVE TAX — fixed per-bet cost kills the edge on small bets
# ----------------------------------------------------------------------------
def break_even_bet(house_edge, vrf_cost_usd):
    """Below this stake, house edge < RNG cost => protocol loses money per bet."""
    return vrf_cost_usd / house_edge


def section_rng_tax():
    print("=" * 78)
    print("4) RNG IS A REGRESSIVE TAX: fixed per-bet VRF cost destroys small-bet edge")
    print("=" * 78)
    print("   Break-even bet = VRF_cost / house_edge  (below it, every bet loses money)")
    print()
    chains = {"Ethereum L1 ($3-8/req)": 5.0,
              "Generic L2 ($0.05-0.30)": 0.15,
              "App-L3 / batched ($0.002)": 0.002}
    edges = [0.01, 0.02, 0.04]
    print(f"  {'RNG venue':28}" + "".join(f"  h={e*100:>4.1f}%" for e in edges))
    print("  " + "-" * 58)
    for venue, cost in chains.items():
        row = f"  {venue:28}"
        for e in edges:
            row += f"  ${break_even_bet(e, cost):>8,.2f}"
        print(row)
    print()
    print("  Read as: minimum bet that is profitable AFTER paying for verifiable RNG.")
    print("  INSIGHT: on L1, a 1%-edge dice game needs a $500 minimum bet just to break")
    print("  even on RNG — economically impossible. Verifiable RNG FORCES the product")
    print("  onto cheap L2/L3 or off-chain-commit RNG, which trades away decentralization.")
    print("  It also means casinos make money on RAKE-PER-BET; micro-stakes are a loss.")
    print()


# ----------------------------------------------------------------------------
# 5) SHARED-POOL CONTAGION — adding one high-variance game raises ruin risk for ALL
# ----------------------------------------------------------------------------
def book_year_pnl(games_caps, tvl, turnover, n_paths=200_000):
    """games_caps: list of (Game, volume_fraction, payout_cap). Returns LP year ROC."""
    total = np.zeros(n_paths)
    annual_volume = tvl * turnover
    for g, frac, cap in games_caps:
        V = annual_volume * frac
        typ_bet = BET_FRACTION * cap * tvl / g.M
        n = max(1, int(round(V / typ_bet)))
        W = rng.binomial(n, g.p, size=n_paths)
        total += V - W * (g.M * typ_bet)
    return total / tvl   # gross house ROC (before LP split), per path


def section_contagion():
    print("=" * 78)
    print("5) SHARED-POOL CONTAGION: governance laxity on ONE game poisons every LP")
    print("=" * 78)
    print("   A disciplined book caps every payout at 1% of pool. Now one integrated")
    print("   game is allowed a looser cap (lax governance, or a higher-margin 'feature').")
    print("   TVL=$1M, turnover=20x. We report the GROSS house year (pre-LP-split):")
    print()
    print(f"  {'book':46}{'mean':>8}{'p1':>9}{'P(loss)':>10}{'worst':>9}")
    print("  " + "-" * 82)
    disciplined = [(GAMES["dice_2x"], 0.6, 0.01), (GAMES["roulette"], 0.3, 0.01),
                   (GAMES["slots"], 0.1, 0.01)]
    lax = [(GAMES["dice_2x"], 0.6, 0.01), (GAMES["roulette"], 0.3, 0.01),
           (GAMES["slots"], 0.1, 0.10)]                       # slots cap loosened 1%->10%
    laxer = [(GAMES["dice_2x"], 0.55, 0.01), (GAMES["roulette"], 0.3, 0.01),
             (GAMES["slots"], 0.1, 0.10), (GAMES["crash_hi"], 0.05, 0.20)]
    for label, book in [("Disciplined: all payouts ≤1% of pool", disciplined),
                        ("  slots payout cap loosened to 10%", lax),
                        ("  + crash game cap at 20%", laxer)]:
        r = book_year_pnl(book, tvl=1_000_000, turnover=20)
        print(f"  {label:46}{r.mean()*100:>7.1f}%{np.percentile(r,1)*100:>8.1f}%"
              f"{(r<0).mean()*100:>9.1f}%{r.min()*100:>8.1f}%")
    print()
    print("  INSIGHT: the multiplier itself is safe IF the payout cap scales with the")
    print("  pool. The killer is a single game with a loose cap (or a bug that lets payout")
    print("  exceed intent): it imports a fat left tail into the SHARED bankroll that the")
    print("  dice LPs never agreed to. 'Deep shared liquidity' is also a single correlated")
    print("  point of failure — the pool is only as safe as its loosest cap and its")
    print("  buggiest integrated SDK contract. Isolate sub-pools by variance class, enforce")
    print("  per-game caps in protocol (not governance), and budget for audits per game.")
    print()


# ----------------------------------------------------------------------------
# 6) REAL YIELD vs EMISSIONS — is the 'APY' house PnL or just token inflation?
# ----------------------------------------------------------------------------
def section_real_vs_emissions():
    print("=" * 78)
    print("6) REAL YIELD vs EMISSIONS: most GambleFi 'APY' is subsidy, not house edge")
    print("=" * 78)
    # Bootstrapping pool: low volume early -> real yield tiny -> must bribe LPs.
    tvl = 1_000_000
    scenarios = [
        ("Cold start (turnover 2x)",   0.02, 2),
        ("Traction (turnover 10x)",    0.02, 10),
        ("Scale (turnover 30x)",       0.02, 30),
    ]
    advertised = 0.30  # 30% headline APY promised to attract LPs
    lp_share = 0.70
    print(f"  Headline APY advertised to LPs: {advertised:.0%}.  Where does it come from?")
    print()
    print(f"  {'phase':30}{'real yield':>12}{'emissions':>12}{'% real':>10}")
    print("  " + "-" * 66)
    for name, edge, turn in scenarios:
        real = lp_apy(edge, turn, lp_share)
        emission = max(0.0, advertised - real)
        pct_real = real / advertised * 100
        print(f"  {name:30}{real*100:>11.1f}%{emission*100:>11.1f}%{pct_real:>9.0f}%")
    print()
    print("  INSIGHT: at cold start, ~9 of every 10 'APY' points are token emissions —")
    print("  i.e. dilution, not earnings. That capital is mercenary and leaves when")
    print("  emissions taper, right when a drawdown is most likely. The only durable")
    print("  LP yield is edge×turnover×share; everything above it is borrowed from the")
    print("  token's future. Underwrite the model on REAL yield, treat emissions as CAC.")
    print()


# ----------------------------------------------------------------------------
# 7) FEE WATERFALL & WHO BEARS THE TAIL
# ----------------------------------------------------------------------------
def section_waterfall():
    print("=" * 78)
    print("7) FEE WATERFALL: LP is the residual claimant AND the tail-risk bearer")
    print("=" * 78)
    # Of $100 wagered at 2% edge => $2.00 gross gaming revenue (GGR). Split it.
    ggr = 2.00
    rng_cost = 0.10          # verifiable RNG, on a cheap chain, per the relevant bets
    protocol = 0.15 * ggr
    dev_frontend = 0.25 * ggr
    lp = ggr - rng_cost - protocol - dev_frontend
    print(f"  Per $100 wagered, house edge 2%  ->  GGR = ${ggr:.2f}")
    print(f"    - verifiable RNG / gas (off the top): ${rng_cost:.2f}")
    print(f"    - protocol take (15% of GGR):         ${protocol:.2f}")
    print(f"    - game dev + frontend (25% of GGR):   ${dev_frontend:.2f}")
    print(f"    = LP residual:                        ${lp:.2f}   ({lp/ggr:.0%} of GGR)")
    print()
    print("  INSIGHT: LPs get paid LAST and also absorb 100% of the negative-skew")
    print("  losses. If the protocol over-rewards the DEMAND side (devs/frontends) to win")
    print("  the two-sided market, LP comp falls below the tail-risk premium and LPs exit")
    print("  at the first crash. Sustainable design: LP must clear risk-free + a tail")
    print("  premium (≈15-25% real) BEFORE you pay distribution. Liquidity is a commodity;")
    print("  do not starve it to subsidize growth — but the real MOAT is distribution.")
    print()


# ----------------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------------
def make_charts(skew_results):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(charts skipped: {e})")
        return

    # Chart A: APY = edge x turnover surface
    fig, ax = plt.subplots(figsize=(7, 4.5))
    turns = np.linspace(1, 60, 100)
    for e in [0.01, 0.02, 0.04]:
        ax.plot(turns, lp_apy(e, turns, 0.70) * 100, label=f"house edge {e*100:.0f}%")
    ax.axhspan(15, 25, color="green", alpha=0.08, label="LP hurdle (risk-free+tail premium)")
    ax.set_xlabel("Turnover  (annual wagered volume / TVL)")
    ax.set_ylabel("LP APY  (%)")
    ax.set_title("LP yield is driven by capital velocity, not the size of the rake")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("figures/01_yield_vs_turnover.png", dpi=120)
    plt.close(fig)

    # Chart B: required bankroll multiple vs max multiplier
    fig, ax = plt.subplots(figsize=(7, 4.5))
    names = [g.name for g in GAMES.values()]
    mults = [required_bankroll_multiple(g, 0.01) for g in GAMES.values()]
    ax.bar(range(len(names)), mults, color="firebrick", alpha=0.8)
    ax.set_yscale("log")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([n.split(" (")[0] for n in names], rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Min bankroll / max bet  (log scale)")
    ax.set_title("Variance is a capital tax: reserves scale with the top multiplier")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig("figures/02_bankroll_vs_variance.png", dpi=120)
    plt.close(fig)

    # Chart C: LP outcome distributions (negative skew)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for key, color in [("roulette", "steelblue"), ("slots", "firebrick"),
                       ("crash_hi", "darkorange")]:
        r = skew_results[key] * 100
        ax.hist(r, bins=80, alpha=0.45, label=GAMES[key].name.split(" (")[0], color=color)
    ax.axvline(0, color="black", lw=1)
    ax.set_xlabel("LP annual return on capital (%)  — mature book, turnover 40x")
    ax.set_ylabel("frequency (paths)")
    ax.set_title("Left-skew from the random count of jackpots (pool is short a lottery)")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig("figures/03_lp_return_distributions.png", dpi=120)
    plt.close(fig)
    print("\nCharts written to simulation/figures/: 01_yield_vs_turnover.png, "
          "02_bankroll_vs_variance.png, 03_lp_return_distributions.png")


def main():
    print("\nSHARED ON-CHAIN CASINO / LOTTERY POOL — BUSINESS MODEL SIMULATION\n")
    section_yield_identity()
    section_variance_tax()
    skew = section_negative_skew()
    section_rng_tax()
    section_contagion()
    section_real_vs_emissions()
    section_waterfall()
    make_charts(skew)


if __name__ == "__main__":
    main()
