<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# [https://docs.kalshi.com/api-reference/exchange/get-exchange-announcements](https://docs.kalshi.com/api-reference/exchange/get-exchange-announcements)

Now I have all the information needed. Let me create a comprehensive markdown file for you.<tool_call>execute_code</arg_value><arg_key>code</arg_key><arg_value>
import os

output_dir = os.path.expanduser("~")
file_path = os.path.join(output_dir, "kalshi_api_reference.md")

content = r'''\# Kalshi API Complete Reference for AI

> **Purpose:** This document is a comprehensive reference for the Kalshi Exchange API, covering REST, WebSocket, and FIX interfaces. It is optimized for AI-assisted development of trading bots and automated systems.

***

## Table of Contents

1. [Overview](#1-overview)
2. [API Environments \& Base URLs](#2-api-environments--base-urls)
3. [Authentication](#3-authentication)
4. [Rate Limits \& Tiers](#4-rate-limits--tiers)
5. [REST API Endpoints](#5-rest-api-endpoints)
6. [WebSocket API](#6-websocket-api)
7. [Pagination](#7-pagination)
8. [Orderbook Structure](#8-orderbook-structure)
9. [Order Lifecycle](#9-order-lifecycle)
10. [Code Examples](#10-code-examples)
11. [Key Concepts](#11-key-concepts)

***

## 1. Overview

Kalshi is a CFTC-regulated exchange offering event-contract markets (predictions) and perpetual futures (perps). The API provides:

- **Predictions APIs**: Event-contract markets via REST, WebSocket, and FIX
- **Perps APIs**: Perpetual futures (margin) via REST, WebSocket, and FIX


### API Categories

| Category | Description |
| :-- | :-- |
| Predictions REST | Event-contract markets REST API |
| Predictions WebSocket | Real-time event-contract market data |
| Perps REST | Perpetual futures REST API |
| Perps WebSocket | Real-time perps market data |
| FIX | Financial Information eXchange protocol support |


***

## 2. API Environments \& Base URLs

Kalshi provides separate **production** and **demo** environments. Credentials are NOT shared between environments.

### REST API Base URLs

| Environment | Recommended Base URL | Also Supported |
| :-- | :-- | :-- |
| Production | `https://external-api.kalshi.com/trade-api/v2` | `https://api.elections.kalshi.com/trade-api/v2` |
| Demo | `https://external-api.demo.kalshi.co/trade-api/v2` | `https://demo-api.kalshi.co/trade-api/v2` |

> **Note:** Despite the `elections` subdomain, the production Trade API provides access to ALL Kalshi markets, not only election-related ones.

### WebSocket API URLs

| Environment | Recommended URL | Also Supported |
| :-- | :-- | :-- |
| Production | `wss://external-api-ws.kalshi.com/trade-api/ws/v2` | `wss://api.elections.kalshi.com/trade-api/ws/v2` |
| Demo | `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` | `wss://demo-api.kalshi.co/trade-api/ws/v2` |

### Private Connectivity

For network-level isolation, Kalshi supports **AWS PrivateLink** for REST and WebSocket APIs. Traffic is routed entirely within AWS backbone, never traversing the public internet. Available for production hosts `external-api.kalshi.com` (REST) and `external-api-ws.kalshi.com` (WebSocket). Contact `institutional@kalshi.com` to provision.

### Request Signing

The host does not change the signature payload. **Sign the full request path from the API root, without query parameters.**

Example: For `https://external-api.kalshi.com/trade-api/v2/portfolio/orders?limit=5`, sign:

```
/trade-api/v2/portfolio/orders
```


***

## 3. Authentication

### Generating API Keys

1. Log in to your Kalshi account (demo: `https://demo.kalshi.co` or production: `https://kalshi.com`)
2. Navigate to **Account \& security** → **API Keys**
3. Click **Create Key**
4. Save both:
    - **Private Key**: Downloaded as a `.key` file (RSA_PRIVATE_KEY format)
    - **API Key ID**: Displayed on screen (e.g., `a952bcbe-ec3b-4b5b-b8f9-11dae589608c`)

> **Warning:** Your private key cannot be retrieved after the page is closed. Store it securely!

### Required Headers for Authenticated Requests

| Header | Description | Example |
| :-- | :-- | :-- |
| `KALSHI-ACCESS-KEY` | Your API Key ID | `a952bcbe-ec3b-4b5b-b8f9-11dae589608c` |
| `KALSHI-ACCESS-TIMESTAMP` | Current time in milliseconds | `1703123456789` |
| `KALSHI-ACCESS-SIGNATURE` | Request signature (RSA-PSS signed) | `base64_encoded_signature` |

### Signature Creation Process

1. **Create message string**: Concatenate `timestamp + HTTP_METHOD + path`
    - Example: `1703123456789GET/trade-api/v2/portfolio/balance`
    - **Important**: Sign the full URL path from the API root, WITHOUT query parameters
2. **Sign with private key**: Use RSA-PSS with SHA256
3. **Encode as base64**: Convert the signature to a base64 string

### Python Signing Function

```python
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

def sign_request(private_key, timestamp, method, path):
    path_without_query = path.split('?')[^0]
    message = f"{timestamp}{method}{path_without_query}".encode('utf-8')
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')
```


### JavaScript Signing Function

```javascript
const crypto = require('crypto');

function signPssText(privateKeyPem, text) {
    const sign = crypto.createSign('RSA-SHA256');
    sign.update(text);
    sign.end();
    const signature = sign.sign({
        key: privateKeyPem,
        padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
        saltLength: crypto.constants.RSA_PSS_SALTLEN_DIGEST,
    });
    return signature.toString('base64');
}
```


### Common Authentication Issues

| Problem | Solution |
| :-- | :-- |
| 401 Unauthorized | Check your API Key ID and private key file path |
| Signature error | Ensure timestamp is in milliseconds (not seconds) |
| Path not found | If BASE_URL already ends with `/trade-api/v2`, pass only the endpoint path (e.g., `/portfolio/balance`) |
| Signature error with query params | Sign the request path WITHOUT query parameters. Use `path.split('?')[^0]` |


***

## 4. Rate Limits \& Tiers

### Token-Based Limits

Every authenticated request costs **tokens**. Your tier sets your budget (tokens per second) at which your balance refills. Most requests cost the default of **10 tokens**.

### Read and Write Buckets

You have two independent token budgets:


| Bucket | Covers |
| :-- | :-- |
| **Read** | `GET` endpoints and anything not routed to Write |
| **Write** | Order placement, amends, cancels, order groups, RFQ quote flow, block trade proposal accepts |

The split is by operation type, not by protocol. REST and FIX requests drain the same buckets.

### Bucket Capacity and Bursting

- Basic and Advanced Predictions Read buckets, and Write buckets above Basic tier: hold up to **2 seconds of budget**
- After 2 quiet seconds, bucket is full → can spend up to **2x per-second budget in a single burst**
- Predictions Read buckets above Advanced, Perps Read buckets, and Basic-tier Write buckets: hold **1 second of budget**


### Rate Limit Response

A rate-limited request returns `429 Too Many Requests`:

```json
{"error": "too many requests"}
```

- No `Retry-After` or `X-RateLimit-*` headers
- No penalty or cooldown
- Bucket keeps refilling; next request succeeds once balance covers cost
- Apply exponential backoff on 429


### Batch Endpoints

Batch requests do NOT save tokens. Every item is billed separately:

- Batch Create Orders: 25 orders = 25 × 10 = 250 tokens
- Batch Cancel Orders: 25 cancels = 25 × 2 = 50 tokens
- The whole batch must fit in the bucket at once


### Perps Limits

Perps API uses the same bucket mechanics but in **separate** Read and Write buckets. Perps calls do not draw down event-contract budgets and vice versa. You effectively have up to 4 independent buckets.

### Tiers and Budgets

| Tier | Read Budget (tokens/sec) | Write Budget (tokens/sec) |
| :-- | :-- | :-- |
| Basic | 200 | 100 |
| Advanced | 300 | 300 |
| Expert | 600 | 600 |
| Premier | 1,000 | 1,000 |
| Paragon | 2,000 | 2,000 |
| Prime | 4,000 | 4,000 |
| Prestige | 6,000 | 8,000 |

> Write bucket capacity is **twice** the per-second budget above the Basic tier.

### Tier Qualification

- **Basic**: Complete account signup
- **Advanced**: Call the Upgrade Account API Usage Level endpoint
- **Expert, Premier, Paragon, Prime, Prestige**: Earned automatically from trading volume or assigned by Kalshi


### Volume Share Calculation

```
volume share = your trailing 30-day volume ÷ (previous month's exchange volume × 2)
```

| Tier | Earn (volume share) | Keep (volume share) |
| :-- | :-- | :-- |
| Expert | 0.075% | 0.05% |
| Premier | 0.125% | 0.10% |
| Paragon | 0.25% | 0.20% |
| Prime | 0.50% | 0.40% |
| Prestige | 1.00% | 0.80% |


***

## 5. REST API Endpoints

### Exchange Endpoints

| Method | Endpoint | Description |
| :-- | :-- | :-- |
| GET | `/exchange/status` | Get exchange status |
| GET | `/exchange/announcements` | Get exchange-wide announcements |
| GET | `/exchange/series_fee_changes` | Get series fee changes |
| GET | `/exchange/schedule` | Get exchange schedule |
| GET | `/exchange/user_data_timestamp` | Get user data timestamp |

#### Get Exchange Announcements

```
GET /exchange/announcements
```

**Response (200):**

```json
{
  "announcements": [
    {
      "message": "",
      "delivery_time": "2023-11-07T05:31:56Z"
    }
  ]
}
```

**Response Fields:**

- `announcements` (object[], required): A list of exchange-wide announcements
    - `message` (string): The announcement message
    - `delivery_time` (string): ISO 8601 timestamp of delivery


### Market Endpoints

| Method | Endpoint | Description |
| :-- | :-- | :-- |
| GET | `/markets` | List markets (filter by series, event, status) |
| GET | `/markets/{ticker}` | Get single market details |
| GET | `/markets/{ticker}/orderbook` | Get market orderbook (no auth required) |
| GET | `/markets/trades` | Get trades for all markets |
| GET | `/series` | Get series list |
| GET | `/series/{ticker}` | Get series information |

### Events Endpoints

| Method | Endpoint | Description |
| :-- | :-- | :-- |
| GET | `/events` | List events (supports `with_nested_markets=true`) |
| GET | `/events/{ticker}` | Get event details |

### Orders Endpoints

| Method | Endpoint | Description |
| :-- | :-- | :-- |
| GET | `/portfolio/orders` | List user orders |
| POST | `/portfolio/events/orders` | Create order (limit only, no market orders) |
| POST | `/portfolio/events/orders/{order_id}/amend` | Amend order price/quantity |
| DELETE | `/portfolio/events/orders/{order_id}` | Cancel order |
| POST | `/portfolio/orders/batch` | Batch create orders |
| DELETE | `/portfolio/orders/batch` | Batch cancel orders |

### Portfolio Endpoints

| Method | Endpoint | Description |
| :-- | :-- | :-- |
| GET | `/portfolio/balance` | Get account balance |
| GET | `/portfolio/positions` | Get your positions |
| GET | `/portfolio/fills` | Get fills |
| GET | `/portfolio/history` | Get portfolio history |

### Account Endpoints

| Method | Endpoint | Description |
| :-- | :-- | :-- |
| GET | `/account/limits` | Get account API limits and tier info |
| GET | `/account/endpoint_costs` | Get list of non-default endpoint costs |
| GET | `/account/limits/perps` | Get perps account API limits |

### Public Endpoints (No Auth Required)

These endpoints do NOT require authentication headers:

- `GET /markets` - List markets
- `GET /markets/{ticker}` - Get market details
- `GET /markets/{ticker}/orderbook` - Get orderbook
- `GET /events` - List events
- `GET /events/{ticker}` - Get event details
- `GET /series` - List series
- `GET /series/{ticker}` - Get series info

Base URL for public endpoints: `https://external-api.kalshi.com/trade-api/v2`

***

## 6. WebSocket API

### Connection URL

| Environment | URL |
| :-- | :-- |
| Production | `wss://external-api-ws.kalshi.com/trade-api/ws/v2` |
| Demo | `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` |

### Authentication

WebSocket connections require authentication during the connection handshake.

**Required Headers:**

```
KALSHI-ACCESS-KEY: your_api_key_id
KALSHI-ACCESS-SIGNATURE: request_signature
KALSHI-ACCESS-TIMESTAMP: unix_timestamp_in_milliseconds
```

**Signing for WebSocket:**

```
message = timestamp + "GET" + "/trade-api/ws/v2"
```


### Channels

| Channel | Type | Description |
| :-- | :-- | :-- |
| `ticker` | Public | Market ticker updates |
| `trade` | Public | Public trades |
| `orderbook_delta` | Private | Orderbook changes |
| `fill` | Private | User fill notifications |
| `market_positions` | Private | Market position updates |
| `market_lifecycle_v2` | Public | Market \& event lifecycle |
| `multivariate_market_lifecycle` | Public | Multivariate market lifecycle |
| `communications` | Private | Communications |
| `order_group_updates` | Private | Order group updates |

### Subscription Commands

**Subscribe to ticker updates:**

```json
{
  "id": 1,
  "cmd": "subscribe",
  "params": {
    "channels": ["ticker"]
  }
}
```

**Subscribe to orderbook for specific markets:**

```json
{
  "id": 2,
  "cmd": "subscribe",
  "params": {
    "channels": ["orderbook_delta"],
    "market_tickers": ["KXFUT24-LSV", "KXHARRIS24-LSV"]
  }
}
```


### Message Types

- `subscribed` - Subscription confirmation
- `ticker` - Ticker update (contains `yes_bid_dollars`, `yes_ask_dollars`)
- `orderbook_snapshot` - Full orderbook state
- `orderbook_delta` - Incremental orderbook change (may include `client_order_id` if you caused it)
- `error` - Error message


### Error Codes

| Code | Error | Description | User Error? |
| :-- | :-- | :-- | :-- |
| 1 | Unable to process message | Invalid JSON or type mismatch | Y |
| 2 | Params required | Missing required params | Y |
| 3 | Channels required | Subscribe must include channels | Y |
| 4 | Subscription IDs required | Unsubscribe must include sids | Y |
| 5 | Unknown command | Unsupported cmd value | Y |
| 6 | Already subscribed | Duplicate subscription | Y |
| 7 | Unknown subscription ID | Invalid subscription ID | Y |
| 8 | Unknown channel name | Unsupported channel | Y |
| 9 | Authentication required | Channel requires auth | Y |
| 10 | Channel error | Internal channel error | N |
| 11 | Invalid parameter | Malformed parameter | Y |
| 12 | Exactly one subscription ID required | Update_subscription needs one sid | Y |
| 13 | Unsupported action | Action not supported | Y |
| 14 | Market Ticker required | Market filter required | Y |
| 15 | Action required | Missing params.action | Y |
| 16 | Market not found | Market ticker doesn't exist | Y |
| 17 | Internal error | Unexpected server error | N |
| 18 | Command timeout | Server routing timeout | N |
| 19-22 | Shard factor errors | Communications shard issues | Y |
| 25 | Subscription buffer overflow | Buffer overflow during message burst | Y |

### Keep-Alive

The Python `websockets` library automatically handles WebSocket ping/pong frames. No manual heartbeat required. Other libraries may require manual ping/pong implementation.

***

## 7. Pagination

The Kalshi API uses **cursor-based pagination** for list endpoints.

### How It Works

1. Make initial request without a cursor
2. Check if response includes a `cursor` field
3. If cursor exists, make another request with `?cursor={cursor_value}`
4. Continue until cursor is `null` (no more pages)

### Pagination Parameters

- `cursor`: Token from previous response to get next page
- `limit`: Number of items per page (typically 1-100, default: 100)


### Endpoints Supporting Pagination

- `/markets` - Get Markets
- `/events` - Get Events
- `/series` - Get Series
- `/markets/trades` - Get Trades
- `/portfolio/history` - Get Portfolio History
- `/portfolio/fills` - Get Fills
- `/portfolio/orders` - Get Orders


### Example: Paginating Through Markets

```python
import requests

def get_all_markets(series_ticker):
    all_markets = []
    cursor = None
    base_url = "https://external-api.kalshi.com/trade-api/v2/markets"
    
    while True:
        url = f"{base_url}?series_ticker={series_ticker}&limit=100"
        if cursor:
            url += f"&cursor={cursor}"
        
        response = requests.get(url)
        data = response.json()
        all_markets.extend(data['markets'])
        
        cursor = data.get('cursor')
        if not cursor:
            break
    
    return all_markets
```


***

## 8. Orderbook Structure

### Getting Orderbook Data

```
GET /markets/{ticker}/orderbook
```

No authentication required.

### Response Structure

The orderbook is wrapped in an `orderbook_fp` object containing two arrays:

- `yes_dollars`: Bids for YES positions
- `no_dollars`: Bids for NO positions

Each bid is a two-element string array: `[price_dollars, count_fp]`

- `price_dollars`: Price as dollar string (e.g., `"0.4200"` = \$0.42)
- `count_fp`: Number of contracts as fixed-point string (e.g., `"13.00"` = 13 contracts)
- Arrays are sorted by price in **ascending order**
- The **highest** bid (best bid) is the **last** element in each array


### Example Response

```json
{
  "orderbook_fp": {
    "yes_dollars": [
      ["0.0100", "200.00"],
      ["0.1500", "100.00"],
      ["0.4200", "13.00"]
    ],
    "no_dollars": [
      ["0.0100", "100.00"],
      ["0.3800", "300.00"],
      ["0.5600", "17.00"]
    ]
  }
}
```


### Why Only Bids?

Kalshi's orderbook only returns bids, not asks, because of the **reciprocal relationship** in binary prediction markets:


| Action | Equivalent To | Why |
| :-- | :-- | :-- |
| YES BID at \$0.60 | NO ASK at \$0.40 | Willing to pay \$0.60 for YES = Willing to receive \$0.40 for NO |
| NO BID at \$0.30 | YES ASK at \$0.70 | Willing to pay \$0.30 for NO = Willing to receive \$0.70 for YES |

### Calculating Spreads

**YES spread:**

- Best YES bid = Highest price in `yes_dollars` array
- Best YES ask = \$1.00 - (Highest price in `no_dollars` array)
- Spread = Best YES ask - Best YES bid

**NO spread:**

- Best NO bid = Highest price in `no_dollars` array
- Best NO ask = \$1.00 - (Highest price in `yes_dollars` array)
- Spread = Best NO ask - Best NO bid


### Example Spread Calculation

```python
from decimal import Decimal

best_yes_bid = Decimal("0.4200")   # Highest YES bid (last in array)
best_yes_ask = Decimal("1.00") - Decimal("0.5600")  # $1.00 - highest NO bid = $0.44
spread = best_yes_ask - best_yes_bid  # $0.44 - $0.42 = $0.02
```


***

## 9. Order Lifecycle

### Order Types

- Kalshi only supports **limit orders** (no market orders)
- You can simulate market orders by using limit orders with aggressive pricing


### Order Parameters

```json
{
  "ticker": "KXHIGHNY-24JAN01-T60",
  "side": "bid",
  "count": "1",
  "price": "0.0100",
  "time_in_force": "good_till_canceled",
  "self_trade_prevention_type": "taker_at_cross",
  "client_order_id": "uuid-4-string"
}
```


### Order Fields

- `ticker`: Market ticker
- `side`: `"bid"` (buy) or `"ask"` (sell)
- `count`: Number of contracts (as string)
- `price`: Price in dollars (1-99 cents, as string)
- `time_in_force`: Order duration (e.g., `good_till_canceled`)
- `self_trade_prevention_type`: e.g., `taker_at_cross`
- `client_order_id`: Optional but recommended UUID for deduplication


### Client Order ID

- Optional but strongly recommended for order deduplication
- Generate a unique UUID4 for each order before submission
- Enables idempotent retries on network issues
- API rejects duplicate submissions with same `client_order_id`
- Store locally to track orders before receiving server's `order_id`


### Order Operations

| Operation | Method | Endpoint |
| :-- | :-- | :-- |
| Create Order | POST | `/portfolio/events/orders` |
| Amend Order | POST | `/portfolio/events/orders/{order_id}/amend` |
| Cancel Order | DELETE | `/portfolio/events/orders/{order_id}` |
| Batch Create | POST | `/portfolio/orders/batch` |
| Batch Cancel | DELETE | `/portfolio/orders/batch` |
| List Orders | GET | `/portfolio/orders` |

### Error Handling

| Error | Solution |
| :-- | :-- |
| 401 Unauthorized | Check API keys and signature generation |
| 400 Bad Request | Verify order parameters (price must be 1-99 cents) |
| 409 Conflict | Order with this `client_order_id` already exists |
| 429 Too Many Requests | Hit rate limit - slow down requests |


***

## 10. Code Examples

### Complete Authenticated GET Request (Python)

```python
import requests
import datetime
import base64
from urllib.parse import urlparse
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding

API_KEY_ID = 'your-api-key-id-here'
PRIVATE_KEY_PATH = 'path/to/your/kalshi-key.key'
BASE_URL = 'https://external-api.demo.kalshi.co/trade-api/v2'  # or production

def load_private_key(key_path):
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )

def create_signature(private_key, timestamp, method, path):
    path_without_query = path.split('?')[^0]
    message = f"{timestamp}{method}{path_without_query}".encode('utf-8')
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def get(private_key, api_key_id, path, base_url=BASE_URL):
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    sign_path = urlparse(base_url + path).path
    signature = create_signature(private_key, timestamp, "GET", sign_path)
    headers = {
        'KALSHI-ACCESS-KEY': api_key_id,
        'KALSHI-ACCESS-SIGNATURE': signature,
        'KALSHI-ACCESS-TIMESTAMP': timestamp
    }
    return requests.get(base_url + path, headers=headers)

# Load private key
private_key = load_private_key(PRIVATE_KEY_PATH)

# Get balance
response = get(private_key, API_KEY_ID, "/portfolio/balance")
print(f"Your balance: ${response.json()['balance'] / 100:.2f}")
```


### Complete Authenticated POST Request (Python)

```python
import uuid
from urllib.parse import urlparse

def post(private_key, api_key_id, path, data, base_url=BASE_URL):
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    sign_path = urlparse(base_url + path).path
    signature = create_signature(private_key, timestamp, "POST", sign_path)
    headers = {
        'KALSHI-ACCESS-KEY': api_key_id,
        'KALSHI-ACCESS-SIGNATURE': signature,
        'KALSHI-ACCESS-TIMESTAMP': timestamp,
        'Content-Type': 'application/json'
    }
    return requests.post(base_url + path, headers=headers, json=data)

# Find an open market
response = requests.get(
    'https://external-api.demo.kalshi.co/trade-api/v2/markets?limit=1&status=open'
)
market = response.json()['markets'][^0]

# Place a buy order
order_data = {
    "ticker": market['ticker'],
    "side": "bid",
    "count": "1",
    "price": "0.0100",
    "time_in_force": "good_till_canceled",
    "self_trade_prevention_type": "taker_at_cross",
    "client_order_id": str(uuid.uuid4())
}

response = post(private_key, API_KEY_ID, '/portfolio/events/orders', order_data)

if response.status_code == 201:
    order = response.json()
    print(f"Order ID: {order['order_id']}")
    print(f"Remaining Count: {order['remaining_count']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```


### WebSocket Connection (Python)

```python
import asyncio
import base64
import json
import time
import websockets
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

KEY_ID = "your_api_key_id"
PRIVATE_KEY_PATH = "path/to/private_key.pem"
MARKET_TICKER = "KXHARRIS24-LSV"
WS_URL = "wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2"

def sign_pss_text(private_key, text: str) -> str:
    message = text.encode('utf-8')
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def create_headers(private_key, method: str, path: str) -> dict:
    timestamp = str(int(time.time() * 1000))
    msg_string = timestamp + method + path.split('?')[^0]
    signature = sign_pss_text(private_key, msg_string)
    return {
        "Content-Type": "application/json",
        "KALSHI-ACCESS-KEY": KEY_ID,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
    }

async def orderbook_websocket():
    with open(PRIVATE_KEY_PATH, 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    
    ws_headers = create_headers(private_key, "GET", "/trade-api/ws/v2")
    
    async with websockets.connect(WS_URL, additional_headers=ws_headers) as websocket:
        print(f"Connected! Subscribing to orderbook for {MARKET_TICKER}")
        
        subscribe_msg = {
            "id": 1,
            "cmd": "subscribe",
            "params": {
                "channels": ["orderbook_delta"],
                "market_ticker": MARKET_TICKER
            }
        }
        await websocket.send(json.dumps(subscribe_msg))
        
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "subscribed":
                print(f"Subscribed: {data}")
            elif msg_type == "orderbook_snapshot":
                print(f"Orderbook snapshot: {data}")
            elif msg_type == "orderbook_delta":
                if 'client_order_id' in data.get('msg', {}):
                    print(f"Update (your order): {data}")
                else:
                    print(f"Orderbook update: {data}")
            elif msg_type == "error":
                print(f"Error: {data}")

if __name__ == "__main__":
    asyncio.run(orderbook_websocket())
```


### JavaScript Authenticated Request

```javascript
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const axios = require('axios');

function loadPrivateKeyFromFile(filePath) {
    const absolutePath = path.resolve(filePath);
    return fs.readFileSync(absolutePath, 'utf8');
}

function signPssText(privateKeyPem, text) {
    const sign = crypto.createSign('RSA-SHA256');
    sign.update(text);
    sign.end();
    const signature = sign.sign({
        key: privateKeyPem,
        padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
        saltLength: crypto.constants.RSA_PSS_SALTLEN_DIGEST,
    });
    return signature.toString('base64');
}

const currentTimeMilliseconds = Date.now();
const timestampStr = currentTimeMilliseconds.toString();
const privateKeyPem = loadPrivateKeyFromFile('path/to/your/private-key.pem');
const method = "GET";
const baseUrl = 'https://external-api.demo.kalshi.co';
const reqPath = '/trade-api/v2/portfolio/balance';
const pathWithoutQuery = reqPath.split('?')[^0];
const msgString = timestampStr + method + pathWithoutQuery;
const sig = signPssText(privateKeyPem, msgString);

const headers = {
    'KALSHI-ACCESS-KEY': 'your-api-key-id',
    'KALSHI-ACCESS-SIGNATURE': sig,
    'KALSHI-ACCESS-TIMESTAMP': timestampStr
};

axios.get(baseUrl + reqPath, { headers })
    .then(response => {
        console.log(response.data);
    })
    .catch(error => {
        console.error('Error:', error);
    });
```


***

## 11. Key Concepts

### Market Data Hierarchy

1. **Series**: Top-level category (e.g., `KXHIGHNY` for NYC highest temperature)
2. **Events**: Grouping of markets under a series
3. **Markets**: Individual tradeable contracts (e.g., yes/no on a specific outcome)

### Discovery Flow

```
Series → Events → Markets → Orderbook
```


### Binary Market Mechanics

- Markets resolve to YES or NO
- YES + NO prices always sum to \$1.00
- Bids only in orderbook (asks are implied)
- Prices range from \$0.01 to \$0.99


### Time In Force Options

- `good_till_canceled` - Order remains active until canceled
- Other time-in-force options available (check API reference for full list)


### Self-Trade Prevention

- `taker_at_cross` - Prevents self-trading by taking the taker side at cross


### Fixed-Point Migration

- Orderbook values use fixed-point strings (e.g., `"13.00"`)
- Prices use dollar strings (e.g., `"0.4200"`)
- Both are strings to support subpenny pricing and fractional contract sizes


### Demo vs Production

- Separate credentials for each environment
- Demo: `https://external-api.demo.kalshi.co/trade-api/v2`
- Production: `https://external-api.kalshi.com/trade-api/v2`
- Demo is for testing; production for real trading

***

## Additional Resources

- **Official Docs**: https://docs.kalshi.com
- **API Reference**: https://docs.kalshi.com/api-reference
- **Changelog**: https://docs.kalshi.com/changelog
- **Developer Agreement**: https://kalshi.com/developer-agreement
- **Kalshi Discord**: https://discord.gg/kalshi
- **Support**: support@kalshi.com
- **Institutional**: institutional@kalshi.com


### Specifications Available for Download

- Predictions REST: `openapi.yaml`
- Predictions WebSocket: `asyncapi.yaml`
- Perps REST: `perps_openapi.yaml`
- Perps WebSocket: `perps_asyncapi.yaml`


### FIX Protocol Support

- Common Components
- Connectivity
- Authentication \& Sessions
- Order Entry
- Order Groups
- Market Data
- RFQ
- Drop Copy Session
- Listener Sessions
- Market Settlement
- Error Handling
- Subpenny Pricing

***

*Document generated from Kalshi official documentation. Last updated: July 2026.*
'''

