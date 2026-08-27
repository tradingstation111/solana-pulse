# Solana Pulse — State of the Solana Ecosystem

**Generated:** 2026-08-27T01:34:54Z · **Run time:** 22.21s · **History depth:** 4 runs · **Sources:** 16/19 live

Automatically generated from public, keyless data sources using the Python standard library only. No API keys, no third-party packages.

## 1. Alerts

> Baseline building: 3 of 5 runs collected. Statistical detection activates once enough history exists; threshold and cross-source rules are already active.

**No anomalies detected.** All monitored metrics are within their expected ranges.

## 2. At a glance

| Metric | Value | Context |
|---|---|---|
| Throughput | 4,060 TPS | non-vote 2,195 TPS |
| Slot time | 366 ms | ~400 ms target |
| Epoch | 1,023 | 13.8% complete |
| Validators | 697 | 12 delinquent |
| Nakamoto coefficient | 18 | validators controlling >33% of stake |
| SOL price | — | — 24h |
| Market cap | — | rank #— |
| DeFi TVL | $5.69B | +8.86% 7d |
| DEX volume 24h | $2.49B | -15.13% |
| Chain fees 24h (REV) | $12.99M | -1.88% |
| Stablecoins on Solana | $16.21B | 52 assets |
| Tokenised RWA | $2.07B | equities $455.51M |
| Median transaction fee | 5,360 lamports | — |
| Staking ratio | 74.8% | 436.88M SOL staked |

## 3. Network performance

Cluster health is **ok** on `https://api.mainnet-beta.solana.com`, running solana-core **4.2.0** (feature set 565,236,538).

| Metric | Current | Mean (30 samples) |
|---|---|---|
| Transactions per second | 4,059.9 | 4,436.7 |
| Non-vote TPS | 2,194.6 | 2,572.5 |
| Slot time (ms) | 365.9 | 365.7 |
| Peak TPS in window | 5,216.6 | — |
| Absolute slot | 441,995,644 | — |
| Block height | 420,043,970 | — |
| Lifetime transactions | 542,231,905,247 | — |
| Slots left in epoch | 372,356 | — |

### 3.1 Direct block sampling

6 finalised blocks were downloaded in full and parsed locally, spanning 275 seconds of chain time. These figures are computed from raw block contents, not from any aggregator.

| Measurement | Value |
|---|---|
| Median user transaction fee | 5,360 lamports (—) |
| 90th percentile fee | 25,783 lamports |
| Median priority fee | 252 lamports |
| Priority fees as share of fees paid | 78.2% |
| On-chain transaction failure rate | 45.1% |
| Vote transactions as share of all | 46.8% |
| Average transactions per block | 1,453 |
| Average unique fee payers per block | 260 |
| Unique fee payers across the sample | 1,066 |
| Wallets active in sampling window (capture-recapture estimate) | 2,251 |
| New-wallet discovery rate | 3.88 /s |

## 4. Validators and decentralisation

**685 active** validators and **12 delinquent**, securing 436.88M SOL of stake (— at the current price). Delinquent stake is 0.038% of the total.

| Concentration measure | Value |
|---|---|
| Nakamoto coefficient (>33% of stake) | 18 |
| Largest validator share | 3.91% |
| Top 10 share | 24.28% |
| Top 20 share | 35.57% |
| Top 100 share | 72.25% |
| Median validator stake | 176,498 SOL |
| Median commission | 5% |
| Zero-commission validators | 260 |

**Top 15 validators by activated stake**

