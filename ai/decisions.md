# Architecture Decisions
<!-- Append-only. Tag new entries with date and brief context. -->

---

## 2026-07-05 — Window Bot final design decisions

After extensive testing and correction, these are the locked decisions
for the 15-minute crypto window bot:

### Entry Rules
- Initial entry at window open: place orders only when prices are in
  the **0.40-0.60** range.
- If prices are outside range: subscribe to WS, show (waiting for 50/50),
  check prices every 1s via `_asset_mid_prices`. Enter immediately when
  range is hit.
- No price gate for re-entry either — re-entry also checks 0.40-0.60.
- Entry orders: GTC post_only (maker). No price sanity skip — if prices
  never hit range mid-window, transition cleanly to next window.

### Stop-Loss
- **No pre-placed limit stops.** They can't work on a CLOB:
  - With `post_only`: rejected because stop price crosses the spread.
  - Without `post_only`: fills immediately at current market, defeating
    the purpose.
- **WS monitoring + IoC only.** `check_stop_escalation()` fires on every
  `orderbook_delta` WS message (sub-second). When market crosses the stop
  level, fires an IoC order with **5¢ slippage buffer** to ensure fill.
- IoC order: `reduce_only: true`, `time_in_force: immediate_or_cancel`.
- Stop price: `entry_price ± stop_width` (e.g., entry at $0.50, stop_width
  $0.15 → stop at $0.35 for YES, $0.65 for NO).

### Take-Profit
- GTC post_only maker at **0.98** (long YES) / **0.02** (long NO).
- Maker fees ≈ $0 for retail sizes.
- Canceled at **T-60s** so winners ride to $1.00 settlement.
- No `reduce_only` on GTC orders (Kalshi API rejects it).

### Re-entry
- When a **TP or stop fills**: asset added to `reentry_candidates`.
- Re-entry triggers when ALL session assets are in `reentry_candidates`
  AND all cached mid-prices are in 0.40-0.60 AND >3 min to expiry.
- Uses same config pairing (BTC→YES bid, ETH→NO ask, etc.).

### Timing
- All timing from Kalshi market data (`close_time`), not local clock.
- No `_next_window_open()` — continuous discovery via `discover_markets()`.
- 1s loop ticks instead of long sleeps.
- If window close time passes by >30s without settlement event,
  force-clear `current_markets` to avoid hanging.

### Position Reconciliation
- Every 1s during active window: fetch `GET /portfolio/positions`,
  compare against internal `OrderManager.entries`.
- If mismatch: **trust Kalshi**, reduce `filled_count` or clear entry.
- Cancel orphaned TPs on cleared entries.

### TP Cancellation (T-60s)
- Calculated from market `close_time` - 60s.
- Cancels all unfilled take-profits so positions ride to $1 settlement.
- Stop monitoring continues via WS after TP cancellation.
