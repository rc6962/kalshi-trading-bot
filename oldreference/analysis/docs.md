# Kalshi API — Verified Implementer Reference

> Consolidated from repo docs (`kalshi_knowledge.md`, `strategy-2026-06-27.md`,
> `KALSHI_15MIN_COMPLETE_RESEARCH_FINDINGS.md`, `kalshi_api_llm_overview.md`,
> `Newest Kalshi API Information.md`) plus live fetches from `docs.kalshi.com`
> on 2026-07-04: `llms.txt`, `order_direction.md`, `create-order-v2.md`.
>
> **Last verified:** 2026-07-04
>
> Where the repo's `strategy-2026-06-27.md` (older, V1 order shape) conflicts
> with the live Kalshi docs, the live docs win. Conflicts are called out inline
> with ⚠️ markers.

---

## 1. Environments & Base URLs

| Environment | REST | WebSocket |
|---|---|---|
| Production | `https://external-api.kalshi.com/trade-api/v2` | `wss://external-api-ws.kalshi.com/trade-api/ws/v2` |
| Demo | `https://external-api.demo.kalshi.co/trade-api/v2` | `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` |

- Also supported (prod): `api.elections.kalshi.com` (despite the subdomain, serves all markets, not just elections)
- Credentials are NOT shared between environments; demo keys reject on prod (and vice versa)
- AWS PrivateLink available for institutional isolation — contact `institutional@kalshi.com`
- Source: `kalshi_api_llm_overview.md` §api_environments (matches live docs)

---

## 2. Authentication (RSA-PSS)

**Required headers on every authenticated request:**

| Header | Value |
|---|---|
| `KALSHI-ACCESS-KEY` | Your API Key ID (UUID) |
| `KALSHI-ACCESS-TIMESTAMP` | Current time in **milliseconds** (string) |
| `KALSHI-ACCESS-SIGNATURE` | Base64-encoded RSA-PSS SHA256 signature |

**Signed message:** `timestamp + HTTP_METHOD + path_without_query`

Example: for `GET /trade-api/v2/portfolio/orders?limit=5`, sign
`{ts}GET/trade-api/v2/portfolio/orders` — strip the query string before signing.

**Key loading:**
```python
from cryptography.hazmat.primitives import serialization
serialization.load_pem_private_key(pem_bytes, password=None)
```

**Signing:**
```python
padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH),
hashes.SHA256()
```

Then `base64.b64encode(signature).decode()`.

Source: `kalshi_api_llm_overview.md` §api_keys (verified against live docs).

---

## 3. Rate Limits (Token Bucket)

Two independent buckets per environment:

| Bucket | Covers |
|---|---|
| **Read** | `GET` endpoints and anything not routed to Write |
| **Write** | Order placement, amends, cancels, order groups, RFQ quote flow, block trade proposal accepts |

Per-second refill rates by tier:

| Tier | Read | Write |
|---|---|---|
| Basic | 200 | 100 |
| Advanced | 300 | 300 |
| Expert | 600 | 600 |
| Premier | 1,000 | 1,000 |
| Paragon | 2,000 | 2,000 |
| Prime | 4,000 | 4,000 |
| Prestige | 6,000 | 8,000 |

- Default request cost: **10 tokens**
- Order create: 10 tokens (Write). Cancel: 2 tokens (Write).
- **Batch endpoints bill per-item** — 25 orders = 250 tokens, all must fit in the bucket at once or the whole batch is rejected.
- Capacity: up to **2 seconds of budget** for burst. After 2 quiet seconds, full burst available.
  - Exception: Basic-tier Write and Perps Read hold only 1 second of budget.
- `429` response body: `{"error": "too many requests"}` — **no `Retry-After` header**. Bucket keeps refilling; apply exponential backoff.
- Perps uses separate buckets; Perps calls do not draw down event-contract budgets.
- Determining tier at runtime: `GET /account/limits` (recommended instead of assuming Basic).

Source: `kalshi_api_llm_overview.md` §rate_limits; `kalshi_knowledge.md` §15.

---

## 4. Orderbook — Bid-Only, Complement Pricing

**Endpoint:** `GET /markets/{ticker}/orderbook` — **no auth required**

**Response shape:**
```json
{
  "orderbook_fp": {
    "yes_dollars": [["0.0100", "200.00"], ..., ["0.4200", "13.00"]],
    "no_dollars":  [["0.0100", "100.00"], ..., ["0.5600", "17.00"]]
  }
}
```