| # | Vote account | Stake | Share | Commission | Status |
|---|---|---|---|---|---|
| 1 | `CcaHc2L43ZWjwCHART3…` | 17.06M SOL | 3.906% | 7% | active |
| 2 | `he1iusunGwqrNtafDtL…` | 16.03M SOL | 3.669% | 0% | active |
| 3 | `3N7s9zXMZ4QqvHQR15t…` | 12.31M SOL | 2.819% | 0% | active |
| 4 | `CatzoSMUkTRidT5DwBx…` | 11.75M SOL | 2.690% | 5% | active |
| 5 | `26pV97Ce83ZQ6Kz9XT4…` | 9.22M SOL | 2.110% | 7% | active |
| 6 | `8GbwASqdpw4dVcwbWUx…` | 9.05M SOL | 2.072% | 0% | active |
| 7 | `51JBzSTU5rAM8gLAVQK…` | 8.90M SOL | 2.038% | 10% | active |
| 8 | `9QU2QSxhb24FUX3Tu2F…` | 7.85M SOL | 1.797% | 7% | active |
| 9 | `CvSb7wdQAFpHuSpTYTJ…` | 7.30M SOL | 1.671% | 5% | active |
| 10 | `DumiCKHVqoCQKD8roLA…` | 6.58M SOL | 1.506% | 0% | active |
| 11 | `HZKopZYvv8v6un2H6KU…` | 6.12M SOL | 1.401% | 100% | active |
| 12 | `3JD3jMmnR6g88qff2WZ…` | 6.06M SOL | 1.386% | 0% | active |
| 13 | `DdCNGDpP7qMgoAy6paF…` | 5.93M SOL | 1.356% | 5% | active |
| 14 | `GHViLgbrJdZDPb6sphR…` | 5.64M SOL | 1.291% | 100% | active |
| 15 | `FKsC411dik9ktS6xPAD…` | 4.82M SOL | 1.103% | 7% | active |

**Largest delinquent validators**

| Vote account | Stake | Share | Last vote |
|---|---|---|---|
| `4QQqaHgJfrpaS8aU47C…` | 66,322 SOL | 0.0152% | 441,861,440 |
| `Gar9q7Ru2sKfVxFnR5x…` | 29,733 SOL | 0.0068% | 440,639,999 |
| `9hHEiSDTz9LeA4B4N2t…` | 24,002 SOL | 0.0055% | 440,639,999 |
| `mrgn4t2JabSgvGnrCaH…` | 23,802 SOL | 0.0054% | 441,973,083 |
| `gangtRyGPTvYWb8K3xS…` | 16,426 SOL | 0.0038% | 441,252,679 |
| `ChaosDKeBjU22B4nnvY…` | 1,417 SOL | 0.0003% | 441,983,754 |
| `4GEEKSwzc242QKF1uzz…` | 1,344 SOL | 0.0003% | 441,012,366 |
| `25quQGzrtcU224Kk7G5…` | 1,060 SOL | 0.0002% | 440,636,516 |
| `8Ug1zHMVDHAra2TaMFk…` | 2 SOL | 0.0000% | 0 |
| `R1vAoSPFQdCc6wsAEMt…` | 2 SOL | 0.0000% | 384,048,870 |

**Commission distribution**

| Commission band | Validators |
|---|---|
| 0% | 260 |
| 1-5% | 312 |
| 6-10% | 59 |
| 11-50% | 1 |
| 51-100% | 65 |

### 4.1 Validator client diversity

3,736 nodes are visible over gossip across 55 distinct software versions. The dominant client is **Agave** at 55.5% of nodes.

| Client | Nodes | Share |
|---|---|---|
| Agave | 2,073 | 55.5% |
| JitoLabs | 993 | 26.6% |
| AgaveBam | 379 | 10.1% |
| Frankendancer | 107 | 2.9% |
| Unknown(10) | 88 | 2.4% |
| Firedancer | 37 | 1.0% |
| Unknown(8) | 28 | 0.7% |
| Unknown(11) | 14 | 0.4% |
| Unknown(12) | 9 | 0.2% |
| Unknown(13) | 3 | 0.1% |
| Unknown(9) | 2 | 0.1% |
| Unknown(3366) | 1 | 0.0% |
| Unknown(40142) | 1 | 0.0% |
| Unknown(19785) | 1 | 0.0% |

## 5. Economy

