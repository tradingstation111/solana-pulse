"""Static configuration: endpoints, sampling sizes, thresholds, watched accounts.

Everything a maintainer would plausibly want to change lives here, so the
collectors stay free of magic numbers.  No secrets, by design.
"""

from __future__ import annotations

# --- Solana JSON-RPC ---------------------------------------------------------
# Ordered failover list.  All entries were verified to answer anonymously.
# ``api.mainnet-beta.solana.com`` is the Solana Foundation public endpoint and
# is authoritative; publicnode is the hot spare.  A method is retried on the
# next endpoint only when the current one fails, so the normal run costs one
# endpoint's rate budget.
RPC_ENDPOINTS: tuple[str, ...] = (
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com",
)

# Blocks sampled per run for fee / success-rate / active-signer statistics.
# Each block with account details is ~6 MiB, so this is the main bandwidth knob.
BLOCK_SAMPLE_COUNT = 6
# Slots between sampled blocks (~400ms/slot => 150 slots is ~60 seconds apart).
BLOCK_SAMPLE_SPACING = 150

LAMPORTS_PER_SOL = 1_000_000_000
VOTE_PROGRAM_ID = "Vote111111111111111111111111111111111111111"

# Notable mainnet accounts sampled with getBalance / getSignaturesForAddress.
# Chosen because each is a well-known, publicly documented program or reserve
# whose activity is a meaningful ecosystem signal.
WATCHED_ACCOUNTS: tuple[dict[str, str], ...] = (
    {"label": "SPL Token Program", "address": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
     "kind": "program", "why": "Every SPL token transfer touches it - a liveness canary."},
    {"label": "Token-2022 Program", "address": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
     "kind": "program", "why": "Newer token standard; adoption trend vs classic SPL."},
    {"label": "Jupiter Aggregator v6", "address": "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
     "kind": "program", "why": "Dominant Solana DEX router; proxy for swap demand."},
    {"label": "Stake Program", "address": "Stake11111111111111111111111111111111111111",
     "kind": "program", "why": "Delegation and stake-account churn."},
    {"label": "Memo Program v2", "address": "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
     "kind": "program", "why": "Widely used by bridges and CEX withdrawals."},
)

# --- Off-chain, keyless HTTP APIs -------------------------------------------
COINGECKO_MARKETS = (
    "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=solana"
    "&price_change_percentage=1h%2C24h%2C7d%2C30d"
)
COINGECKO_CHART = (
    "https://api.coingecko.com/api/v3/coins/solana/market_chart"
    "?vs_currency=usd&days=90&interval=daily"
)
COINGECKO_ECOSYSTEM = (
    "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
    "&category=solana-ecosystem&order=market_cap_desc&per_page=20&page=1"
)

LLAMA_CHAIN_TVL_HISTORY = "https://api.llama.fi/v2/historicalChainTvl/Solana"
LLAMA_CHAINS = "https://api.llama.fi/v2/chains"
LLAMA_PROTOCOLS = "https://api.llama.fi/protocols"
LLAMA_DEX = "https://api.llama.fi/overview/dexs/solana?excludeTotalDataChartBreakdown=true"
LLAMA_FEES = "https://api.llama.fi/overview/fees/solana?excludeTotalDataChartBreakdown=true"
LLAMA_STABLES = "https://stablecoins.llama.fi/stablecoins?includePrices=true"
LLAMA_STABLE_CHART = "https://stablecoins.llama.fi/stablecoincharts/Solana"

STATUS_PAGE = "https://status.solana.com/api/v2/summary.json"

