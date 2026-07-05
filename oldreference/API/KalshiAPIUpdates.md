I'll research the Kalshi documentation site and related pages to compile a comprehensive reference document for you.This is great news — the Kalshi docs site actually publishes a purpose-built file for AI agents. Let me pull that directly.I found something very useful: Kalshi's documentation site actually has a purpose-built index file at **`https://docs.kalshi.com/llms.txt`** designed specifically for AI agents to reference — every page on docs.kalshi.com includes the note: "Fetch the complete documentation index at: /llms.txt · Use this file to discover all available pages before exploring further." I'd strongly recommend having your IDE agent fetch that URL directly/periodically since it's the canonical, always-current index. Below is a compiled reference document synthesizing everything I found on the RFQ page and its closely linked pages, which you can drop into your repo as `KALSHI_RFQ_REFERENCE.md`.

---

```markdown
# Kalshi RFQ & API Reference (Agent Quick-Reference)

> Source: docs.kalshi.com (getting_started/rfqs + linked pages)
> NOTE: Kalshi publishes a live machine-readable index at https://docs.kalshi.com/llms.txt
> An agent should fetch that file directly for the most current/complete doc index before deep-diving.

## 1. What RFQs Are

Kalshi implements an RFQ (Request for Quote) system for pre-execution communication between members. RFQs allow a requester to solicit quotes from market makers on a specific market and size. Execution follows a two-step lock: accept, then confirm. RFQs are available on any market, including combo (multivariate event) markets.

Quote notifications are NOT delivered on the orderbook channel — quote notifications arrive on the communications WebSocket channel, not the orderbook channel.

## 2. High-Level Flow

1. Requester creates an RFQ specifying a market ticker, size, and whether to rest any remainder. The RFQ is broadcast to all makers.
2. Makers submit quotes (two-sided pricing — see §4).
3. Requester accepts a quote (best price only — per CFTC filing, "the Quoter will be informed of the accepted transaction, and will have 30 seconds to confirm. The Requester can only accept a Quote containing the best price.")
4. After acceptance, the maker has the confirmation window to confirm. Upon confirmation, the platform begins the execution timer.
5. At the end of the timer, orders are entered into the book.
6. Maker confirms within the confirmation window. Once confirmed, neither party can withdraw. After the execution timeout, orders are placed on the public book.
7. Fills: fills appear in GET /portfolio/fills — match on creator_order_id (maker) or rfq_creator_order_id (requester).

**Timing defaults:** Standard confirmation window is 30 seconds ("Market maker confirms willingness to execute after quote acceptance. Quote must be confirmed within 30 seconds of acceptance or it will be voided."). Note: rulebook filings show this window has been adjusted over time for High Volatility Markets (see §5).

## 3. Sizing an RFQ

When creating an RFQ, the requester specifies size in exactly one of: contracts_fp — number of contracts (whole only). target_cost_dollars — dollar amount to spend. The exchange derives a contract count from the quote price, returned as yes_contracts_fp / no_contracts_fp on the quote.

## 4. Quotes — Pricing Rules

- Each quote has two prices: yes_bid (price per YES contract) and no_bid (price per NO contract). These are typically different.
- Either can be "0" to decline that side, but not both. If yes_bid + no_bid > $1 the quote is rejected.
- Quoters do not specify a size — each quote is implicitly for the full RFQ amount (contracts_fp, or whatever count target_cost_dollars resolves to at the quoted prices).
- Prices must land on the market's price grid. Check price_ranges on GET /markets/{ticker} for the valid step size.
- A new quote on the same RFQ replaces the maker's previous quote.

## 5. High Volatility Markets (HVM)

- The exchange designates certain markets as High Volatility Markets (HVM). All combo markets are HVMs. HVMs use shorter confirmation and execution windows.
- Per CFTC rule filings, HVM confirmation windows have been amended over time (values reduced from the standard 30s down to as little as 1-2 seconds in HVMs, per "The Exchange may identify certain markets to be High Volatility Markets ('HVM'). In a HVM, upon Quote acceptance, a Quoter will have only 2 1 seconds... to confirm" — check current live values via API/website since these have changed across rulebook amendments).
- The Exchange will indicate if a market is considered to be a HVM through its website and via the API.

## 6. Combos (Multivariate Events / MVE / "Parlays")

- Combo RFQs include mve_collection_ticker and mve_selected_legs.
- Subscribe to the communications channel (requires auth). rfq_created and rfq_deleted go to all subscribers. quote_created, quote_accepted, and quote_executed go only to the involved requester and maker. Combo RFQs include mve_collection_ticker and mve_selected_legs.
- Real-world context: Kalshi used RFQs to power NFL parlay products — "When a Kalshi retail bettor chooses multiple outcomes they want to combine into a single bet, market makers offer lines through an anonymous bidding system. The best offer within that split-second timeframe is presented to the retail bettor, who can then confirm or cancel their attempted wager."

## 7. WebSocket / Communications Channel

- Communications: Real-time Request for Quote (RFQ) and quote notifications. Requires authentication.
- Events emitted: `rfq_created`, `rfq_deleted` (broadcast to all subscribers); `quote_created`, `quote_accepted`, `quote_executed` (only to involved parties).
- General WS channel groups: Private channels (user-specific data): orderbook_delta, fill, market_positions, communications, order_group_updates · Public market-data channels (no additional channel-level auth): ticker, trade, market_lifecycle_v2, multivariate_market_lifecycle, multivariate
- Endpoints: production `wss://external-api-ws.kalshi.com/trade-api/ws/v2`; demo `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2`; legacy hosts "wss://api.elections.kalshi.com/trade-api/ws/v2 for production and wss://demo-api.kalshi.co/trade-api/ws/v2 for demo, remain supported."