> ⚠️ **Source unavailable:** `market`. This section is incomplete. Reported errors: CoinGecko: SOL 90d chart — FetchError: HTTP 429 Too Many Requests: {"status":{"error_code":429,"error_message":"You've exceeded the Rate Limit. Please visit https://www.coingecko.com/en/api/pricing to subscribe to our API plans for higher rate limits."}}; CoinGecko: SOL market — FetchError: HTTP 429 Too Many Requests: {"status":{"error_code":429,"error_message":"You've exceeded the Rate Limit. Please visit https://www.coingecko.com/en/api/pricing to subscribe to our API plans for higher rate limits."}}; CoinGecko: ecosystem tokens — FetchError: HTTP 429 Too Many Requests: {"status":{"error_code":429,"error_message":"You've exceeded the Rate Limit. Please visit https://www.coingecko.com/en/api/pricing to subscribe to our API plans for higher rate limits."}}

**Supply and inflation**

| Supply metric | Value |
|---|---|
| Total supply | 632.97M SOL |
| Circulating supply | 584.06M SOL (92.3%) |
| Non-circulating | 48.91M SOL |
| Current inflation rate | 3.677% |
| Staking ratio (stake / circulating) | 74.8% |

**Total value locked**

Solana holds $5.69B in DeFi TVL, ranking **#2** of 465 tracked chains and 6.44% of all on-chain TVL. Change: -0.01% (24h), +8.86% (7d), +18.08% (30d).

**Top protocols by TVL on Solana**

_Centralised-exchange wallets and bridge contracts are excluded from these figures (Bridge, CEX, Canonical Bridge, Chain), because they hold assets on Solana without being Solana DeFi._

| # | Protocol | Category | TVL | 24h | 7d |
|---|---|---|---|---|---|
| 1 | Sanctum Validator LSTs | Liquid Staking | $1.53B | +4.5% | +20.2% |
| 2 | Kamino Lend | Lending | $1.21B | +2.4% | +7.7% |
| 3 | Raydium AMM | Dexs | $1.11B | +4.4% | +21.7% |
| 4 | Jupiter Lend | Lending | $1.10B | +4.1% | +11.4% |
| 5 | Binance Staked SOL | Liquid Staking | $1.03B | +3.3% | +19.6% |
| 6 | Jito Liquid Staking | Liquid Staking | $1.01B | +4.7% | +18.6% |
| 7 | BlackRock BUIDL | RWA | $886.37M | +0.3% | +1.6% |
| 8 | Jupiter Perpetual Exchange | Derivatives | $768.58M | +2.8% | +5.0% |
| 9 | Jupiter Staked SOL | Liquid Staking | $523.93M | +3.7% | +18.1% |
| 10 | xStocks | RWA | $430.09M | -0.0% | +6.4% |
| 11 | Marinade Native | Staking Pool | $401.36M | +5.6% | +65.7% |
| 12 | Sentora | Risk Curators | $363.23M | +0.6% | +5.9% |
| 13 | PumpSwap | Dexs | $330.27M | -0.5% | +22.0% |
| 14 | Solstice | Basis Trading | $303.01M | -0.0% | -40.1% |
| 15 | Drift Staked SOL | Liquid Staking | $284.20M | +3.7% | +18.3% |

**TVL by category**

| Category | TVL |
|---|---|
| Liquid Staking | $5.89B |
| Lending | $2.58B |
| Dexs | $2.29B |
| RWA | $2.07B |
| Derivatives | $860.64M |
| Staking Pool | $619.82M |
| Risk Curators | $468.82M |
| Yield | $446.73M |
| Basis Trading | $381.48M |
| Yield Aggregator | $109.65M |

**DEX volume**

$2.49B traded in 24h across 77 venues (-15.1% day over day, -17.2% week over week). 7-day total $21.03B, 30-day total $58.26B.

| Venue | 24h volume | 7d volume | 24h change |
|---|---|---|---|
| PumpSwap | $765.13M | $4.40B | +34.7% |
| Orca DEX | $297.72M | $2.86B | -35.2% |
| BisonFi | $251.44M | $3.12B | -38.9% |
| Meteora DLMM | $184.81M | $1.76B | -25.0% |
| Scorch | $173.07M | $1.42B | +0.0% |
| Raydium AMM | $166.92M | $1.53B | -13.6% |
| Manifest Trade | $123.36M | $1.23B | -37.5% |
| Axiom | $88.92M | $447.30M | +0.0% |
| Jupiterz | $79.31M | $393.75M | +0.0% |
| Aquifer | $70.52M | $418.13M | +0.0% |