Each entry is `[price_dollars:str, count_fp:str]`.

⚠️ **CRITICAL PARSING RULE:** Arrays are sorted **ascending** by price. The
**last element** is the best bid, not index `[0]`:

```python
best_yes_bid = yes_dollars[-1][0]   # CORRECT
best_yes_bid = yes_dollars[0][0]    # WRONG — this is the lowest bid
best_yes_bid = max(row[0] for row in yes_dollars)  # works but inefficient
```

⚠️ The original implementation plan's `best_yes_bid = max(yes_dollars[0])` is
**wrong** — `yes_dollars[0]` is the first bid row, not all the prices.

**Complement pricing (binary market invariant):**

| Side | Best bid computation | Implied ask |
|---|---|---|
| YES | `yes_dollars[-1][0]` | `1.00 - no_dollars[-1][0]` |
| NO | `no_dollars[-1][0]` | `1.00 - yes_dollars[-1][0]` |

**Spread(YES) = `(1.00 - best_no_bid) - best_yes_bid`**

Source: `kalshi_api_llm_overview.md` §orderbook_responses (verified).

---

## 5. WebSocket Channels (Concrete Names)

| Channel | Visibility | Purpose |
|---|---|---|
| `fill` | private | User fill notifications — **this is what the plan calls "order channel"** |
| `orderbook_delta` | public | Incremental book updates |
| `orderbook_snapshot` | public | Full book snapshot (sent on first subscribe) |
| `market_positions` | private | Position updates |
| `market_lifecycle_v2` | public | Market state changes incl. **`settled` event** for PnL capture |
| `ticker` | public | Top-of-book market ticker updates |
| `trade` | public | Public trades (shows `taker_outcome_side` / `taker_book_side`) |
| `order_group_updates` | private | Order group lifecycle |
| `communications` | private | RFQ / quote flow |

**Subscribe command:**
```json
{
  "id": 1,
  "cmd": "subscribe",
  "params": {
    "channels": ["fill", "market_lifecycle_v2", "orderbook_delta"],
    "market_tickers": ["KXBTC15M-..."],
    "use_yes_price": true
  }
}
```

**`use_yes_price` flag (NEW, important):** Set to `true` in subscribe params to
get no-side `orderbook_delta` levels reported in **yes-leg pricing** so both
sides share the same price scale. Default `false` (legacy no-leg pricing flips
the price scale between yes/no sides). The default will flip to `true` in a
future release; integrations should opt in now.

**Auth:** same headers as REST, signed over `(timestamp + "GET" + "/trade-api/ws/v2")` during the WebSocket handshake.

**Keep-alive:** Python `websockets` handles ping/pong automatically. Kalshi sends Ping frames with body `heartbeat` (margin WS — check trade WS docs for any equivalent, but `websockets` lib handles it transparently either way).

Source: `order_direction.md`, `kalshi_api_llm_overview.md` §websocket.

---

## 6. Order Construction (V2 — CANONICAL, RESOLVES §5 CONTRADICTION)

⚠️ This section supersedes `strategy-2026-06-27.md` §2.1-2.2, which describes
the **legacy V1** order shape (`action`/`side:"yes"`). Those fields are
deprecated, removed no earlier than **2026-05-28**. New code MUST use V2.

**V2 endpoint:** `POST /portfolio/events/orders`

⚠️ NOT `/portfolio/orders` (legacy endpoint, deprecated 2026-05-06).

**V2 request fields (from live OpenAPI spec):**

| Field | Required | Type | Notes |
|---|---|---|---|
| `ticker` | ✅ | string | Market ticker |
| `side` | ✅ | enum `"bid"` \| `"ask"` | `bid` = buy YES, `ask` = sell YES (= long NO). NO separate `action`; NO `"yes"`/`"no"` values on V2. |
| `count` | ✅ | fixed-point string | e.g. `"10.00"` (2 decimals; min granularity 0.01 contracts) |
| `price` | ✅ | fixed-point dollar string | e.g. `"0.5600"` (up to 6 decimals; constrained by market tick size) |
| `time_in_force` | ✅ | enum | `fill_or_kill` \| `good_till_canceled` \| `immediate_or_cancel` |
| `self_trade_prevention_type` | ✅ | enum | `taker_at_cross` \| `maker` |
| `client_order_id` | recommended | string (UUID) | Dedup key — API rejects duplicates with `409` |
| `post_only` | optional | bool | Maker-only order |
| `reduce_only` | optional | bool | Caps place count by current position |
| `expiration_time` | optional | int64 Unix sec | For GTT (GTC + expiration_time) — do NOT set with IoC |
| `cancel_order_on_pause` | optional | bool | Auto-cancel if exchange pauses |
| `subaccount` | optional (default 0) | int | 0 = primary |
| `order_group_id` | optional | string | Order group linkage |
| `exchange_index` | optional (default 0) | int | Shard; `-1` = auto-route |

