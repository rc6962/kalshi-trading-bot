# KALSHI PREDICTION MARKETS — AGENT QUICK-REFERENCE
# Source: https://docs.kalshi.com (docs.kalshi.com/getting_started/rfqs and all related pages)
# Last verified: July 2026
# Full doc index: https://docs.kalshi.com/llms.txt

---

## 1. PLATFORM OVERVIEW

- Kalshi is the first CFTC-regulated prediction market exchange in the United States.
- Offers binary event contracts that settle to $1 (YES) or $0 (NO).
- Traders buy and sell contracts representing the probability of real-world events.
- Regulated as a Designated Contract Market (DCM) under CFTC oversight.
- Fiat-based (USD) settlement; off-chain order matching via central limit order book (CLOB).
- API is completely free to access. No subscription or per-request fees.
- Official docs: https://docs.kalshi.com
- Official OpenAPI spec: download `openapi.yaml` (REST), `asyncapi.yaml` (WebSocket), `perps_openapi.yaml` (Perps).

---

## 2. API SURFACES

| Surface    | Protocol        | Use Case                                |
|------------|-----------------|----------------------------------------|
| REST       | HTTPS           | Market data, orders, portfolio, RFQs   |
| WebSocket  | WSS             | Real-time streaming updates            |
| FIX 4.4    | FIX Protocol    | Institutional-grade order entry        |

- Both Predictions (event-contract) and Margin/Perps exchanges are supported.
- REST and WebSocket APIs covered in this document.

---

## 3. BASE URLS

| Environment | REST Base URL                                              |
|-------------|-----------------------------------------------------------|
| Production  | https://external-api.kalshi.com/trade-api/v2              |
| Demo/Test   | (separate demo environment — always test here first)      |

- WebSocket: `wss://api.kalshi.com/trade-api/ws/v2`
- Always develop and test against the demo environment before production.
- Note: Despite legacy subdomain naming, the production Trade API covers ALL Kalshi markets
  (economics, climate, technology, entertainment, elections, sports, etc.).

---

## 4. AUTHENTICATION

### Method: RSA-PSS Signed Requests

- Generate an API key pair in Settings → API in your Kalshi dashboard.
- You receive: an API Key ID + a private RSA key.
- Never share or commit keys to version control.
- Keys can optionally be restricted to a single subaccount (pass `subaccount` 0–63 to POST /api_keys).

### Signing Algorithm (Manual Implementation)

For every authenticated request, build the signing message:
  `{timestamp_ms}{HTTP_METHOD}{path}`

- Path includes the `/trade-api/v2` prefix, excludes the query string.
- Sign with RSA-PSS, SHA-256 for both hash and MGF1, salt length = digest length (32 bytes).
- Base64-encode the resulting signature.

### Required Headers (Authenticated Requests)