**Fees and Real Economic Value**

$12.99M in fees were paid on Solana in the last 24h (-1.9% day over day), $78.87M over 7 days and $284.23M over 30 days. Lifetime fees stand at $14.80B.

| Fee-generating protocol | 24h fees | 7d fees |
|---|---|---|
| PumpSwap | $3.81M | $20.09M |
| pump.fun | $1.95M | $10.23M |
| Axiom | $1.60M | $8.26M |
| Bags | $1.45M | $1.47M |
| Solana | $889.16K | $4.98M |
| fomo Wallet | $664.84K | $3.26M |
| Jupiter Perpetual Exchange | $631.25K | $3.82M |
| Meteora DLMM | $507.74K | $3.60M |
| Raydium AMM | $322.06K | $2.75M |
| Phantom Wallet | $284.72K | $1.94M |

**Stablecoins on Solana**

$16.21B across 52 assets; the largest holds 43.1% of the float.

| Asset | Circulating on Solana | 24h | 7d | Peg type |
|---|---|---|---|---|
| USDC (USD Coin) | $6.98B | -2.56% | +3.10% | fiat-backed |
| USDT (Tether) | $2.84B | -0.00% | -0.87% | fiat-backed |
| USDGO (USDGO) | $1.25B | +4.60% | +5.18% | fiat-backed |
| USD1 (World Liberty Financial USD) | $1.12B | +2.61% | +6.90% | fiat-backed |
| BUIDL (BlackRock USD) | $886.37M | +6.95% | +19.55% | fiat-backed |
| PYUSD (PayPal USD) | $684.52M | +1.43% | +1.15% | fiat-backed |
| USDG (Global Dollar) | $613.71M | -3.27% | -2.97% | fiat-backed |
| USDe (Ethena USDe) | $537.11M | +0.07% | -0.11% | crypto-backed |
| USX (Solstice USX) | $303.01M | -24.80% | -40.14% | crypto-backed |
| SOFID (SoFiUSD) | $216.43M | +0.24% | +2.71% | fiat-backed |
| USDY (Ondo US Dollar Yield) | $179.34M | -0.00% | +0.01% | fiat-backed |
| YLDS (YLDS) | $161.25M | -3.08% | -4.10% | fiat-backed |

## 6. Ecosystem growth

**Tokenised real-world assets:** $2.07B across 15 tracked issuers, of which $455.51M is tokenised equity exposure.

| RWA issuer | Value on Solana | 24h |
|---|---|---|
| BlackRock BUIDL | $886.37M | +0.3% |
| xStocks | $430.09M | -0.0% |
| OnRe | $277.86M | +0.2% |
| Ondo Yield Assets | $179.34M | +0.3% |
| Hastra | $161.88M | -0.5% |
| Theo Network thBill | $26.39M | +0.0% |
| Ondo Global Markets | $25.21M | +0.5% |
| Plume Vaults | $22.86M | +0.2% |
| Apollo Diversified Credit Securitize Fund | $18.37M | +0.0% |
| VanEck Treasury Fund | $13.94M | -0.1% |

**Wallet activity:** 260 distinct fee payers appeared in the average sampled block, and 1,066 distinct wallets across the whole sample. Projected user (non-vote) transactions per day at the current rate: 189,614,880.

**Watched programs and accounts**

| Label | Address | Balance | Sig. rate | Failures in sample |
|---|---|---|---|---|
| SPL Token Program | `TokenkegQfeZyiN…` | 0.1938 SOL | — | 24% |
| Token-2022 Program | `TokenzQdBNbLqP5…` | 0.0701 SOL | — | 56% |
| Jupiter Aggregator v6 | `JUP6LkbZbjS1jKK…` | 6.9203 SOL | — | 32% |
| Stake Program | `Stake1111111111…` | 0.0011 SOL | 42.9/min | 0% |
| Memo Program v2 | `MemoSq4gqABAXKb…` | 0.5230 SOL | — | 0% |

