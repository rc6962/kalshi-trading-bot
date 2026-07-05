# Handoff — 2026-07-05

## Current State
The 15-minute crypto window bot is fully implemented with the following
design (see `ai/decisions.md` for full details):
- Entry at 0.40-0.60 price range only
- WS monitoring + IoC for stops (no pre-placed limit stops)
- TP as GTC post_only maker, canceled at T-60s
- Re-entry when all assets return to 50/50
- Position reconciliation every 1s
- 1s event-driven loop

## Last Commit
`07dba22` — Restore 0.40-0.60 price gate for entry, with proper window
rollover when prices never hit range.

## Files Updated This Session
- `main.py` — core bot logic
- `kalshi/order_manager.py` — order management
- `startup-prompt.md` — updated Kalshi-Docs references to ai/
- `.rules.md` — cleaned up terminal commands section
- `ai/decisions.md` — populated with all locked decisions
- `ai/logs/active/2026-07-05_05-00-00.md` — session log

## Files That Need Attention
- `ai/handoff.md` — was empty, now has this entry
- `ai/decisions.md` — was empty, now populated

## Bot Behavior Summary
- At window open: discovers markets, subscribes WS, checks if prices in
  0.40-0.60. If yes → places entry orders. If no → watches price every
  1s via WS, enters when range hit.
- On entry fill: places TP (GTC maker at 0.98/0.02), starts stop
  monitoring via WS check_stop_escalation.
- Stop fires when market crosses stop_level → IoC with 5¢ slippage buffer.
- TP canceled if not filled by T-60s. Survivors ride to $1 settlement.
- Position reconciliation runs every 1s — trusts Kalshi as source of truth.
- Window rollover is automatic: force-clear current_markets 30s after
  close if WS settlement missed.

## Known Issues / Open Items
- The 0.40-0.60 price gate means the bot won't enter in skewed markets.
  This is intentional.
- No trailing stop or advanced exit logic yet.
- `_stop_price_2()` exists but is unused (no dual limit stops).