## 8. REST Endpoints — RFQ / Quotes (Communications group)

Base: `https://external-api.kalshi.com/trade-api/v2` (or `https://api.elections.kalshi.com/...` legacy host)

| Method | Path | Purpose |
|---|---|---|
| GET | `/communications/rfqs` | List RFQs (paginated via cursor) |
| POST | `/communications/rfqs` | Create RFQ |
| GET | `/communications/rfqs/{rfq_id}` | Get single RFQ |
| DEL | `/communications/rfqs/{rfq_id}` | Delete/cancel RFQ |
| GET | `/communications/quotes` | List Quotes (paginated) |
| POST | `/communications/quotes` | Create Quote (maker) |
| GET | `/communications/quotes/{quote_id}` | Get single Quote |
| DEL | `/communications/quotes/{quote_id}` | Delete/cancel Quote |
| PUT | `/communications/quotes/{quote_id}/accept` | Accept Quote (requester) |
| PUT | `/communications/quotes/{quote_id}/confirm` | Confirm Quote (maker) |

### Create RFQ — request body fields
market_ticker, rest_remainder, contracts, contracts_fp, target_cost_centi_cents, target_cost_dollars, replace_existing, subtrader_id, subaccount

- Endpoint for creating a new RFQ. You can have a maximum of 100 open RFQs at a time.
- The number of contracts for the RFQ. Whole contracts only. Contracts may be provided via contracts or contracts_fp; if both provided they must match.
- The subaccount number to create the RFQ for (direct members only; 0 for primary, 1-32 for subaccounts)

### RFQ object fields (GET /communications/rfqs response)
`id, creator_id, market_ticker, contracts_fp, status, created_ts, target_cost_dollars, mve_collection_ticker, mve_selected_legs[event_ticker, market_ticker, side, yes_settlement_value_dollars], rest_remainder, cancellation_reason, creator_user_id, creator_subaccount, cancelled_ts, updated_ts`

### Quote object fields (GET /communications/quotes response)
`id, rfq_id, creator_id, rfq_creator_id, market_ticker, contracts_fp, yes_bid_dollars, no_bid_dollars, created_ts, updated_ts, status, accepted_side, accepted_ts, confirmed_ts, executed_ts, cancelled_ts, rest_remainder, cancellation_reason, creator_user_id, rfq_creator_user_id, rfq_target_cost_dollars, rfq_creator_order_id, creator_order_id, yes_contracts_fp, no_contracts_fp`

