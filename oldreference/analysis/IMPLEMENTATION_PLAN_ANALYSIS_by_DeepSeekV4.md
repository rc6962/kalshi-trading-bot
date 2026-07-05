# Kalshi 15-Min Crypto Window Bot — Implementation Plan Analysis
**Reviewer:** DeepSeek V4 (DeepSeek-AI)  
**Date:** 2026-07-04  
**Scope:** Full review of the proposed implementation plan against Kalshi's documented API (docs.kalshi.com, local API specs, kalshi_knowledge.md) and domain research (TurbineFi backtests, GitHub landscape, prior bot learnings).

---

## 1. Executive Summary

The plan is **well-structured and implementable** from an API/architecture standpoint, but contains **strategy-level flaws** that, if unaddressed, will make the bot lose money consistently. The "passive maker + stop-loss + hold-to-expiry" concept is a **demonstrably negative-EV strategy archetype** per published backtests. Below I break down each concern with evidence from the research docs.

---

## 2. Strategy Concerns — The Core Problem

### 2.1 This Is a Mean-Reversion Fade Dressed as "Market Making"

The plan describes: place maker-limit orders 1 penny inside the book, wait for fill, place stop-loss, hold survivors to expiry. In effect, this is betting that price will revert — you're buying when someone crosses the spread to hit your resting order, hoping the price moves back toward your side.

**This fails categorically on 15-minute markets.** Per TurbineFi's 5,000-strategy backtest (Apr 29, 2026), published in `KALSHI_15MIN_COMPLETE_RESEARCH_FINDINGS.md`:

| Archetype | Variants | Profitable | Mean ROI |
|-----------|----------|------------|----------|
| Mean-reversion | 432 | **0** | -8.12% |
| Time-decay pivot | 80 | **0** | -$2,258 avg |
| Price-threshold | 4,290 | 7 (0.16%) | -19.95% |
| **Panic fade** | **96** | **93 (96.9%)** | **+4.90%** |

Beating the spread to be "penny-inside" means: your order may cross the spread and execute as taker (higher fees), or it sits at the existing best bid/ask and earns maker fees — both will be filled by traders who are directionally correct, and your hold-to-expiry assumption expects reversion that **does not happen** in the 15-minute window.

From `kalshi-15m-strategies.md` (Section 2.3):
> "All 'best' variants by net P&L were still unprofitable... Win rates hovered just above 50% (≈0.5038). Trade counts were extremely high (≈14,000+ trades), implying heavy fee and slippage drag."

From `strategy-2026-06-27.md` (Section 1.2):
> "Critical finding: On 15-minute Kalshi crypto, the contract price once above 0.60 does NOT revert. Post-move drift is real and directional. Do not fade it."

### 2.2 The "Penny Inside" Logic Has a Hidden Taker-Fee Trap

The plan says: "Place entry orders 1 penny inside the orderbook to ensure maker status." But the Kalshi orderbook is bid-only (NO ask = $1 - best YES bid). If you improve the quote by $0.01, your order may **cross the spread entirely** and execute as taker — incurring 7% (0.07 multiplier) fees instead of near-zero maker fees.

From `KALSHI_15MIN_COMPLETE_RESEARCH_FINDINGS.md` (Section 1.1 Fee Formula):
```
fee_per_contract = round(multiplier × price × (1 − price), 2)
Crypto multiplier: 7% (0.07)
Taker at 50¢: ~$0.0175/contract
Maker: ~$0.00 (rounding to nearest cent)
```

The plan itself notes this risk in Section 7, but the default behavior ("1 penny inside") makes it the rule, not the exception. The fix should be: **always join the existing best bid/ask** (never improve) unless the spread is >$0.02 wide.

### 2.3 Positive BTC/ETH Correlation — The Portfolio Blow-Up Risk

The plan acknowledges this in Section 7 but offers no mitigation. Research confirms:

From `kalshi_knowledge.md` (Section 13): "Key risk dynamics: high sensitivity to short volatility bursts near expiry; correlation with macro news/liquidations."

From `GITHUB_KALSHI_BOT_LANDSCAPE.md`: "No multi-asset correlation handling — BTC/ETH/SOL/DOGE/XRP/BNB/HYPE all trade simultaneously — no repo manages portfolio correlation."

**If BTC spikes in the final minute, every YES stop-loss on altcoins trips simultaneously.** The daily loss cap helps, but a single correlated event can wipe multiple positions in one window. Suggested fix: **cap concurrent correlated pairs (BTC+ETH count as 1 slot toward global limit)**.

