# KALSHI API — MASTER INDEX & AGENT REFERENCE
# Primary source: https://docs.kalshi.com/llms.txt
# Companion detail: KALSHI_API_REFERENCE.md (or see Section 3 onward below)
# Last verified: July 2026
#
# ── HOW TO USE THIS FILE ────────────────────────────────────────────────────
# 1. This file IS the table of contents (llms.txt) + digested detail in one.
# 2. Every page known to Kalshi is listed in Section 2 with its URL.
# 3. Fetch any URL for deeper schema / code samples.
# 4. Always check /changelog for breaking changes before deploying.
# ────────────────────────────────────────────────────────────────────────────

---

## SECTION 1 — AGENT BOOTSTRAP INSTRUCTIONS

- Canonical doc index:    https://docs.kalshi.com/llms.txt
- Fetch this URL first to discover ALL available pages.
- REST prod base URL:     https://external-api.kalshi.com/trade-api/v2
- REST demo base URL:     https://external-api.demo.kalshi.co/trade-api/v2
- WS prod:                wss://external-api-ws.kalshi.com/trade-api/ws/v2
- WS demo:                wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2
- WS legacy (still works): wss://api.elections.kalshi.com/trade-api/ws/v2 (prod)
                            wss://demo-api.kalshi.co/trade-api/ws/v2 (demo)
- Changelog RSS:          https://docs.kalshi.com/changelog/rss.xml
- OpenAPI specs:          openapi.yaml (REST) · asyncapi.yaml (WS) · perps_openapi.yaml (Perps)

---

## SECTION 2 — COMPLETE PAGE INDEX (from llms.txt)

Each entry = Title : Description : URL

### ── GETTING STARTED ──────────────────────────────────────────────────────

| Title                                       | Description                                                                 | URL |
|---------------------------------------------|-----------------------------------------------------------------------------|-----|
| Welcome / Making Your First Request         | Start trading with Kalshi API in under 5 minutes                            | https://docs.kalshi.com/welcome |
| Market Lifecycle                            | How markets move from creation to settlement                                | https://docs.kalshi.com/getting_started/market_lifecycle |
| Orderbook Responses                         | Understanding Kalshi orderbook structure and binary prediction market mechanics | https://docs.kalshi.com/getting_started/orderbook_responses |
| Understanding Pagination                    | Learn how to navigate large datasets using cursor-based pagination          | https://docs.kalshi.com/getting_started/pagination |
| Quick Start: Authenticated Requests (No SDK)| Three simple steps to make your first authenticated API request to Kalshi   | https://docs.kalshi.com/getting_started/quick_start_authenticated_requests |
| Quick Start: Create Your First Order (No SDK)| Find markets, place orders, check status, and cancel orders on Kalshi      | https://docs.kalshi.com/getting_started/quick_start_orders |
| Quick Start: Market Data (No SDK)           | Access real-time market data without authentication                         | https://docs.kalshi.com/getting_started/quick_start_market_data |
| Quick Start: WebSockets (No SDK)            | Establish and maintain a WebSocket connection to stream real-time market data | https://docs.kalshi.com/getting_started/quick_start_websockets |
| RFQs                                        | Request for Quote functionality for prediction markets                      | https://docs.kalshi.com/getting_started/rfqs |
| Rate Limits & Tiers                         | Token-bucket rate limit model, tiers, and bursting rules                    | https://docs.kalshi.com/getting_started/rate_limits |
| Historical Data                             | Accessing historical exchange data via the Kalshi API                       | https://docs.kalshi.com/getting_started/historical_data |
| Kalshi Glossary                             | Core terminology used in the Kalshi exchange                                | https://docs.kalshi.com/getting_started/glossary |

---

### ── WEBSOCKET CHANNELS ───────────────────────────────────────────────────