GITHUB_SIMD_OPEN = (
    "https://api.github.com/repos/solana-foundation/solana-improvement-documents/"
    "pulls?state=open&per_page=100&sort=updated&direction=desc"
)
GITHUB_SIMD_CLOSED = (
    "https://api.github.com/repos/solana-foundation/solana-improvement-documents/"
    "pulls?state=closed&per_page=50&sort=updated&direction=desc"
)
GITHUB_RELEASES = (
    ("Agave (Anza)", "https://api.github.com/repos/anza-xyz/agave/releases?per_page=5"),
    ("Firedancer (Jump)", "https://api.github.com/repos/firedancer-io/firedancer/releases?per_page=5"),
)

# SIMDs the ecosystem is actively watching; matched case-insensitively against
# PR titles so they can be surfaced even when buried in a long list.
HIGHLIGHT_SIMDS: tuple[str, ...] = ("alpenglow", "simd-525", "simd-0525", "simd-0326", "simd-0296")

# Accepted proposals live as Markdown files in this directory. Listing it gives
# the set of SIMDs that have actually been merged, which is a different and more
# useful question than "what pull requests are open".
GITHUB_SIMD_PROPOSALS = (
    "https://api.github.com/repos/solana-foundation/solana-improvement-documents/contents/proposals"
)

# Named upgrades to surface explicitly. The middle field is the proposal's
# filename *stem* - the part after the SIMD number - matched exactly, so that
# "alpenglow" cannot accidentally resolve to "alpenglow-migration".
TRACKED_UPGRADES: tuple[tuple[str, str, str], ...] = (
    ("Alpenglow", "alpenglow",
     "Replaces TowerBFT and Proof of History voting with Votor and Rotor, targeting "
     "sub-second finality. The largest consensus change in Solana's history."),
    ("Alpenglow migration", "alpenglow-migration",
     "The staged rollout plan that takes the cluster from the current consensus to Alpenglow."),
    ("SIMD-0525 — reduce slot times", "reduce-slot-times",
     "Shortens the target slot time below 400 ms, raising throughput and lowering latency."),
    ("SIMD-0296 — larger transactions", "larger-transactions",
     "Raises the transaction size limit above 1232 bytes, unlocking more complex instructions."),
    ("SIMD-0123 — block revenue distribution", "block-revenue-distribution",
     "Lets validators share block revenue with their stakers on chain."),
)

NEWS_FEEDS: tuple[tuple[str, str], ...] = (
    ("Solana News", "https://solana.com/news/rss.xml"),
    ("Helius Blog", "https://www.helius.dev/blog/rss.xml"),
    ("Agave Releases", "https://github.com/anza-xyz/agave/releases.atom"),
    ("Firedancer Releases", "https://github.com/firedancer-io/firedancer/releases.atom"),
    ("SIMD Repository", "https://github.com/solana-foundation/solana-improvement-documents/commits/main.atom"),
)

# X/Twitter: there is no keyless, terms-compliant read path.  Nitter mirrors are
# unreliable and rate-limited.  Rather than ship fabricated sentiment we surface
# the official accounts as links and say so in the dashboard.  See README.
X_ACCOUNTS: tuple[tuple[str, str], ...] = (
    ("@solana", "https://x.com/solana"),
    ("@SolanaFndn", "https://x.com/SolanaFndn"),
    ("@anza_xyz", "https://x.com/anza_xyz"),
    ("@jito_sol", "https://x.com/jito_sol"),
)

# --- Anomaly detection -------------------------------------------------------
# Robust z-score = 0.6745 * (x - median) / MAD.  |z| >= 3.5 is the classic
# Iglewicz-Hoaglin outlier cut; 5.0 is treated as critical here.
ROBUST_Z_WARN = 3.5
ROBUST_Z_CRITICAL = 5.0
# Below this many historical runs the baseline is not trustworthy and detection
# reports "baseline building" instead of firing.
MIN_BASELINE_POINTS = 5
# Rolling window (number of most recent runs) used for the baseline.
BASELINE_WINDOW = 96

HISTORY_PATH = "data/history.jsonl"
# Cap so the committed history file stays reviewable in a git diff.
HISTORY_MAX_RECORDS = 5000