**V2 response:**
```json
{
  "order_id": "uuid",
  "client_order_id": "uuid",
  "fill_count": "0.00",
  "remaining_count": "10.00",
  "average_fill_price": "0.5600",  // only if fill_count > 0
  "average_fee_paid": "0.0098",    // only if fill_count > 0
  "ts_ms": 1715793600123
}
```

**Mapping NO intent to V2:**
- Want to be long NO? Submit `side: "ask"` with `price = (1.00 - desired_no_price)` as the yes-leg price.
- Example: NO buy at $0.30 ⇒ `{"side": "ask", "price": "0.70"}`.
- Kalshi matches it as a YES sell; mechanically equivalent to a NO buy at the complement price.

⚠️ **CONFLICT — needs live verification in Phase 0:** `strategy-2026-06-27.md`
§2.2 claims "GTC rejects `reduce_only=True`". The V2 schema shows `reduce_only`
as a free boolean with no documented constraint against GTC. Possibilities:
- The strategy doc was correct as of an earlier API version and V2 lifted the restriction
- The restriction still exists but isn't in the OpenAPI schema enum/dependency
- Phase 0 must place a 1¢ demo order with `reduce_only: true, time_in_force: "good_till_canceled"`
  and observe whether it returns `400` or is accepted.

Source: `create-order-v2.md` (live OpenAPI spec); repo `order_direction.md`.

---

## 7. Stop-Loss Mechanics (Decision Locked post-Review)

A stop-loss must reliably flatten a losing position **when triggered** — i.e.,
when the market is moving against us, exactly when fills are hardest.

**GTC maker stop is unsafe** because:
- A resting maker order at our stop price only fills if someone crosses it.
- In a fast adverse move, the book may gap past our stop price without
  printing at it, leaving the stop unfilled.
- Symptoms already live in this bot per `strategy-2026-06-27.md` §4.3:
  "12 canceled limit exit orders at 5-second intervals in the final 60 seconds."

**Required stop-loss shape:**
```
side          = opposite of entry
                 YES-long entry  → stop is ask  (sell YES to flatten)
                 NO-long entry   → stop is bid  (buy YES back to flatten)
time_in_force = immediate_or_cancel   // NOT GTC
reduce_only   = true                    // caps by current position
price         = aggressive limit beyond opposite best bid (see below)
```

**"Aggressive price" computation (marketable limit, simulates market order):**
- For a sell-YES stop: `price = best_yes_bid - buffer`  (e.g. buffer = $0.05)
- For a buy-YES stop: `price = best_yes_ask + buffer`  (e.g. buffer = $0.05)
- This crosses the spread, guaranteeing immediate fill (taker), at a small cost premium.

**Retry policy for IoC returning `fill_count = 0`** (per `strategy-2026-06-27.md`
§6.3, this is a known failure mode in the final 60 seconds of thin 15m books):
- Retry up to 3 times with progressively wider buffer (5¢ → 10¢ → 20¢).
- If still 0: log `stop_failed` event with reason and accept loss via settlement.
- Do NOT loop indefinitely — the 12-cancel-exit pattern in the live bot is the failure mode this prevents.

**Fees on stops:** Always taker (never maker), because aggressing the spread
guarantees taker status. See §8 for the fee formula.

---

## 8. Fees (Confirmed)

**Formula:**
```
fee_per_contract = round(multiplier × price × (1 − price) × contracts, 2)
```

- Crypto multiplier = **0.07** (7%) — highest among Kalshi categories
- Peak fee at `price = 0.50`: `$0.0175` per contract (1.75% of notional)
- At 30¢/70¢: `$0.0147` per contract
- At 10¢/90¢: `$0.0063` per contract
- **Maker fees ≈ $0.00** for retail contract sizes (cent rounding zeroes them)
- Settlement fees are built into the per-contract fee — no separate charge