| Title                               | Auth Required | Description                                                              | URL |
|-------------------------------------|---------------|--------------------------------------------------------------------------|-----|
| WebSocket API Overview              | Yes (handshake) | Trade API WebSocket endpoint and schema reference                       | https://docs.kalshi.com/websockets |
| Communications                      | Yes           | Real-time RFQ and quote notifications                                    | https://docs.kalshi.com/websockets/communications |
| Connection Keep-Alive               | No            | WebSocket control frames for connection management                       | https://docs.kalshi.com/websockets/connection_keepalive |
| Market & Event Lifecycle            | No            | Market state changes and event creation notifications                    | https://docs.kalshi.com/websockets/market_lifecycle |
| Market Positions                    | Yes           | Real-time updates of your positions in markets                           | https://docs.kalshi.com/websockets/market_positions |
| Market Ticker                       | No            | Market price, volume, and open interest updates                          | https://docs.kalshi.com/websockets/market_ticker |
| Multivariate Lookups                | No            | Multivariate collection lookup notifications                             | https://docs.kalshi.com/websockets/multivariate_lookups |
| Multivariate Market & Event Lifecycle | No          | MVE market state changes and event creation notifications                | https://docs.kalshi.com/websockets/multivariate_market_lifecycle |
| Order Group Updates                 | Yes           | Real-time order group lifecycle and limit updates                        | https://docs.kalshi.com/websockets/order_group_updates |

---

### ── REST API REFERENCE — PREDICTIONS ───────────────────────────────────

#### Markets
| Endpoint                        | URL |
|---------------------------------|-----|
| Get Markets (list)              | https://docs.kalshi.com/api-reference/markets/get-markets |
| Get Market (single)             | https://docs.kalshi.com/api-reference/markets/get-market |
| Get Market Orderbook            | https://docs.kalshi.com/api-reference/markets/get-market-orderbook |
| Get Market Candlesticks         | https://docs.kalshi.com/api-reference/markets/get-market-candlesticks |
| Get Trades                      | https://docs.kalshi.com/api-reference/markets/get-trades |

#### Events & Series
| Endpoint                        | URL |
|---------------------------------|-----|
| Get Events (list)               | https://docs.kalshi.com/api-reference/events/get-events |
| Get Event (single)              | https://docs.kalshi.com/api-reference/events/get-event |
| Get Series (list)               | https://docs.kalshi.com/api-reference/series/get-series |
| Get Series (single)             | https://docs.kalshi.com/api-reference/series/get-series-single |

#### Orders
| Endpoint                        | URL |
|---------------------------------|-----|
| Create Order                    | https://docs.kalshi.com/api-reference/orders/create-order |
| Get Orders (list)               | https://docs.kalshi.com/api-reference/orders/get-orders |
| Get Order (single)              | https://docs.kalshi.com/api-reference/orders/get-order |
| Cancel Order                    | https://docs.kalshi.com/api-reference/orders/cancel-order |
| Amend Order                     | https://docs.kalshi.com/api-reference/orders/amend-order |

#### Portfolio
| Endpoint                        | URL |
|---------------------------------|-----|
| Get Balance                     | https://docs.kalshi.com/api-reference/portfolio/get-balance |
| Get Fills                       | https://docs.kalshi.com/api-reference/portfolio/get-fills |
| Get Positions                   | https://docs.kalshi.com/api-reference/portfolio/get-positions |
| Get Portfolio Settlements       | https://docs.kalshi.com/api-reference/portfolio/get-portfolio-settlements |

#### Communications (RFQs & Quotes)
| Endpoint                        | URL |
|---------------------------------|-----|
| Create RFQ                      | https://docs.kalshi.com/api-reference/communications/create-rfq |
| Get RFQs (list)                 | https://docs.kalshi.com/api-reference/communications/get-rfqs |
| Get RFQ (single)                | https://docs.kalshi.com/api-reference/communications/get-rfq |
| Delete RFQ                      | https://docs.kalshi.com/api-reference/communications/delete-rfq |
| Create Quote                    | https://docs.kalshi.com/api-reference/communications/create-quote |
| Get Quotes (list)               | https://docs.kalshi.com/api-reference/communications/get-quotes |
| Get Quote (single)              | https://docs.kalshi.com/api-reference/communications/get-quote |
| Delete Quote                    | https://docs.kalshi.com/api-reference/communications/delete-quote |
| Accept Quote                    | https://docs.kalshi.com/api-reference/communications/accept-quote |
| Confirm Quote                   | https://docs.kalshi.com/api-reference/communications/confirm-quote |
| Get Communications ID           | https://docs.kalshi.com/api-reference/communications/get-communications-id |