with open(file_path, 'w', encoding='utf-8') as f:
f.write(content)

print(f"File created: {file_path}")
print(f"File size: {os.path.getsize(file_path)} bytes")
print(f"Line count: {len(content.splitlines())}")
</think><tool_call>execute_code</arg_value><arg_value>code</arg_key><arg_value>
import os

file_path = os.path.expanduser("~/kalshi_api_reference.md")

# Verify file exists and show first/last sections

with open(file_path, 'r') as f:
content = f.read()

print(f"File: {file_path}")
print(f"Size: {os.path.getsize(file_path):,} bytes")
print(f"Lines: {len(content.splitlines()):,}")
print(f"Words: {len(content.split()):,}")
print(f"\n--- First 5 lines ---")
for line in content.splitlines()[:5]:
print(line)
print(f"\n--- Last 5 lines ---")
for line in content.splitlines()[-5:]:
print(line)
</arg_value></tool_call>
<span style="display:none">[^1][^10][^11][^12][^13][^14][^15][^2][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://docs.kalshi.com/getting_started/api_environments

[^2]: https://docs.kalshi.com/getting_started/quick_start_market_data

[^3]: https://docs.kalshi.com/welcome

[^4]: https://docs.kalshi.com/getting_started/quick_start_authenticated_requests

[^5]: https://github.com/AndrewNolte/KalshiPythonClient/blob/main/README.md

[^6]: https://docs.cobot.gg/api-reference/kalshi

[^7]: https://docs.kalshi.com/getting_started/rate_limits

[^8]: https://dev.to/zuplo/kalshi-api-the-complete-developers-guide-1fo4

[^9]: https://docs.kalshi.com/api-reference/market/get-trades

[^10]: https://docs.kalshi.com/fix/connectivity

[^11]: https://docs.kalshi.com/api-reference/market/get-series-list

[^12]: https://www.youtube.com/watch?v=yYjo1lzNoGI\&vl=en

[^13]: https://docs.kalshi.com/api-reference/account/get-account-api-limits

[^14]: https://docs.kalshi.com/getting_started/api_keys

[^15]: https://www.youtube.com/watch?v=E2mgWN4ReqQ

