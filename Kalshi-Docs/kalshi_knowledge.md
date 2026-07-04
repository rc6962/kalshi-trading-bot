```markdown
# Kalshi Prediction Markets — Domain Knowledge
<!-- ai/kalshi_knowledge.md -->
<!-- Append-only. Do not delete or overwrite existing entries — add new
     sections or refine existing ones, preserving prior knowledge unless
     confirmed wrong or outdated. Tag new additions with session/date. -->

## Table of Contents
1. Overview
2. Product Definition & Contract Structure
3. Assets Covered
4. Contract Payoff Behavior
5. Listing, Timing & Calendar Mechanics
6. Settlement Mechanics (CF Benchmarks RTI) — ⚠️ Verify Per Asset/Frequency
7. **YES/NO Order Equivalence — Critical API Mechanic (CONFIRMED)**
8. Market Microstructure & Pricing
9. Regulatory Context & Positioning
10. Relationship to Perpetual Futures
11. Fee Structure — ⚠️ Unverified
12. Strategy Landscape (Community-Sourced, Not Official)
13. Implementation Considerations for AI/Algo Systems
14. Open Questions / Things to Verify Live

---

## 1. Overview

Kalshi's 15-minute crypto markets are ultra-short-term binary event
contracts that let traders bet on whether a cryptocurrency's price
will be up or down over a 15-minute window. They sit on top of
Kalshi's regulated event-contract exchange and are available across
multiple major crypto assets.

At a high level:
- Each contract asks a yes/no question like "Will BTC be above the
  target price in 15 minutes?"
- Traders buy Up (equivalent to "Yes") or Down ("No") contracts,
  priced between roughly 0.01 and 0.99, representing implied
  probabilities.
- At settlement, one side resolves near 0.99 and the other resolves
  at 0, with actual cash PnL determined by entry and exit prices plus
  fees.
- Settlement is mechanically tied to CF Benchmarks' Real-Time Index
  (RTI/BRTI) via a 60-second average — see Section 6 for important
  caveats about consistency across assets/frequencies.

This document is written for AI agents and developers (e.g., trading
bots) to reason precisely about how these markets work, how they are
listed and settled, and how to interact with them via Kalshi's API.

---

## 2. Product Definition & Contract Structure

### Core Contract Question
15-minute crypto markets are binary event contracts on short-horizon
price direction. Example questions:
- "Will Bitcoin be up or down in 15 minutes?"
- "BTC 15 min – Up or Down relative to a target price (e.g.,
  70,922.50) at the end of the 15-minute window?"

Key structural features:
- **Binary payoff** — one side (Up or Down) resolves in the money,
  the other out of the money.
- **Short horizon** — each contract covers a 15-minute interval, and
  a new instance starts immediately after settlement.
- **Target price** — for "Up or Down" markets, a target/strike level
  is displayed in the contract header.

---

## 3. Assets Covered

Kalshi currently lists 15-minute markets across seven major
cryptocurrencies — confirmed directly against Kalshi's live category
page and independently corroborated by third-party trading guides:

- Bitcoin (BTC)
- Ethereum (ETH)
- Solana (SOL)
- Ripple (XRP)
- Dogecoin (DOGE)
- Binance Coin (BNB)
- Hype (HYPE)

Each asset has its own "X 15 min – Up or Down" event market with the
same 15-minute resolution window.

---

## 4. Contract Payoff Behavior

For 15-minute crypto contracts — confirmed convention:
- Contracts are quoted between approximately 0.01 and 0.99.
- If the outcome you backed is correct, the contract resolves near
  0.99 (behaves like a $1 payout); PnL is
  `(settlement_price - entry_price) × contracts`.
- If wrong, the contract resolves at 0 (or very close); PnL is
  `- entry_price × contracts` (ignoring interim trades and fees).
- Common shorthand: these markets "pay 99¢ if you're right and 0¢ if
  you're wrong" — functionally a classic binary option with a $1
  nominal value minus fees.

---

## 5. Listing, Timing & Calendar Mechanics

### Market Listing on the Crypto Calendar
On the Crypto Events Calendar, 15-minute markets appear as recurring
events under each asset (e.g., "BTC Up or Down – 15 minutes," "ETH Up
or Down – 15 minutes," etc.). The calendar shows:
- Next expiry time (e.g., "Jun 27, 11:00PM ET").
- Countdown timer showing remaining time.
- Volume/market count — 15m entries often show $0 volume right after
  a new window opens.

### Session Roll and Continuous Trading
- Each 15-minute contract has a clearly labeled end time.
- Once the window ends and the contract settles, a new 15-minute
  contract is listed with an updated target price reflecting current
  conditions.
- This creates a continuous series of 15-minute markets — traders
  (and bots) must "roll" from one settling market to the next for
  continuous exposure.
- Ticker pattern is reportedly consistent (e.g., a `KXBTC15M-...`
  style identifier) — confirm exact current format live rather than
  hardcoding, since ticker conventions can change.

---

## 6. Settlement Mechanics — ⚠️ VERIFY PER ASSET/FREQUENCY

### CF Benchmarks and CFB Real-Time Indexes
- CF Benchmarks is a UK FCA-authorized digital asset index provider,
  established in 2016 from the Crypto Facilities Multilateral Trading
  Facility, that aggregates crypto prices from multiple major
  exchanges.
- CFB RTIs provide a per-second spot price for each crypto in USD.
- Kalshi's Help Center states: crypto market contracts are settled by
  averaging 60 seconds of CFB Real-Time Indexes, which report a price
  once per second.
- Confirmed directly on a live Kalshi BTC 15-min contract's own rules
  text: resolution is based on "the simple average of the sixty
  seconds of CF Benchmarks' BRTI" before the window's close, compared
  against the target/strike price.

### 60-Second Averaging Mechanism (generic model)
1. At contract end (e.g., T = 11:00:00 PM ET), identify the last
   minute before expiration (10:59:00–10:59:59).
2. For each second `s`, the relevant CFB RTI publishes a price
   `RTI_s`.
3. Compute the arithmetic mean: `RTI_avg = (1/60) × Σ RTI_s`.
4. Compare `RTI_avg` to the contract's target price (e.g., "Up"
   resolves if `RTI_avg >= target`).
5. The side consistent with the truth of the question wins.

This reduces single-exchange manipulation risk (price is averaged
across time and venues) and provides a defensible regulatory
benchmark.

### ⚠️ KNOWN SOURCE CONFLICT — verify before relying on this in code
- Kalshi's own live market rules text (primary source) states 15-min
  BTC contracts settle via the 60-second BRTI average described above.
- A third-party backtesting/analysis source claims the opposite for
  the same product family: that 15-min BTC markets ("the KXBTC15M
  family") settle using Kalshi's own captured reference prices
  recorded directly on the market record, with no external index
  lookup required.
- These two claims directly contradict each other. The official
  Kalshi contract text should be trusted over the third-party claim,
  but **always re-verify against the specific live market's own rules
  text before wiring this into execution/settlement logic** — do not
  assume uniformity.
- Additionally, a separate source claims Kalshi's **hourly** BTC
  markets use a different index (BRRNY) than the 15-minute markets use
  — meaning settlement methodology may NOT be uniform across
  frequencies. Do not assume 15-min mechanics automatically apply to
  hourly/daily BTC markets, or that BTC's mechanism is identical for
  ETH/SOL/XRP/DOGE/BNB/HYPE without checking each market's own rules
  text.

---

## 7. YES/NO Order Equivalence — Critical API Mechanic (CONFIRMED)

This is one of the most important structural facts to internalize
for anyone building order-placement or position-tracking logic
against Kalshi's API.

- Kalshi binary markets have two complementary sides, YES and NO,
  whose prices always sum to $1 (100¢). Because of this, a NO
  purchase is not a separate, independent position from a mechanical/
  API standpoint — it is treated as economically and mechanically
  equivalent to selling (shorting) YES, and vice versa.
- **CONFIRMED**: Over Kalshi's API, a "buy NO" order is actually
  placed/executed as a YES sell (short sell) under the hood. There is
  no independent "NO order" primitive at the execution level — NO-side
  intent is translated into a YES-sell mechanically. This is confirmed
  behavior, not a theoretical equivalence — treat it as ground truth
  when writing order-construction and reconciliation logic.
- Concretely: buying a NO contract at price `X` is the same economic
  position, AND the same underlying API-level action, as
  selling/shorting a YES contract at price `(1 - X)` (in cents: a NO
  bid at 93¢ is equivalent to a YES ask at 7¢, and a YES bid at 7¢ is
  equivalent to a NO ask at 93¢, for identical contract sizes).
- This is also why Kalshi's public orderbook endpoint only returns
  bids — never asks — for either side: there's no need for a separate
  "ask" array, because a bid on one side already encodes the implied
  ask on the other side via the `100 - price` relationship.
- **Practical implications for bots/agents:**
  - Any code path that constructs a "NO buy" order should be written
    with the understanding that it will resolve to a YES-sell action
    at the API/matching-engine level. Do not build separate, parallel
    order-construction logic for YES and NO as if they were
    independent order types — they are not.
  - Position tracking logic must treat a NO holding and a short YES
    holding as the SAME underlying exposure, not as two separate
    additive positions. A bot that sums "YES contracts held" +
    "NO contracts held" as independent quantities will misstate net
    exposure.
  - This matters directly for risk controls: a bot that buys YES on
    one leg and NO on the same market (thinking it's "hedging two
    different things") is actually just closing out or reducing its
    own YES position, not adding an independent hedge.
  - When reading fills/order history, expect to see NO-side intent
    represented as YES-sell actions in the underlying data. Reconcile
    accordingly — don't assume the API will hand back a literal
    "side: NO, action: buy" record without translation.
  - Always verify net exposure via `GET /portfolio/positions` (the
    authoritative source of truth for actual position state) rather
    than reconstructing it naively from raw order/fill history if
    there's any doubt about how a given order was recorded.

**Source note**: this NO-buy-as-YES-sell mechanic is confirmed. The
general bid-only-orderbook and price-complementarity mechanics were
independently corroborated from Kalshi's own API documentation and
quick-start guides. Endpoint-specific field naming (e.g., whether V2
order payloads expose a `side` field with literal `no` values that get
translated server-side, vs. requiring the caller to pre-translate to
YES-sell before submitting) should still be checked against the
current live API reference when writing new order-construction code,
since Kalshi has been actively migrating order endpoints (v1→v2,
fixed-point migration) — see `KALSHI_MASTER_INDEX.md` Section C3 and
Section G.

---

## 8. Market Microstructure & Pricing

- Contracts trade between approximately 0.01 and 0.99; a price of
  0.60 implies a 60% market-implied probability of the event.
- Traders can buy at one price and sell at another before expiry,
  realizing profit/loss based on price movement without holding to
  settlement.
- The UI displays implied probability for Up/Down plus potential
  dollar payout, simplifying decision-making for short-term trades.
- Orders are **limit orders only** — there is no native "market
  order" type; aggressive limit prices are used to approximate
  market-order behavior.

### Binary Options Analogy vs. Kalshi's Structure
- These markets are commonly compared to classic binary options: a
  simple yes/no on an underlying price condition within a fixed
  window, with payoffs near $1 or $0.
- Key differences from typical offshore binary options platforms:
  - **Regulatory status**: Kalshi is a CFTC-regulated Designated
    Contract Market (DCM); many binary options venues are unregulated.
  - **Reference rate quality**: CF Benchmarks RTI with 60-second
    averaging at expiry, vs. single-exchange last-trade prices common
    on many binary platforms.
  - **Contract framing**: these are "event contracts" on price
    direction, not options with strike/expiry/Greeks in the
    traditional derivatives sense.

---

## 9. Regulatory Context & Positioning

- Kalshi operates as a CFTC-regulated Designated Contract Market
  (DCM); this extends to its crypto event contracts, including 15-min
  products.
- Use of CF Benchmarks indices and transparent, published settlement
  rules is part of maintaining regulatory compliance and market
  integrity.
- Practical implications:
  - Available across all US states, subject to KYC/eligibility
    requirements, as a regulated platform.
  - Each contract has a formal rules page specifying the exact
    condition tested at expiry and how the benchmark price is
    computed — always check this per-market rather than assuming.
  - Tying settlement to an established index provider is intended to
    reduce ambiguity and the risk of ex-post rule reinterpretation.

---

## 10. Relationship to Perpetual Futures

- Kalshi's crypto category also includes **perpetual futures
  (perps)** — a separate product line: leveraged, continuous
  futures-like contracts with no expiration.
- 15-minute markets, by contrast, are discrete binary events with
  fixed 15-minute windows and 0/0.99-style payoffs.
- Design implication: perps suit long-running directional or hedging
  strategies; 15-min event contracts suit high-frequency views,
  short-term market-making, or intraday stat-arb.
- Note: perps use a fully separate REST/WebSocket/FIX API lane from
  event contracts — do not assume identical endpoints, fields, or
  margin mechanics between the two products (see
  `KALSHI_MASTER_INDEX.md` Section C8).

---

## 11. Fee Structure — ⚠️ UNVERIFIED (third-party source only)

- A third-party open-source Kalshi trading bot documents the
  following fee formula, **not yet confirmed against Kalshi's own
  official fee schedule**:
  - Taker: `ceil(0.07 × contracts × P × (1-P) × 100) / 100`
  - Maker: `ceil(0.0175 × contracts × P × (1-P) × 100) / 100`
  - (`P` = contract price as a probability, e.g., 0.60 for 60¢)
- **ACTION ITEM**: confirm this formula against Kalshi's official fee
  documentation before relying on it for PnL modeling or strategy
  backtesting — fee drag materially affects viability of
  high-frequency 15-min strategies, so getting this exactly right
  matters more than for lower-frequency trading.

---

## 12. Strategy Landscape (Community-Sourced, Not Official)

The following are informal strategy patterns observed in community
discussion and third-party commentary — **not official Kalshi
documentation** — included here for situational awareness, not as
recommendations:

- **Directional Trigger Bots**: systems that enter positions when
  contract prices cross thresholds (e.g., entering when a side is
  priced at 0.85, implying 85% market odds) to try to capture edge
  between 0.85 and 0.99.
- **"Bonding" Strategies**: approaches focused on selling near-0/1
  contracts (e.g., selling at 0.99 or buying at 0.01) to collect small
  edge repeatedly — akin to writing short-dated options; reportedly
  popular on 15m BTC markets but requires careful risk management
  given tail risk.
- **Cross-Venue Arbitrage**: bots trading pricing discrepancies
  between Kalshi's 15-min BTC/ETH/SOL markets and external venues
  (e.g., Polymarket), sometimes using external indicators to infer
  fair binary prices from spot/derivatives markets.

For an AI trading agent, relevant design points:
- Monitor orderbook skew and implied probabilities in real time.
- Model the distribution of short-horizon price changes in the
  underlying RTI/BRTI.
- Account for Kalshi's fee structure (see Section 11 caveats), rate
  limits, and API semantics when executing frequent orders.

---

## 13. Implementation Considerations for AI/Algo Systems

### Discovering and Tracking 15-Minute Markets
1. **Market discovery** — scan the crypto category or use the API to
   find markets with 15-minute cadence and tickers corresponding to
   BTC/ETH/SOL/XRP/DOGE/BNB/HYPE; maintain a mapping from instrument
   to its currently live 15-minute contract and upcoming ones.
2. **Rule ingestion** — for each contract, read its rules to
   determine exact target/strike price, direction definition (e.g.,
   `RTI_avg >= target` for Up), time zone, and precise expiration
   timestamp. Encode into a machine-readable representation for
   simulation/monitoring. Remember: verify settlement source per
   Section 6's caveats rather than assuming.
3. **Expiry alignment** — convert Kalshi's end time to UTC for
   consistent scheduling; stop entering new positions near expiry if
   your strategy requires it.

### Pricing and Risk Modeling
- Treat the settlement price as a 60-second average of a per-second
  RTI stream, not a single tick (pending Section 6 verification per
  market).
- Consider simulating 60-second paths of underlying spot prices to
  compute outcome probabilities vs. target, for edge detection against
  market-implied probability (`p_impl ≈ price`, ignoring fees).
- Key risk dynamics: high sensitivity to short volatility bursts near
  expiry (final 60 seconds dominate settlement); correlation with
  macro news/liquidations feeding into the underlying index; slippage
  and spread risk from rapid repricing near expiry.

### Execution and Lifecycle Management
- **Read side**: pull event/market metadata and orderbooks (public);
  subscribe to WebSocket channels for ticker/orderbook deltas instead
  of polling.
- **Write side**: place limit orders for Up/Down (YES/NO — remember
  Section 7's confirmed equivalence mechanic); amend/cancel as
  conditions change; close positions early by selling back contracts
  on the opposite side of the original trade.
- Handle Kalshi's token-based rate limits (separate read/write
  buckets — see `KALSHI_MASTER_INDEX.md` Section B10).
- Use client order IDs for idempotent ordering across reconnections.
- Track portfolio exposure **by asset and net direction** (not by
  raw YES-count + NO-count, per Section 7) to avoid over-leveraging a
  single short time window.

---

## 14. Open Questions / Things to Verify Live

- [ ] Exact settlement source per asset and per frequency (Section 6)
      — confirm BTC 15-min vs. hourly vs. ETH/SOL/etc. individually.
- [ ] Official fee schedule accuracy vs. the third-party formula in
      Section 11.
- [ ] Exact current ticker format pattern for rolling 15-min contracts.
- [x] ~~Whether V2 order endpoints expose NO orders directly or always
      normalize internally to YES bid/ask~~ — CONFIRMED: NO buys are
      placed as YES sells over the API (see Section 7).
- [ ] Whether the exact request payload requires the caller to
      pre-translate NO-side intent into YES-sell parameters, or whether
      the API accepts a literal `side: no` field and does the
      translation server-side — check current API reference for the
      exact request shape before writing new order-construction code.
- [ ] Cross-reference against `KALSHI_MASTER_INDEX.md` and
      `KALSHI_RFQ_REFERENCE.md` whenever API mechanics are touched, to
      avoid duplicating/contradicting those files.

---

## 15. API Rate Limiting — Token Bucket Mechanics (CONFIRMED)

**Source:** Kalshi official API documentation (https://docs.kalshi.com/getting_started/rate_limits)

Kalshi uses a **token-based rate limiting** system with separate Read and Write buckets.

### Token Budgets by Tier

| Tier | Read Budget (tokens/sec) | Write Budget (tokens/sec) |
|------|--------------------------|---------------------------|
| Basic | 200 | 100 |
| Advanced | 300 | 300 |
| Expert | 600 | 600 |
| Premier | 1,000 | 1,000 |
| Paragon | 2,000 | 2,000 |
| Prime | 4,000 | 4,000 |
| Prestige | 6,000 | 8,000 |

### Cost per Request

- **Order placement (Create Order):** 10 tokens (Write bucket)
- **Order cancellation:** 2 tokens (Write bucket)
- **GET requests (market data, positions, orders):** 10 tokens (Read bucket)
- **Batch endpoints:** Each item billed separately (25 orders = 250 tokens)

### Bucket Mechanics

- **Capacity:** 2 seconds of budget (Basic tier Write = 200 tokens max burst)
- **Refill rate:** Continuous at the per-second rate (Basic = 100 tokens/sec)
- **After 2 quiet seconds:** Bucket is full and ready for burst
- **429 response:** No `Retry-After` header — bucket keeps refilling continuously
- **Recommended:** Apply exponential backoff on 429 or timeout responses

### Token Exhaustion Behavior

When the Write bucket is empty:
- New order requests return `429 Too Many Requests` or timeout
- Bucket refills continuously at the per-second rate
- No penalty or cooldown beyond natural refill time
- **Critical:** Repeated rapid retries can exhaust bucket faster than it refills, causing cascading failures

### Design Implications for Trading Bots

Bots using Kalshi's order placement endpoints should implement:
1. **Bounded retries** — Max N attempts before giving up
2. **Exponential backoff** — Wait progressively longer between retries
3. **Cooldown periods** — Pause to allow token bucket to refill
4. **Request pacing** — Don't exceed sustainable rate (Basic tier: ~10 orders/sec)
5. **Idempotency** — Use `client_order_id` to prevent duplicate orders on retry

### Related Documentation
- Official Rate Limits: https://docs.kalshi.com/getting_started/rate_limits
- Full API Reference: `Kalshi-Docs/API/Newest Kalshi API Information.md` (Section 4)
- Order Placement: `Kalshi-Docs/API/Newest Kalshi API Information.md` (Section 9)

---
<!-- END OF FILE — append new dated entries below this line as new
     sessions learn more. Do not edit above without strong justification. -->
```