### 2.4 Stop-Loss Width of $0.15 Is Too Tight for Altcoins

$0.15 on a $0.40 entry is a -37.5% move. On altcoins (DOGE, XRP) with thin books, normal noise will trigger stops before the trend resolves. From `strategy-2026-06-27.md` (Section 3.3):

> "Current: -25%. May need to go tighter to -20% on altcoins (DOGE, XRP) with thin books."

`KALSHI_15MIN_COMPLETE_RESEARCH_FINDINGS.md` recommends -20% stops for SOL/DOGE/XRP. The plan's default $0.15 width is asset-agnostic — it should vary per asset tier.

---

## 3. API/Technical Corrections

### 3.1 WebSocket Auth — Plan Says "access_token or signed message"

From the plan's Section 6, Step 4.1: "Handshake auth with access_token or signed message."

This is **incorrect per current Kalshi docs**. The production WebSocket (`wss://external-api-ws.kalshi.com/trade-api/ws/v2`) uses the **same RSA-PSS signed headers as REST**. Per `Newest Kalshi API Information.md` (Section 6):

> "WebSocket connections require authentication during the connection handshake. Required Headers: KALSHI-ACCESS-KEY, KALSHI-ACCESS-SIGNATURE, KALSHI-ACCESS-TIMESTAMP. Signing for WebSocket: message = timestamp + 'GET' + '/trade-api/ws/v2'"

There is no OAuth/token-based alternative. The `ws_client.py` must generate RSA-PSS headers identical to the REST client.

### 3.2 WS URL Mismatch

The plan uses: `wss://external-api-ws.kalshi.com/trade-api/ws/v2` — this is correct per current docs. Good.

### 3.3 Fill Detection Channel — Plan Uses "order channel"

The plan's Step 4.1 says: "Subscribe to: order channel (fills, order updates)"

Per the `llms.txt` index and official docs, fills come on the **`fill` channel** (private/authenticated), and order updates come on **`orderbook_delta`** (private). The `ticker` channel is the public price/volume channel. There's also `user_orders` for order created/updated notifications.

Subscribe to:
- `orderbook_delta` — real-time orderbook with `client_order_id` for your orders
- `fill` — your fill notifications (the critical one for stop-loss placement)
- `market_lifecycle_v2` — market state changes (settled/determined)

### 3.4 V2 API Order Fields — side vs action

The plan uses "side=bid" for YES and "side=ask" for NO. But per the V2 API docs (`Newest Kalshi API Information.md`, Section 9), and confirmed in `kalshi_knowledge.md` (Section 7), the V2 order endpoint uses:

```
side: "bid" or "ask" (not "yes"/"no")
```

For a "buy YES" entry: `side: "bid"`, `action: "buy"`  
For a "buy NO" entry (short YES): `side: "bid"`, `action: "sell"` — **NOT "side: ask"** for NO.

In V2, "buy NO" is mechanically a YES sell (short YES). Per `kalshi_knowledge.md` Section 7:
> "Over Kalshi's API, a 'buy NO' order is actually placed/executed as a YES sell (short sell) under the hood."

**Critical fix for order_manager.py**: When placing a NO entry, the API call must be `side="bid"` with `action="sell"` — placing `side="ask"` for NO is incorrect in V2.

### 3.5 Market Discovery — Query Pattern Can Miss Markets

Step 2.1 uses: `GET /markets?series_ticker=KX{ASSET}15M&status=open&limit=20`

Per `kalshi_knowledge.md` (Section 5): the ticker pattern `KXBTC15M-...` is reported but "confirm exact current format live rather than hardcoding." Series tickers vs. market tickers are different things — the series ticker for BTC 15-min might be `KXBTC15M` but markets under it have date-specific suffixes like `KXBTC15M-26JUL04T1200`.

Also, `status=open` only returns `active` markets. If a market just closed (past `close_time`), it won't appear. The bot needs to handle the case where no open market exists (short window between settlement and new listing). Per `kalshi_knowledge.md` (Section 5):

> "Once the window ends and the contract settles, a new 15-minute contract is listed with an updated target price."

There may be a 0-60 second gap between settlement and new listing. The bot should retry market discovery up to 2-3 times with exponential backoff before skipping a window.

### 3.6 Orderbook Price Grid Validation

Step 2.2 says: "Validate prices are within 0.01–0.99 and on the market's price grid."

The price grid is available via `GET /markets/{ticker}` → `price_ranges` field. Per `KalshiAPIUpdates.md` (Section 4):