**Asymmetry that matters for the bot:**
| Order side | Fee regime |
|---|---|
| Resting entry (GTC + post_only or non-crossing price) | Maker ≈ $0 |
| Stop-loss exit (IoC + aggressive price) | Taker formula above |
| Marketable entry (crossing spread) | Taker formula above |
| Take-profit limit (resting) | Maker ≈ $0 |

`reporting/metrics.compute_fees()` must distinguish `fill_side ∈ {maker, taker}`
per fill event. Trade log must record `fill_side` for accurate ex-post reporting.

**EV gate (for live entries):**
```
EV = p_win × (0.99 − entry_price) − (1 − p_win) × entry_price − fee_entry − fee_stop_expected
```
where `fee_stop_expected = stop_trigger_prob × taker_fee(stop_price)`.

Source: `KALSHI_15MIN_COMPLETE_RESEARCH_FINDINGS.md` §1.1; `kalshi_knowledge.md`
§11 (originally unverified, now confirmed via live `fee_rounding.md` reference
in `llms.txt`).

---

## 9. Market Lifecycle & Settlement Capture

**States:** `initialized → active → closed → determined → finalized`

**WS events on `market_lifecycle_v2` channel:**
`created`, `activated`, `deactivated`, `close_date_updated`, `determined`, `settled`

| Transition | Mechanism |
|---|---|
| `initialized → active` | Implicit (no WS event); when `open_time` passes |
| `active/inactive → closed` | Implicit (no WS event); when `close_time` passes |
| `closed → determined` | Explicit WS event `determined`; `result` set to `yes`/`no`/`scalar` |
| `determined → finalized` | Explicit WS event `settled`; positions paid out |

**Order operations after `close_time`:** rejected with `MARKET_INACTIVE`.

**Resting orders auto-cancel** shortly after close. Cancellation updates flow
on the usual user channels (`fill`? confirm — likely `order` updates on a
separate channel; verify in Phase 0).

**SETTLEMENT CAPTURE — closes the plan's open decision #3:**

Do NOT poll REST for settlement. Subscribe to `market_lifecycle_v2.settled`.

On `settled` event, capture at minimum:
- `ticker`
- `result` (yes/no/scalar)
- `settlement_price` (0 / 0.99 for crypto binary contracts)
- `settlement_ts`

**Realized PnL computation:**
- For each surviving position on that ticker, realized PnL per contract:
  `(settlement_price − entry_price) − fees_paid`
- YES-long that wins: `(0.99 − entry_price) − fees`
- NO-long (YES-short) that wins: `(entry_price − 0.01) − fees`  (sell at entry, settle at 1 minus; confirm sign convention with one closed market)
- Always reconcile with `GET /portfolio/settlements`.

For window-rollover trades where the bot has already placed the next window's
entries before previous settlement completes: do NOT reuse `entries` dict
keys across windows — namespace by `{window_id, ticker}` to avoid cross-window
stop/fill attribution errors.

Source: `kalshi_api_llm_overview.md` §market_lifecycle.

---

## 10. 15-Min Crypto Specifics

**Series tickers (all 7 confirmed live):**
```
KXBTC15M, KXETH15M, KXSOL15M, KXDOGE15M,
KXXRP15M, KXBNB15M, KXHYPE15M
```

**Cadence:** new window opens at every `:00 / :15 / :30 / :45` (UTC? — confirm
timezone via a live `GET /markets/{ticker}` `close_time` field; widely reported
as ET but `close_time` is a Unix timestamp so zone doesn't matter for compute).

**Listing flow:** as the previous window settles, the next window's market
transitions to `active` (no explicit WS event for this — implicit at
`open_time`). Discovery query should sort on `close_time` and pick the
soonest future close.

⚠️ The original plan said "Filter markets whose `close_time` is the next
15-minute boundary" — this is fragile (e.g., DST, late-listed markets,
cooldown after settlement). Instead: query `series_ticker=KX{ASSET}15M&status=open`,
sort by ascending `close_time`, take the first one with `close_time > now + 30s`
(30s buffer for the just-settled market).

