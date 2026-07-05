# Kalshi 15-Min Crypto Window Bot — Session Summary
# Date: 2026-07-05
# Last updated: 2026-07-05

---

## Strategy
- Enter at window open near $0.50 (50/50)
- YES: buy YES at ~$0.50 → place **sell** stop at `$0.50 - stop_width`
- NO: buy NO (sell YES) at ~$0.50 → place **buy** stop at `$0.50 + stop_width`
- Each asset traded independently — don't wait for both fills

## Stop-Loss Logic
User-configurable `stop_width` at startup (default $0.15):
- **YES entries** (side="bid"): dual sell-stops at `$0.50 - stop_width` (primary) and `$0.50 - stop_width + $0.02` (secondary)
- **NO entries** (side="ask"): dual buy-stops at `$0.50 + stop_width` (primary) and `$0.50 + stop_width - $0.02` (secondary)
- When **either** stop fills: cancel the other dual stop + cancel take-profit
- **Limit-first** (avoid taker fees), **IOC fallback** if market passes the stop level
- `check_stop_escalation()` monitors orderbook delta and escalates to IOC if market price crosses stop level

## Take-Profit
- Placed simultaneously with stops on entry fill
- **YES**: sell at $0.98
- **NO**: buy at $0.02
- **Last minute (T-60s)**: cancel all take-profits — let winners ride to settlement ($1.00)

## Key Files
- `main.py` — Window loop, WS callbacks, config, CLI args
- `kalshi/order_manager.py` — Entry/stop/TP placement, fill handling, IOC escalation
- `kalshi/ws_client.py` — WebSocket connection, subscriptions
- `kalshi/rest_client.py` — REST API calls
- `kalshi/orderbook.py` — Orderbook fetching for entry pricing

## WebSocket Subscriptions
`["fill", "market_lifecycle_v2", "orderbook_delta"]`

## Key Data Structures

```python
@dataclass EntryState:
    client_order_id, ticker, asset, side, entry_price
    requested_count, filled_count, remaining_count
    stop_width, order_id
    stop_order_id, stop_client_order_id         # primary
    stop_order_id_2, stop_client_order_id_2    # secondary
    tp_order_id, tp_client_order_id, tp_price, tp_filled
```

```python
@dataclass
class BotConfig:
    yes_assets: list[str]
    no_assets: list[str]
    contracts: int
    stop_width: Decimal
    daily_loss_cap: float
    live_mode: bool
```

## Important API Mechanics (per Kalshi docs)
- **YES/NO equivalence**: NO buy = YES sell internally. Orderbook only returns bids; asks are implied via `1 - price`
- **Rate limits**: Token bucket — 10 tokens/order, 2 tokens/cancel, exponential backoff on 429
- **Time-in-force**: `good_till_canceled` (entry/stop), `immediate_or_cancel` (IOC/stop fallback)
- **`reduce_only: true`** on all stop/TP orders to prevent over-filling
- **`post_only: true`** on entry orders to avoid taker fees
- **`self_trade_prevention_type: taker_at_cross`** on all orders

## REST Endpoints Used
- `POST /portfolio/events/orders` — Create order
- `DELETE /portfolio/events/orders/{order_id}` — Cancel order
- `GET /markets/{ticker}/orderbook` — Get orderbook (public, no auth)
- `GET /exchange/status` — Check exchange status
- `GET /portfolio/balance` — Check balance

## Order Types
| Order | Side | Time-in-Force | Post-Only | Reduce-Only |
|-------|------|---------------|-----------|-------------|
| Entry | bid/ask | good_till_canceled | Yes | No |
| Stop (primary) | opposite | good_till_canceled | Yes | Yes |
| Stop (secondary) | opposite | good_till_canceled | Yes | Yes |
| Stop (IOC fallback) | opposite | immediate_or_cancel | No | Yes |
| Take-Profit | opposite | immediate_or_cancel | No | Yes |

## What Was Done
- Fixed PnL double-counting bug in `_daily_realized_pnl()`
- Fixed race conditions with lock-while-networking
- Fixed CLI argument parsing
- Added take-profit orders on entry fill
- Added dual stops (primary + secondary) per entry
- Added `orderbook_delta` handler for real-time market monitoring
- Added `check_stop_escalation()` and `_escalate_to_ioc()` for IOC fallback when market passes stop levels
- Updated `on_stop_fill()` to cancel dual stops + take-profit when a stop fills
- Commits: `c689f17` (take-profit), `65f64f7` (dual stops + market monitoring)

## What's In Progress / Next Steps
1. ❌ Last-minute TP cancellation (`cancel_all_take_profits()` called T-60s) — needs integration into window loop
2. ❌ Re-entry logic when price returns to 50/50 mid-window
3. ❌ Remove duplicate `_place_ioc_stop_remaining` method in order_manager.py (lines 421-473 and 746-882)

## Verified Against Kalshi Docs
- ✅ Order structure: `side` = "bid"/"ask", prices as dollar strings, counts as fixed-point strings
- ✅ Time-in-force: `good_till_canceled`, `immediate_or_cancel` — both valid
- ✅ REST endpoints: `/portfolio/events/orders` (create), DELETE cancel — correct
- ✅ WS channels: `fill`, `market_lifecycle_v2`, `orderbook_delta` — all valid
- ✅ Orderbook structure: `yes_dollars`/`no_dollars` arrays with `[price, count]` pairs, sorted ascending, highest bid = last element
- ✅ YES/NO equivalence confirmed — orderbook only returns bids, asks implied via `1 - price`
- ✅ Rate limits: Token bucket model — 10 tokens/order, 2 tokens/cancel
- ✅ `reduce_only` flag: Supported and correctly used on stops
- ✅ `post_only` flag: Supported, used on entry orders

## Relevant Documentation
- `Kalshi-Docs/API/Newest Kalshi API Information.md` — Full API reference
- `Kalshi-Docs/API/KALSHIMASTERAPIINDEX.md` — Master API index with all endpoints
- `Kalshi-Docs/kalshi_knowledge.md` — Domain knowledge and confirmed mechanics
- `Kalshi-Docs/API/kalshi_openapi.yaml` — OpenAPI spec
- `Kalshi-Docs/API/kalshi_asyncapi.yaml` — WebSocket spec