> "Prices must land on the market's price grid. Check price_ranges on GET /markets/{ticker} for the valid step size."

The plan's orderbook.py should fetch market metadata to get the price grid before computing maker prices.

### 3.7 Get Balance Endpoint

Step 5.1 says: "Call GET /portfolio/balance." Correct. Balance is returned in cents per docs:
```json
{"balance": 25000}  // $250.00 in cents
```

### 3.8 Rate Limits — Plan Underestimates Token Costs

The plan uses `requests` for polling and assumes 3 retries with 1s/2s/4s backoff. Per the rate limit docs:

- Basic tier: Write bucket = 100 tokens/sec, order placement = 10 tokens
- With 7 assets × 2 sides = 14 orders per window (entry orders) + up to 14 stop-loss orders = potentially 28 orders in quick succession
- 28 × 10 = 280 tokens needed. Basic tier takes 2.8 seconds to refill that.
- Batch cancel for previous window adds more write load.

**Recommendation**: Use batch order placement (`POST /portfolio/orders/batch`) for entry orders and batch cancel (`DELETE /portfolio/orders/batch`) for previous window cleanup. Cut token consumption ~2-3x.

---

## 4. Architecture Review by Component

### 4.1 config/settings.py — OK
- Loads correct env vars. Missing: `WS_URL` (separate from REST base URL), and `RATE_LIMIT_TIER` for token budget awareness.
- Should validate the PEM key is RSA (not EC or other).

### 4.2 kalshi/auth.py — OK
- RSA-PSS SHA256 with salt_length=DIGEST_LENGTH is correct per docs.
- Signing message = timestamp + method + path (without query params) matches docs.
- Path must include `/trade-api/v2` prefix.

### 4.3 kalshi/rest_client.py — Minor Issues
- 429 backoff is correct, but plan says "On 5xx, retry once." 503 (maintenance) may require longer backoff. Check `GET /exchange/status` before retrying.
- No mention of `client_order_id` for idempotency. **Must add**: every order should carry a UUID4 `client_order_id` to prevent duplicates on retry.
- Missing: `Content-Type: application/json` header on POST.

### 4.4 storage/trade_log.py — OK
- JSONL append-only is good for durability. Consider adding a periodic integrity check (valid JSON per line, timestamps monotonic).

### 4.5 kalshi/market_discovery.py — Issues Noted Above
- See Section 3.5 of this analysis.
- Should also handle the case where a market exists but has `status=inactive` (exchange paused it). Log and skip.

### 4.6 kalshi/orderbook.py — Critical Fix Needed
- The plan's formula for `best_yes_ask = 1.00 - max(no_dollars[0])` is correct (bids are sorted ascending, last is best). Good.
- But `yes_bid_maker = best_yes_bid + 0.01` is dangerous per Section 2.2 of this analysis. Should be: `yes_bid_maker = best_yes_bid` (join the book) unless spread > $0.02.
- The `yes_ask_maker = best_yes_ask - 0.01` for NO entry placement: this is a `sell` on the bid side at a price that's the implied ask minus $0.01. For "buy NO" you'll want to `sell` at the best existing NO bid (which equals $1 - your ask price). This needs to be translated to `side="bid"`, `action="sell"` at price = `1 - (best_yes_ask - 0.01)`.

### 4.7 kalshi/order_manager.py — Multiple Critical Fixes
- NO entry via `side="ask"` is wrong (Section 3.4 above). Must use `side="bid"`, `action="sell"`.
- Stop-loss direction logic:
  - Plan: "YES entry → stop side=ask, price = entry_price - width" — correct conceptually but in V2 this is `side="bid", action="sell"` at `price = entry_price - width`.
  - Plan: "NO entry → stop side=bid, price = entry_price + width" — for a NO position (equivalent to short YES), a stop-loss means buying back YES. In V2: `side="bid", action="buy"` at `price = entry_price + width`.
- `cancel_all()`: should batch cancel instead of sequential DELETE per order. Use `DELETE /portfolio/orders/batch`.

### 4.8 kalshi/ws_client.py — Corrections Needed
- Auth: RSA-PSS signed headers, not access_token (Section 3.1).
- Subscribe to: `fill` (not "order_channel"), `orderbook_delta`, `market_lifecycle_v2`.
- Watchdog timer at 30s: official keep-alive sends Ping frames every 10s with body `heartbeat`. The `websockets` library handles pong automatically. 30s watchdog is safe.
- Order fill detection on `fill` channel: each fill includes `order_id`, `ticker`, `side`, `price_dollars`, `count_fp`. This is the trigger for stop-loss placement.
- Stop fills: plan says "On order_status_update with remaining_count=0." The official method is listening to `user_orders` channel or polling the order's `remaining_count` — the `fill` channel will also notify when a fill completes, matching on `order_id`.
- Market lifecycle for settlement: `market_lifecycle_v2` emits `determined` then `settled` events.