**Settlement:** 60-second average of CF Benchmarks RTI in the final minute
(confirmed for BTC 15m in market rules text). Source: `kalshi_knowledge.md` §6.

⚠️ Per `kalshi_knowledge.md` §6, settlement source may differ for ETH/SOL/
DOGE/XRP/BNB/HYPE — verify by reading each market's own rules text via
`GET /markets/{ticker}` before relying on uniform behavior.

**Inter-Window Momentum Carry (IWMC):** the settlement price of window N
becomes the effective opening reference for window N+1. This is a structural
edge that **no existing public strategy exploits** (per `kalshi-15m-strategies.md`
§5.4 and `strategy-2026-06-27.md` §8). Out of scope for v1 but the bot's data
model should not preclude adding this later — record settlement prices for
every window even if not used.

---

## 11. YES/NO Position Equivalence (Critical for Risk Code)

**Mechanic is CONFIRMED:** Long NO == Short YES — not just economically but
mechanically at the matching engine. There is no independent "NO order"
primitive at execution. A NO bid is encoded as a YES ask at the complement
price.

**Implications:**

1. **Orderbook only has bids** for both yes_dollars and no_dollars — there are
   no ask arrays. Asks are implied by the complement: `yes_ask = 1.00 - best_no_bid`.

2. **Position tracking must be NET per ticker.** A bot that buys YES at 0.40
   and "buys NO at 0.30" on the same ticker has NOT added two hedges — it has
   flattened (YES-long 1 contract + NO-long 1 contract = net 0 contracts).

3. **Authoritative position truth:** `GET /portfolio/positions` returns net
   per ticker. Use this for risk, NOT a sum of fills. Reconcile on every
   loop iteration (cheap; 1 Read-bucket token).

4. **RiskGuard.check_balance must compute `estimated_max_loss` correctly per side:**
   - Long YES at price `p` (bid entry): max_loss = `p × contracts` (settles 0)
   - Long NO (= short YES) at entry `p` (ask entry): max_loss = `(1.00 − p) × contracts` (settles 1, you bought at p, owe $1)
   
   ⚠️ The original plan's "estimated_max_loss = entry_price × contracts for each
   entry" is **WRONG for NO entries**. This will under-reserve for NO trades
   and allow over-leveraging.

5. **Fills reported on the WebSocket `fill` channel include `outcome_side`
   (yes|no) and `book_side` (bid|ask)** — these are canonical. The legacy
   `action`/`side`/`is_yes`/`purchased_side` fields are deprecated (removed
   2026-05-28 but still present today for backward compatibility).

Source: `kalshi_knowledge.md` §7 (CONFIRMED); `order_direction.md` (canonical).

---

## 12. Open Items — Verify in Phase 0 Before Coding Phase 3+

These items need live verification before order-management code is finalized:

### 12.1 GTC + reduce_only compatibility
- Place a 1¢ demo order with `reduce_only: true`, `time_in_force: "good_till_cancelled"`.
- If accepted → GTC + reduce_only is viable; stops could optionally use GTC instead of IoC (still not recommended; IoC better for stops).
- If rejected with 400 → stops must use IoC + reduce_only (already the recommended pattern in §7).

### 12.2 Account rate-limit tier
- `GET /account/limits` — determine actual tier.
- This drives burst capacity for multi-asset entry batches. 7 assets × N contracts
  per side × 2 sides = up to 14 entry orders per window; if account is Basic tier
  with 100 tokens/sec Write, firing 14 orders in one batch (140 tokens) is fine but
  tight if other writes are in flight. Pre-flight bucket check or pre-compute
  expected wait time.

### 12.3 Settlement source uniformity per asset
- Pull one closed ETH/SOL/DOGE/XRP/BNB/HYPE 15m market — confirm `result` and
  `settlement_price` arrive as expected on `market_lifecycle_v2.settled`.
- If ETH uses a different index methodology than BTC, log per-asset settlement
  source in a config table — do not hardcode BTC's RTI behavior to all assets.

### 12.4 WebSocket reconnect replay semantics
- On WS reconnect, does Kalshi replay recent fill events?
- If yes → dedup via `order_id + fill_count` sequence — never assume each fill
  message is novel just because it arrives.
- If no → safe to handle fills as one-shot; still reconcile against
  `GET /portfolio/fills` on every reconnect.