### Filtering notes (from changelog)
- GET /trade-api/v2/communications/quotes no longer supports filtering by market_ticker or event_ticker, effective immediately. Requests should filter quotes by user, RFQ, status, or update time instead.
- Added rfq_user_filter to GetQuotes for filtering by quotes in response to RFQs created by the authenticated user.
- Retention: Closed RFQs and cancelled quotes returned by the communications APIs will be retained for 7 days after their last update, reduced from the previous 14-day retention window.
- Fixed missing fields in Quote responses: rfq_target_cost_centi_cents, rfq_creator_order_id, and creator_order_id are now properly included in all Quote-related endpoints.

## 9. FIX API — RFQ Messages

- RFQ Creators use the KalshiRT endpoint (same as order entry), which provides message persistence and retransmission support. Market Makers use the KalshiRFQ endpoint to receive RFQ broadcasts and submit quotes.
- MVE/Parlay Support: Instead of specifying a Symbol, you can submit MVE legs directly. The server will automatically resolve or create the parlay market and return the resolved market ticker in the QuoteRequestAck.
- Exchange response to an inbound QuoteRequest from an RFQ creator. The server-assigned RFQ ID is returned in tag 21023.
- RFQCancel accepts either your original client-assigned QuoteReqId (tag 131) or the server-assigned RfqId (tag 21023).
- Exchange → Creator: Notify creator of a new quote. If a new Quote is created when an existing quote for the same market already exists for the user, the exchange will cancel the existing quote. Either BidPx or OfferPx can be zero, but not both.
- Quote lifecycle statuses: In response to a Quote, Status will be PENDING if processed, or REJECTED if rejected. When the requester accepts the quote, Status will be ACCEPTED. In response to a QuoteCancel, Status will be CANCELLED
- Confirm window: Market maker confirms willingness to execute after quote acceptance. Quote must be confirmed within 30 seconds of acceptance or it will be voided.
- Changelog: FIX RFQ Quote (35=S) notifications sent to RFQ creators now include the quoter's public communications ID in NoPartyIDs with PartyRole=35 (Liquidity Provider).

## 10. Authentication (applies to all RFQ/REST calls)

Every authenticated request needs 3 headers, signed with your RSA private key:
- `KALSHI-ACCESS-KEY` — your Key ID
- `KALSHI-ACCESS-SIGNATURE` — RSA-PSS signature
- `KALSHI-ACCESS-TIMESTAMP` — request timestamp in ms

The signature is generated by signing a concatenation of the timestamp, the HTTP method and the path. When signing requests, use the path without query parameters. For example, if your request is to /trade-api/v2/portfolio/orders?limit=5, sign only /trade-api/v2/portfolio/orders.

Getting a key: Log in to your account and navigate to the "Account Settings" page. In the "Profile Settings" page https://kalshi.com/account/profile, locate the "API Keys" section. Click on the "Create New API Key" button. Important: for security reasons, the private key will not be stored by our service, and you will not be able to retrieve it again once this page is closed.

Restricted (subaccount-scoped) keys: Pass subaccount (0-63) to POST /api_keys or POST /api_keys/generate. A restricted key may only read and trade on that one sub-account: requests that target another sub-account are rejected, and the key cannot transfer funds between sub-accounts or create sub-accounts. Restricted keys can use supported REST and FIX order-entry or market-data sessions; they cannot open WebSocket, FIX listener, drop-copy, RFQ, or retransmission sessions. — **important gotcha: subaccount-restricted keys cannot open RFQ sessions.**

## 11. Rate Limits (relevant when polling RFQ/quote endpoints)

Per third-party summary of Kalshi docs: Rate limiting is a token bucket since 2026-04-23, with independent Read and Write buckets and five tiers (Basic 200/100, Advanced 300/300, Premier 1000/1000, Paragon 2000/2000, Prime 4000/4000 tokens/second). Default cost per request is 10 tokens. Two traps: 429 responses carry no Retry-After and no X-RateLimit-* headers (use exponential backoff with jitter), and batched orders do not save tokens. Live budget: `GET /account/limits`; per-endpoint cost: `GET /account/endpoint_costs`.