### 4.9 kalshi/risk_guard.py — OK
- check_kill_switch polling STOP_BOT file is simple and robust.
- Balance check via GET /portfolio/balance is correct.
- Consider adding a `GET /exchange/status` check — if exchange is in maintenance, halt.

### 4.10 main.py — Timing Issues
- "Sleep until 2 seconds after window open" — should be randomized (1-3s) to avoid thundering herd. Also: the market might not be queryable immediately after creation (per `market_lifecycle.md`: "The market may not be queryable immediately after a `created` event. Retry with backoff.")
- The loop should verify market existence with retries before proceeding.
- Ctrl+C handling: should cancel all open orders on shutdown, not just exit.

### 4.11 reporting/metrics.py and pdf_report.py — OK
- Standalone report generation is well-scoped.
- Fee calculation should use the confirmed formula from `KALSHI_15MIN_COMPLETE_RESEARCH_FINDINGS.md` Section 1.1: `fee = round(0.07 × price × (1-price), 2)`.

---

## 5. Open Decisions — My Answers (Updated)

### 5.1 Should the 1-penny-inside logic fall back to joining the best bid/ask if spread ≤ $0.01?
**Yes, and make it the default.** If spread ≥ $0.03, improving by $0.01 is safe. If spread ≤ $0.02, join the book. This should be a rule, not a fallback.

### 5.2 Should the bot auto-cancel unfilled entry orders at T-30s?
**Yes.** GTC orders left in the final 30s will be auto-cancelled by Kalshi at close anyway (`market_lifecycle.md`: "Once close_time passes, all order operations, including cancellations, are rejected with MARKET_INACTIVE"). Cancel proactively at T-30s to avoid stale state.

### 5.3 Should settlement results be fetched via REST?
**Both.** Subscribe to `market_lifecycle_v2` WS channel for real-time settlement detection. Use `GET /portfolio/settlements` (new endpoint per llms.txt index) REST endpoint for reconciliation. Cross-check.

### 5.4 WS disconnect mid-window?
**Skip the window.** Do not queue stale fills — it's error-prone. Log skip, alarm loudly. On reconnect, immediately query `GET /portfolio/orders` to discover any live orders the server still holds, reconcile state, and resume next window.

---

## 6. Missing Components

### 6.1 State Persistence Across Restarts
If the bot crashes mid-window (24/7 ops, it will), on restart it must:
1. Query `GET /portfolio/orders?status=resting` to discover existing GTC orders
2. Query `GET /portfolio/positions` to discover open positions
3. Reconcile against trade log to determine which window we're in
4. Decide: cancel stale orders? Resume? Skip window?

The trade log alone doesn't capture which orders are still live. Add a `state.json` file (or SQLite) that tracks `{window_id: {order_ids, position_status}}`.

### 6.2 Health/Uptime Logging
24/7 ops need uptime proof. Add a `health.log` (or JSONL heartbeat events every 60s) with timestamp + status fields.

### 6.3 Startup Stale-Order Check
Before placing any new orders, query `GET /portfolio/orders?status=resting` and cancel any GTCs from prior sessions. A crashed-and-restarted bot shouldn't have zombie orders.

### 6.4 Exchange Status Check
Before each window, query `GET /exchange/status`. If exchange is paused (maintenance), log and skip window.

### 6.5 Settlement Confirmation
After each window, `GET /portfolio/settlements` to confirm the outcome and log it. Survivors that settled at $0.99/$0.00 need to be logged as `settlement` events with PnL.

---

## 7. Strategy Recommendation — Pivot or Add?

The "passive maker + stop + hold" plan as-is is a **negative-EV strategy** per backtest evidence. Options:

### Option A: Scrap and Pivot to Panic Fade
Replace the entry logic with a `panic_fade` module (96.9% profitable in backtests, documented in `KALSHI_15MIN_COMPLETE_RESEARCH_FINDINGS.md` Section 4.1). Keep the stop-loss and reporting infrastructure. Entry triggers: Kalshi contract price velocity > threshold → fade with large size.