## 7. Upgrades, governance and news

**21 open SIMDs** (Solana Improvement Documents).

_Proposals being tracked closely:_

| SIMD | Title | State | Updated |
|---|---|---|---|
| #478 | [amend SIMD-0123: fix instruction discriminant](https://github.com/solana-foundation/solana-improvement-documents/pull/478) | merged | 2026-05-18 |

_Recently merged:_

| PR | Title | Merged |
|---|---|---|
| #551 | [re-amend SIMD-0340: additional inter- and intra- validation](https://github.com/solana-foundation/solana-improvement-documents/pull/551) | 2026-07-31 |
| #433 | [SIMD-0433: Loader V3: Set Program Data to ELF Length](https://github.com/solana-foundation/solana-improvement-documents/pull/433) | 2026-07-31 |
| #550 | [SIMD-0550: Double disinflation](https://github.com/solana-foundation/solana-improvement-documents/pull/550) | 2026-07-23 |
| #553 | [SIMD-0553: Resource and Inclusion Fee](https://github.com/solana-foundation/solana-improvement-documents/pull/553) | 2026-07-20 |
| #572 | [SIMD-0392: Clarify included stake accounts and calculations](https://github.com/solana-foundation/solana-improvement-documents/pull/572) | 2026-07-16 |
| #574 | [SIMD-0290: narrow scope to blockhash tx](https://github.com/solana-foundation/solana-improvement-documents/pull/574) | 2026-07-16 |
| #565 | [SIMD-0565: Secp256r1 curve syscalls](https://github.com/solana-foundation/solana-improvement-documents/pull/565) | 2026-07-10 |
| #517 | [Clarify requested accounts data size and heap treatment in TXV1](https://github.com/solana-foundation/solana-improvement-documents/pull/517) | 2026-06-24 |

_Open proposals, most recently updated:_

| PR | Title | Author | Opened |
|---|---|---|---|
| #579 | [SIMD-0579: Keccak-p1600 syscall](https://github.com/solana-foundation/solana-improvement-documents/pull/579) | Rexicon226 | 2026-07-09 |
| #607 | [Remove floating point arithmetic from Runtime critical inflation and rent path](https://github.com/solana-foundation/solana-improvement-documents/pull/607) | tao-stones | 2026-08-24 |
| #599 | [SIMD-0599: Remove inactive stakes from partitioned epoch rewards](https://github.com/solana-foundation/solana-improvement-documents/pull/599) | joncinque | 2026-08-13 |
| #612 | [SIMD-0612: Two-Phase Leader Schedule](https://github.com/solana-foundation/solana-improvement-documents/pull/612) | Jotatavo | 2026-08-26 |
| #608 | [SIMD-0608: `DeactivateDelinquent` for Closed Vote Accounts](https://github.com/solana-foundation/solana-improvement-documents/pull/608) | grod220 | 2026-08-25 |
| #610 | [SIMD-0610: Prohibit Nonce Account Self-Withdrawals](https://github.com/solana-foundation/solana-improvement-documents/pull/610) | grod220 | 2026-08-25 |
| #609 | [SIMD-0609: Prohibit Vote Account Self-Withdrawals](https://github.com/solana-foundation/solana-improvement-documents/pull/609) | grod220 | 2026-08-25 |
| #582 | [SIMD-0582: Early detection of instruction trace overflow](https://github.com/solana-foundation/solana-improvement-documents/pull/582) | LucasSte | 2026-07-14 |
| #602 | [SIMD-0602: Disallow Nonce Account as Program ID](https://github.com/solana-foundation/solana-improvement-documents/pull/602) | 2501babe | 2026-08-18 |
| #600 | [simd-0553 amendment: adjust inclusion fee](https://github.com/solana-foundation/solana-improvement-documents/pull/600) | cavemanloverboy | 2026-08-14 |

**Validator client releases**