- Until verified: treat every WS fill as authoritative only if its `order_id`
  is currently in `OrderManager.entries` or `OrderManager.stops`; ignore
  unknown `order_id` fills and trigger a `GET /portfolio/fills` reconciliation.

### 12.5 Partial fill semantics on V2
- V2 schema's response includes `fill_count`/`remaining_count`/`average_fill_price`.
- Read `GET /portfolio/fills` response shape and assume WS fill messages may
  carry partial counts.
- Test with a multi-contract demo order at a mid-spread price to observe
  partial-vs-full fill reporting shape.
- `OrderManager.on_fill(order_id, fill_price)` in the plan **assumes full fill
  — this is wrong**. On partial fill: place proportional stop on filled count
  only; keep remaining count of entry order live until next fill event.

### 12.6 1-penny-inside crossing-spread behavior
- Live-inspect BTC, ETH 15m books for spread distribution.
- If spreads are often 1¢ wide, "improve by 1¢" crosses to taker side.
- Default logic: **improve by 1¢ only if spread ≥ 2¢; otherwise join the best
  bid/ask** (rest at existing touch, guaranteeing maker).
- Add CLI flag: `--maker-strategy {improve|join}` (default `improve`).
- Add `post_only: true` to entries to programmatically enforce maker status —
  Kalshi rejects post_only orders that would cross, surfacing the problem
  before it costs taker fees.

---

## 13. Locked Decisions (from plan review on 2026-07-04)

These supersede the original implementation plan where they conflict:

| # | Original plan | Locked decision |
|---|---|---|
| 1 | Stop-loss is GTC limit, placed on fill | **Stop = IoC + `reduce_only: true` + aggressive price**. Not GTC maker. Stops are always taker. |
| 2 | Settlement via REST polling (open decision) | **Settlement via WS `market_lifecycle_v2.settled` event.** No REST polling. Reconcile with `GET /portfolio/settlements` once per window. |
| 3 | Tracks positions from fill history | **Position truth = `GET /portfolio/positions`.** Track NET direction per ticker; do not sum yes + no counts as independent exposures. |
| 4 | `best_yes_bid = max(yes_dollars[0])` | **`best_yes_bid = yes_dollars[-1][0]`** — last element of ascending-sorted array. |
| 5 | Order endpoint `/portfolio/orders` | **`POST /portfolio/events/orders` (V2).** `side ∈ {bid, ask}`. No `yes`/`no` values; no `action` field. |
| 6 | Fees flat estimate | **Maker ≈ $0 on resting entries; taker formula on stops & marketable entries.** `compute_fees()` records `fill_side` per event. |
| 7 | `estimated_max_loss = entry_price × contracts` per entry | **Per-side:** YES-long loss = `entry_price × contracts`; NO-long loss = `(1 − entry_price) × contracts`. |
| 8 | Maker via "1 penny inside" always | **Improve by 1¢ only if spread ≥ 2¢; else join touch.** Use `post_only: true` to enforce maker status programmatically. |
| 9 | `on_fill(order_id, fill_price)` assumes full fill | **Handle partial fills proportionally** — place stop on filled count only. |

---

## 14. Code Skeleton Pointers (for Phase 1 implementer)

**`kalshi/auth.py`** — wraps sign function from §2.
- `load_private_key(path: str) -> RSAPrivateKey`
- `sign_request(private_key, timestamp: str, method: str, path: str) -> str`
- Strip query string before signing: `path_without_query = path.split('?')[0]`
- ~30 lines

**`kalshi/rest_client.py`**
- `KalshiRestClient.get(path, params=None)`, `.post(path, json=None)`, `.delete(path)`
- Sign path INCLUDING the `/trade-api/v2` prefix (full URL path from root)
- Retry policy: exponential backoff on 429/5xx; max 3 attempts; respect per-tier budgets.
- Typed exceptions: `KalshiAuthError`, `KalshiRateLimitError`, `KalshiOrderError`.

**`kalshi/ws_client.py`**
- Handshake: `additional_headers` in `websockets.connect(url, additional_headers=headers)`
- Sign `"/trade-api/ws/v2"` (method = `"GET"`)
- Subscribe: `fill`, `market_lifecycle_v2`, `orderbook_delta` (with `use_yes_price: true`)
- Dispatch by message `type` to `OrderManager` callbacks
- Reconnect: watchdog timer (30s no-msg → reconnect); exponential backoff; resubscribe on reconnect.