### Option B: Add Coinbase Velocity Gap Fade as Primary Signal
Per `KALSHI_15MIN_COMPLETE_RESEARCH_FINDINGS.md` Section 4.2: when Coinbase BTC 5m > 0.5% + 1m velocity > 0.002% + Kalshi YES < 0.40 → ENTER_YES. 63.6% WR, all 100 variants profitable. This requires adding Coinbase WebSocket/API feed.

### Option C: Keep Architecture, Add Signal Layer
Keep the infrastructure (REST client, WS client, order manager, risk guard, reporting) — it's well-designed. Replace the "every 15 minutes place maker orders" loop with a **signal-driven entry** that only fires when edge is detected (panic_fade, Coinbase gap fade, IWMC carry signal). The 15-minute cadence becomes the window scheduler, not the entry trigger.

**Recommendation: Option C.** The infrastructure is solid. The entry logic needs to be signal-driven, not passive. This is the highest-ROI change with the least code disruption.

---

## 8. Infrastructure ✅ (Keep As-Is)

The following from the plan is correct and should proceed unchanged:
- RSA-PSS auth (config/settings.py, auth.py)
- REST client with retry/backoff
- JSONL trade log (append-only)
- Orderbook parsing (yes_dollars/no_dollars bid-only structure)
- Risk guard (STOP_BOT kill switch, daily loss cap, balance check)
- Report generation (metrics.py, pdf_report.py, generate_report.py)
- .env / requirements.txt setup

---

## 9. Prioritized Fix Checklist

| # | Component | Fix | Priority |
|---|-----------|-----|----------|
| 1 | `order_manager.py` | V2 API: NO entries must use `side="bid", action="sell"`, not "side=ask" | **CRITICAL** |
| 2 | `ws_client.py` | Auth = RSA-PSS signed headers (not token), subscribe to `fill` channel | **CRITICAL** |
| 3 | `orderbook.py` | Penny-inside logic: join book if spread ≤ $0.02; improve only if spread ≥ $0.03 | **CRITICAL** |
| 4 | `main.py` | Replace passive "place every 15m" with signal-driven entry (panic_fade or velocity gap) | **HIGH** |
| 5 | `order_manager.py` | Use batch cancel (`DELETE /portfolio/orders/batch`) instead of sequential DELETE | HIGH |
| 6 | `market_discovery.py` | Add retry with backoff for new-market listing gap; handle inactive status | HIGH |
| 7 | Architecture | Add state persistence (state.json or SQLite) for crash recovery | HIGH |
| 8 | Architecture | Add startup stale-order check + cancel | MEDIUM |
| 9 | `main.py` | Randomized window-open delay (1-3s) | MEDIUM |
| 10 | `risk_guard.py` | Add exchange status check before each window | MEDIUM |
| 11 | `order_manager.py` | Stop-loss width varies by asset tier (BTC/ETH=$0.15, SOL=$0.12, DOGE/XRP=$0.10) | MEDIUM |
| 12 | Architecture | Cap concurrent correlated pairs (BTC+ETH share 1 slot) | MEDIUM |
| 13 | `metrics.py` | Use confirmed fee formula: `round(0.07 × price × (1 − price), 2)` | LOW |
| 14 | Architecture | Add health/heartbeat logging (60s interval) | LOW |
| 15 | `ws_client.py` | Subscribe to `market_lifecycle_v2` for settlement events | LOW |

---

## 10. Conclusion

**Infrastructure: A-** — The REST/WS/auth/reporting architecture is solid, matches Kalshi's V2 API correctly after the few fixes noted. The modular structure is clean and testable.

**Strategy: F** — The passive "place maker-limit orders every 15 minutes" concept is a **known losing archetype** (0/432 profitable in backtests). Without signal-driven entry logic, this bot will bleed capital via fees + adverse fills + correlated stop-outs.

**Fix path:** Implement the infrastructure as planned (with the 15 corrections above), then replace the entry loop with signal-driven triggers. The `panic_fade` and Coinbase velocity gap fade strategies are documented with backtest evidence in the `Kalshi-Docs/` directory. The bot framework can host any strategy — just don't deploy it with the current "passive maker" entry logic against real money.

---

*Analysis compiled from: Kalshi official API docs (docs.kalshi.com, llms.txt), local API specs (openapi.yaml, asyncapi.yaml, Newest Kalshi API Information.md), domain knowledge (kalshi_knowledge.md), strategy research (TurbineFi backtests in KALSHI_15MIN_COMPLETE_RESEARCH_FINDINGS.md, kalshi-15m-strategies.md, strategy-2026-06-27.md), GitHub landscape analysis, and prior bot session learnings.*