## 12. Related Endpoints Useful for RFQ Workflows

- `GET /markets/{ticker}` — check `price_ranges` for valid quote price grid (step size).
- `GET /markets/{ticker}/orderbook` — the order book shows all active bid orders for both yes and no sides of a binary market. It returns yes bids and no bids only (no asks are returned). This is because in binary markets, a bid for yes at price X is equivalent to an ask for no at price (100-X). For example, a yes bid at 7¢ is the same as a no ask at 93¢, with identical contract sizes.
- `GET /portfolio/fills` — to reconcile executed RFQ trades (match on `creator_order_id` / `rfq_creator_order_id`).
- `GET /multivariate_event_collections/...` — for combo/MVE market lookups and creation used by combo RFQs (Get Multivariate Event Collection, Create Market In Multivariate Event Collection, Get Multivariate Event Collection Lookup History, Lookup Tickers For Market In Multivariate Event Collection).

## 13. Regulatory / Design Background (context, not API)

- RFQs were introduced under CFTC self-certification. Historically the mechanism drew scrutiny: the CFTC worried RFQs could hamper open market price competition, with then-CFTC director of market oversight writing that "the RFQ functionality may not provide a competitive, open, and efficient market."
- Kalshi's position: "Market participants still have queue priority under the Kalshi system, and thus have a meaningful opportunity to execute against the order. And participants in the RFQ system are prohibited from taking advantage of the limited non-public" information.
- All RFQ-derived trades ultimately post to the central book: "All RFQ transactions would occur on the centralized order book, and in fact would cede priority to existing resting orders."
- Anyone can technically be a maker, though in practice it's mostly automated/quant participants: "Technically, anyone can become an RFQ market maker. In practice, though, Kalshi's parlay oddsmakers are not the typical user... The process requires onboarding with Kalshi's back-end API trading technology, a basic understanding of the coding language Python and the ability to come up with competitive odds in seconds."

## 14. Quick Links (fetch directly for latest content)

- Master agent index: `https://docs.kalshi.com/llms.txt`
- RFQ concept page: `https://docs.kalshi.com/getting_started/rfqs`
- REST reference (Communications group): `https://docs.kalshi.com/api-reference/communications/*`
- FIX RFQ messages: `https://docs.kalshi.com/fix/rfq-messages`
- WebSocket overview: `https://docs.kalshi.com/websockets`
- API Keys / auth: `https://docs.kalshi.com/getting_started/api_keys`
- Changelog (subscribe to RSS): `https://docs.kalshi.com/changelog` / `/changelog/rss.xml`
- Market Lifecycle: `https://docs.kalshi.com/getting_started/market_lifecycle`
- OpenAPI spec: `openapi.yaml` (event-contract REST), `asyncapi.yaml` (WS), `perps_openapi.yaml` (perps REST) — all linked from the Welcome page.

---
*Compiled from docs.kalshi.com pages plus CFTC rule-certification filings and third-party developer summaries for HVM timing history and rate-limit specifics. Timing values for HVM confirmation windows have changed across multiple rulebook amendments — always verify current values via `GET /markets/{ticker}` (HVM flag) or the live docs before relying on hardcoded seconds.*
```

---

A few practical notes for you:

1. **Best long-term solution**: have your IDE agent fetch `https://docs.kalshi.com/llms.txt` directly on demand — it's Kalshi's own agent-facing index and will always be more current than any static file I hand you, since Kalshi actively revises RFQ/HVM timing parameters (I found conflicting values of 1s vs 2s in recent CFTC filings from Jan 2026, suggesting this is actively changing).
2. Save the markdown above as a file in the repo (e.g., `docs/KALSHI_RFQ_REFERENCE.md`) — that gives your agent a fast, offline-first cheat sheet with inline source citations for anything that needs verification.
3. For exact current numeric values (HVM confirmation window, rate-limit tiers, exact endpoint costs), I'd treat the doc's live pages / `GET /markets/{ticker}` HVM flag / `GET /account/limits` as ground truth over any static snapshot.