**`kalshi/orderbook.py`**
- Parse `orderbook_fp.yes_dollars[-1][0]` and `no_dollars[-1][0]`
- Convert Decimal for math; preserve string for order placement
- Return `{yes_bid, yes_ask, no_bid, no_ask, yes_spread, no_spread}`

**`kalshi/order_manager.py`**
- `place_entry_orders`: builds bid/ask side per asset intent; uses `post_only: true`
- `place_stop_loss`: builds IoC + reduce_only + aggressive price (not GTC)
- `on_fill`: handle partial fills proportionally
- `on_stop_fill`: log realized loss, update daily PnL
- `cancel_all`: cancel previous window's entries (stops should already be IoC-cleared)

**`kalshi/risk_guard.py`**
- `check_kill_switch()` — file existence
- `check_daily_loss(current_pnl, cap)` — halt if exceeded
- `check_balance(estimated_max_loss)` — per-side formula per §13.7
- Call `GET /portfolio/balance` (returns cents — convert)

**`storage/trade_log.py`**
- Append-only JSONL
- Events: `entry_placed`, `fill`, `stop_placed`, `stop_fill`, `settlement`, `error`, `startup`
- Each event: `{ts, type, ticker, window_id, order_id?, fill_count?, fill_price?, fill_side?}`
- `fill_side ∈ {maker, taker}` required for accurate fee reporting

**`reporting/metrics.py`**
- `compute_fees(trades)` must apply taker formula to events with `fill_side="taker"`
  and ~$0 to `fill_side="maker"`
- `compute_max_drawdown(daily_pnl)` — peak-to-trough on cumulative PnL series

---

## 15. Source Documents

### Repo (`Kalshi-Docs/`)
- `kalshi_knowledge.md` — domain knowledge, §7 YES/NO equivalence CONFIRMED, §15 rate limits
- `KALSHI_15MIN_COMPLETE_RESEARCH_FINDINGS.md` — backtest results + fee formula
- `KALSHI_15MIN_RESEARCH_SUMMARY_NEWEST.md` — condensed findings
- `KALSHI_15MIN_RESEARCH_REPORT.md` — full research report
- `kalshi-15m-strategies.md` — strategy archetypes + IWMC (§5.4)
- `strategy-2026-06-27.md` — live config + V1 order shape
  ⚠️ §2.1-2.2 order construction is legacy V1; superseded by V2 OpenAPI spec
- `GITHUB_KALSHI_BOT_LANDSCAPE.md` — 3,200+ repo analysis
- `NEW_STRATEGIES_2026-06-29.md`, `Strategies.md` — strategy notes
- `API/kalshi_api_llm_overview.md` — REST/WS overview + auth examples
- `API/Newest Kalshi API Information.md` — comprehensive REST/WS reference
- `API/kalshi_openapi.yaml`, `API/kalshi_asyncapi.yaml` — machine-readable specs
- `API/KalshiAPIUpdates.md`, `API/KALSHIMASTERAPIINDEX.md`, `API/Kalshi-7-1-26.md`
- `API/script.py` — sample client script

### Live fetched on 2026-07-04
- `https://docs.kalshi.com/llms.txt` — documentation index (resolved endpoint name conflict)
- `https://docs.kalshi.com/getting_started/order_direction.md` — confirmed `outcome_side`/`book_side` canonical, legacy `action`/`side:"yes"` deprecated, removed no earlier than 2026-05-28
- `https://docs.kalshi.com/api-reference/orders/create-order-v2.md` — V2 OpenAPI: `side ∈ {bid, ask}`; `reduce_only` is free bool; V2 path `/portfolio/events/orders` confirmed

### Open Phase 0 verification fetches (when ready to implement)
- `https://docs.kalshi.com/api-reference/portfolio/get-positions.md` — confirm position response shape
- `https://docs.kalshi.com/api-reference/portfolio/get-fills.md` — confirm fill response shape & partial fill fields
- `https://docs.kalshi.com/api-reference/portfolio/get-settlements.md` — confirm settlement response shape
- `https://docs.kalshi.com/websockets/user-fills.md` — confirm WS fill message shape
- `https://docs.kalshi.com/websockets/market-and-event-lifecycle.md` — confirm settled event shape
- `https://docs.kalshi.com/getting_started/fee_rounding.md` — confirm fee rounding mechanics