| Client | Latest stable | Published | Link |
|---|---|---|---|
| Agave (Anza) | v4.2.1 | 2026-08-13 | [release notes](https://github.com/anza-xyz/agave/releases/tag/v4.2.1) |
| Firedancer (Jump) | v26.08.2 | 2026-08-25 | [release notes](https://github.com/firedancer-io/firedancer/releases/tag/v26.08.2) |

**Cluster status page:** All Systems Operational (indicator: `none`, updated 2026-08-27).

**Latest ecosystem news**

- **2026-08-26** · _Firedancer Releases_ · [Frankendancer Testnet v0.1202.40302](https://github.com/firedancer-io/firedancer/releases/tag/v0.1202.40302)
- **2026-08-25** · _Firedancer Releases_ · [Firedancer Mainnet v26.08.2](https://github.com/firedancer-io/firedancer/releases/tag/v26.08.2)
- **2026-08-25** · _Helius Blog_ · [What is an LSM Tree? The Log-Structured Merge Tree Explained](https://www.helius.dev/blog/lsm-tree-explained)
- **2026-08-24** · _Solana News_ · [Solana Changelog: August 20, 2026](https://solana.com/news/solana-changelog-august-20-2026)
- **2026-08-24** · _Agave Releases_ · [Release v4.3.0-beta.2](https://github.com/anza-xyz/agave/releases/tag/v4.3.0-beta.2)
- **2026-08-21** · _Firedancer Releases_ · [Firedancer Testnet v26.08.1](https://github.com/firedancer-io/firedancer/releases/tag/v26.08.1)
- **2026-08-21** · _Agave Releases_ · [Release v4.3.0-beta.1](https://github.com/anza-xyz/agave/releases/tag/v4.3.0-beta.1)
- **2026-08-19** · _Firedancer Releases_ · [Frankendancer Mainnet v0.1106.40201](https://github.com/firedancer-io/firedancer/releases/tag/v0.1106.40201)
- **2026-08-19** · _Solana News_ · [Lowering Slot Time and Validators Economic](https://solana.com/news/lowering-slot-time-and-validators-economic)
- **2026-08-17** · _Agave Releases_ · [Release v4.3.0-beta.0](https://github.com/anza-xyz/agave/releases/tag/v4.3.0-beta.0)
- **2026-08-17** · _Solana News_ · [Transaction v1 and the ALT Trade-off](https://solana.com/news/transaction-v1-and-the-alt-trade-off)
- **2026-08-14** · _Agave Releases_ · [Release v4.2.1](https://github.com/anza-xyz/agave/releases/tag/v4.2.1)

_Social sentiment from X is deliberately omitted: there is no keyless, terms-compliant read path, and inventing it would be worse than leaving it out. Official accounts: [@solana](https://x.com/solana), [@SolanaFndn](https://x.com/SolanaFndn), [@anza_xyz](https://x.com/anza_xyz), [@jito_sol](https://x.com/jito_sol)._

## 8. Trend history

This deployment has 4 recorded runs, the first at 2026-08-27T01:30:53Z. Every run appends one line to `data/history.jsonl`; the anomaly detector reads it back as its baseline.

| Metric | First run | Latest | Min | Max | Change |
|---|---|---|---|---|---|
| TPS | 4,178 | 4,060 | 4,060 | 4,395 | -2.82% |
| Slot time (ms) | 355 | 366 | 355 | 366 | +3.05% |
| Validators | 697 | 697 | 697 | 697 | +0.00% |
| Delinquent stake % | 0.038 | 0.038 | 0.038 | 0.038 | +0.00% |
| SOL price (USD) | 101.53 | 101.79 | 101.53 | 101.79 | +0.26% |
| TVL (USD) | 5,688,924,882 | 5,688,924,882 | 5,688,924,882 | 5,688,924,882 | +0.00% |
| Nakamoto coefficient | 18 | 18 | 18 | 18 | +0.00% |

## 9. Data sources and freshness

| Source | Status | Latency | Fetched | Detail |
|---|---|---|---|---|
| CoinGecko: SOL 90d chart | 🔴 unavailable | 3353 ms | 16 sec ago | FetchError: HTTP 429 Too Many Requests: {"status":{"error_code":429,"error_message":"You'… |
| CoinGecko: SOL market | 🔴 unavailable | 3390 ms | 19 sec ago | FetchError: HTTP 429 Too Many Requests: {"status":{"error_code":429,"error_message":"You'… |
| CoinGecko: ecosystem tokens | 🔴 unavailable | 3326 ms | 12 sec ago | FetchError: HTTP 429 Too Many Requests: {"status":{"error_code":429,"error_message":"You'… |
| DefiLlama: DEX volume | 🟢 live | 74 ms | 22 sec ago | — |
| DefiLlama: chain TVL | 🟢 live | 158 ms | 22 sec ago | — |
| DefiLlama: fees & REV | 🟢 live | 128 ms | 22 sec ago | — |
| DefiLlama: protocols | 🟢 live | 917 ms | 21 sec ago | — |
| DefiLlama: stablecoins | 🟢 live | 362 ms | 22 sec ago | — |
| Ecosystem news feeds | 🟢 live | 2524 ms | 20 sec ago | — |
| GitHub: SIMD proposals | 🟢 live | 398 ms | 22 sec ago | — |
| GitHub: client releases | 🟢 live | 789 ms | 21 sec ago | — |
| Solana RPC: block sample | 🟢 live | 8264 ms | 0 sec ago | 6 blocks, ~150 slots apart |
| Solana RPC: cluster | 🟢 live | 1807 ms | 20 sec ago | — |
| Solana RPC: cluster nodes | 🟢 live | 969 ms | 19 sec ago | — |
| Solana RPC: performance samples | 🟢 live | 305 ms | 20 sec ago | — |
| Solana RPC: supply & inflation | 🟢 live | 7116 ms | 11 sec ago | — |
| Solana RPC: vote accounts | 🟢 live | 637 ms | 20 sec ago | — |
| Solana RPC: watched accounts | 🟢 live | 3101 ms | 8 sec ago | — |
| Solana Statuspage | 🟢 live | 4548 ms | 17 sec ago | — |

## 10. Methodology

**Collection.** Each source is fetched independently and wrapped so that a failure downgrades exactly one section rather than the run. Solana RPC calls fail over across public endpoints; every other source is a public HTTP API or RSS/Atom feed. No API key is used anywhere and the only dependency is the Python standard library.

**Anomaly detection.** Three detectors run on every report:

1. *Statistical* — modified z-score `modified z-score 0.6745*(x-median)/MAD over a rolling window` over the last 96 runs. Median and median absolute deviation are used instead of mean and standard deviation so that one earlier spike cannot mask the next one. |z| ≥ 3.5 raises a warning, |z| ≥ 5.0 is critical. Metrics are direction-aware: a rising Nakamoto coefficient never alerts. Detection stays quiet until 5 runs of history exist.
2. *Threshold rules* — fixed conditions that are bad regardless of history (unhealthy RPC, slot time above 600 ms, delinquent stake above 2%, failure rate above 65%, client monoculture above 85%, stablecoin depeg beyond 2%).
3. *Cross-source correlation* — signals that exist only because several sources are held together: TVL diverging from price, the fee-to-DEX-volume ratio shifting, throughput and failure rate rising together, stablecoin share of TVL rotating.

**Block sampling.** Median fees, failure rates and wallet counts are computed from raw blocks downloaded over RPC and parsed locally, so those figures do not depend on any aggregator. The active-wallet estimate uses Chapman's capture-recapture estimator over two disjoint halves of the sample; because heavy automated wallets appear in every block, that figure is an order-of-magnitude indication for the sampling window, not a daily user count.

**Limits.** Aggregated economic figures (TVL, DEX volume, fees, stablecoin float) carry their providers' methodologies and revisions. Point-in-time RPC readings reflect the endpoint that answered. X/Twitter sentiment is not collected.

---

Solana Pulse 1.0.0 · Python 3.12.3 · Python standard library only · MIT licence