#### Multivariate Events (MVE / Combo)
| Endpoint                        | URL |
|---------------------------------|-----|
| Get MVE Collections (list)      | https://docs.kalshi.com/api-reference/multivariate/get-collections |
| Get MVE Collection (single)     | https://docs.kalshi.com/api-reference/multivariate/get-collection |
| Create MVE Market               | https://docs.kalshi.com/api-reference/multivariate/create-market |
| MVE Lookup                      | https://docs.kalshi.com/api-reference/multivariate/lookup |
| Get MVE Lookup History          | https://docs.kalshi.com/api-reference/multivariate/get-lookup-history |

#### Exchange & API Keys
| Endpoint                        | URL |
|---------------------------------|-----|
| Get Exchange Status             | https://docs.kalshi.com/api-reference/exchange/get-exchange-status |
| Get Exchange Schedule           | https://docs.kalshi.com/api-reference/exchange/get-exchange-schedule |
| Create API Key                  | https://docs.kalshi.com/api-reference/api-keys/create-api-key |
| Get API Keys (list)             | https://docs.kalshi.com/api-reference/api-keys/get-api-keys |
| Delete API Key                  | https://docs.kalshi.com/api-reference/api-keys/delete-api-key |

---

### ── FIX API ──────────────────────────────────────────────────────────────

| Title                    | Description                                                               | URL |
|--------------------------|---------------------------------------------------------------------------|-----|
| FIX API Overview         | Financial Information eXchange (FIX) protocol implementation for Kalshi  | https://docs.kalshi.com/fix/overview |
| Connectivity             | Connection setup and endpoints for Kalshi FIX API                        | https://docs.kalshi.com/fix/connectivity |
| Session Management       | Managing FIX sessions including logon, logout, and message sequencing    | https://docs.kalshi.com/fix/session_management |
| Order Entry Messages     | Submit, modify, and cancel orders through FIX messages                   | https://docs.kalshi.com/fix/order_entry_messages |
| Order Group Messages     | Manage order groups for automatic position management                    | https://docs.kalshi.com/fix/order_group_messages |
| RFQ Messages             | Request for Quote functionality for RFQ creators and market makers       | https://docs.kalshi.com/fix/rfq_messages |
| Drop Copy Session        | Recover missed execution reports and query historical order events       | https://docs.kalshi.com/fix/drop_copy |
| Listener Sessions        | Real-time read-only feed of execution reports from your trading session  | https://docs.kalshi.com/fix/listener_sessions |
| Market Settlement (FIX)  | Settlement reports for market outcomes and position resolution           | https://docs.kalshi.com/fix/market_settlement |
| Error Handling (FIX)     | Understanding and handling errors in the FIX protocol                   | https://docs.kalshi.com/fix/error_handling |
| Subpenny Pricing (FIX)   | Dollar-based pricing format for subpenny precision                      | https://docs.kalshi.com/fix/subpenny_pricing |

---

### ── PYTHON SDK ───────────────────────────────────────────────────────────

| Title                         | Description                                   | URL |
|-------------------------------|-----------------------------------------------|-----|
| Python SDK: ApiKeys           | SDK methods for ApiKeys operations            | https://docs.kalshi.com/python-sdk/api/ApiKeysApi |
| Python SDK: Communications    | SDK methods for Communications / RFQ ops      | https://docs.kalshi.com/python-sdk/api/CommunicationsApi |
| Python SDK: Markets           | SDK methods for Markets operations            | https://docs.kalshi.com/python-sdk/api/MarketsApi |
| Python SDK: Orders            | SDK methods for Orders operations             | https://docs.kalshi.com/python-sdk/api/OrdersApi |
| Python SDK: Portfolio         | SDK methods for Portfolio operations          | https://docs.kalshi.com/python-sdk/api/PortfolioApi |
| Python SDK: Multivariate      | SDK methods for Multivariate Event operations | https://docs.kalshi.com/python-sdk/api/MultivariateApi |
| Python SDK: Events            | SDK methods for Events operations             | https://docs.kalshi.com/python-sdk/api/EventsApi |
| Python SDK: Exchange          | SDK methods for Exchange operations           | https://docs.kalshi.com/python-sdk/api/ExchangeApi |
| Python SDK: Market Model      | Market model schema reference                 | https://docs.kalshi.com/python-sdk/models/Market |

```bash
# Install
pip install kalshi-python-sync   # synchronous
pip install kalshi-python-async  # asynchronous