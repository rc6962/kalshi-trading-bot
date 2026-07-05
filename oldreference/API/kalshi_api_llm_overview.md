# Kalshi Prediction Markets API v2 Overview for LLMs

This file consolidates core human-readable docs plus pointers to machine-readable specs, optimized for local LLM consumption.


## Machine-Readable Specs

The full REST schema is in `kalshi_openapi.yaml` and WebSocket channels in `kalshi_asyncapi.yaml`. Use these alongside this overview for tool-building and codegen.

## Source: welcome.md

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.kalshi.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Introduction

> Welcome to the Kalshi API documentation

<div className="docs-home-hero">
  <div className="docs-home-hero-bg docs-home-hero-bg-light" />

  <div className="docs-home-hero-bg docs-home-hero-bg-dark" />

  <div className="docs-home-hero-content">
    <h1 className="docs-home-hero-title">
      Welcome to Kalshi's API Documentation
    </h1>

    <p className="docs-home-hero-subtitle">
      This documentation covers the Kalshi Exchange API for real-time market data and trade execution
    </p>

    <p className="docs-home-hero-agreement">
      <span>By continuing to use or access Kalshi's API, you are agreeing to be bound to our </span><a className="docs-home-hero-link" href="https://kalshi.com/developer-agreement" target="_blank" rel="noopener noreferrer">Developer Agreement</a>
    </p>
  </div>
</div>

<div className="docs-home-content">
  <h2 className="docs-home-section-title">The APIs</h2>

  <CardGroup cols={2}>
    <Card title="Predictions APIs" icon="chart-line" href="/api-reference">
      Event-contract markets: REST, WebSocket, and FIX.
    </Card>

    <Card title="Perps APIs" icon="chart-candlestick" href="/margin">
      Perpetual futures (margin): REST, WebSocket, and FIX.
    </Card>
  </CardGroup>

  <h2 className="docs-home-section-title">Get started</h2>

  <CardGroup cols={4}>
    <Card title="Making Your First Request" icon="rocket" href="/getting_started/making_your_first_request">
      Make your first API call and start trading on Kalshi.
    </Card>

    <Card title="Demo Environment" icon="atom" href="/getting_started/demo_env">
      Build and test safely against the demo environment.
    </Card>

    <Card title="API Keys" icon="key" href="/getting_started/api_keys">
      Generate and manage your API credentials.
    </Card>

    <Card title="Kalshi Academy" icon="graduation-cap" href="https://help.kalshi.com/">
      New to prediction markets? Explore educational resources and tutorials.
    </Card>
  </CardGroup>

  <h2 className="docs-home-section-title">Reference</h2>

  <CardGroup cols={3}>
    <Card title="Rate Limits" icon="gauge" href="/getting_started/rate_limits">
      Token budgets, tiers, and bursting.
    </Card>

    <Card title="Changelog" icon="list-tree" href="/changelog">
      Stay updated with the latest API changes.
    </Card>

    <Card title="Glossary" icon="book-open" href="/getting_started/terms">
      Key terms and concepts used across the exchange.
    </Card>
  </CardGroup>

  <h2 className="docs-home-section-title">Specifications</h2>

  <CardGroup cols={4}>
    <Card title="Predictions REST" icon="file-code" href="/openapi.yaml">
      Download `openapi.yaml` for event-contract REST API integration.
    </Card>

    <Card title="Predictions WebSocket" icon="file-code" href="/asyncapi.yaml">
      Download `asyncapi.yaml` for event-contract WebSocket integration.
    </Card>

    <Card title="Perps REST" icon="file-code" href="/perps_openapi.yaml">
      Download `perps_openapi.yaml` for perpetual futures REST API integration.
    </Card>

    <Card title="Perps WebSocket" icon="file-code" href="/perps_asyncapi.yaml">
      Download `perps_asyncapi.yaml` for perpetual futures WebSocket integration.
    </Card>
  </CardGroup>
</div>


## Source: api_environments.md

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.kalshi.com/llms.txt
> Use this file to discover all available pages before exploring further.

# API Environments and Endpoints

> REST and WebSocket base URLs for production and demo

Kalshi provides separate production and demo environments. Credentials are not shared between environments, so demo API keys only work against demo endpoints and production API keys only work against production endpoints.

## REST API

Use these base URLs for the Trade API:

| Environment | Recommended base URL                               | Also supported                                  |
| ----------- | -------------------------------------------------- | ----------------------------------------------- |
| Production  | `https://external-api.kalshi.com/trade-api/v2`     | `https://api.elections.kalshi.com/trade-api/v2` |
| Demo        | `https://external-api.demo.kalshi.co/trade-api/v2` | `https://demo-api.kalshi.co/trade-api/v2`       |

The `external-api` hosts are dedicated to the external Trade API and are the recommended hosts for API traders. The existing shared hosts remain supported for compatibility with existing clients.

<Note>
  Despite the `elections` subdomain, the production Trade API provides access to all Kalshi markets, not only election-related markets.
</Note>

## WebSocket API

Use these WebSocket URLs for the Trade API:

| Environment | Recommended URL                                        | Also supported                                   |
| ----------- | ------------------------------------------------------ | ------------------------------------------------ |
| Production  | `wss://external-api-ws.kalshi.com/trade-api/ws/v2`     | `wss://api.elections.kalshi.com/trade-api/ws/v2` |
| Demo        | `wss://external-api-ws.demo.kalshi.co/trade-api/ws/v2` | `wss://demo-api.kalshi.co/trade-api/ws/v2`       |

## Request Signing

The host does not change the signature payload. Sign the full request path from the API root, without query parameters.

For example, all of these hosts use the same signed path for an order request:

```text theme={null}
/trade-api/v2/portfolio/orders
```

If the request URL is:

```text theme={null}
https://external-api.kalshi.com/trade-api/v2/portfolio/orders?limit=5
```

sign:

```text theme={null}
/trade-api/v2/portfolio/orders
```

not the hostname and not the query string.


## Source: api_keys.md

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.kalshi.com/llms.txt
> Use this file to discover all available pages before exploring further.

# API Keys

> API Key usage

<Info>
  This process is the same for the demo or production environment.
</Info>

## Generating an API Key

### Access the Account Settings Page:

Log in to your account and navigate to the "Account Settings" page. You can typically find this option by clicking on your profile picture or account icon in the top-right corner of the application.

### Generate a New API Key

In the "Profile Settings" page [https://kalshi.com/account/profile](https://kalshi.com/account/profile), locate the "API Keys" section. Click on the "Create New API Key" button. This action will generate a new API key in the RSA\_PRIVATE\_KEY format.

### Store Your API Key and Key ID:

After generating the key, you will be presented with:
• Private Key: This is your secret key in RSA\_PRIVATE\_KEY format.
• Key ID: This is a unique identifier associated with your private key.

**Important**: For security reasons, the private key will not be stored by our service, and you will not be able to retrieve it again once this page is closed. Please make sure to securely copy and save the private key immediately. The key will also be downloaded as txt file with the name provided.

## Using a API Key

Each request to Kalshi trading api will need to be signed with the private key generated above.

The following header values will need to be provided with each request:

`KALSHI-ACCESS-KEY`- the Key ID

`KALSHI-ACCESS-TIMESTAMP` - the request timestamp in ms

`KALSHI-ACCESS-SIGNATURE`- request hash signed with private key

The above signature is generated by signing a concatenation of the timestamp, the HTTP method and the path.

<Warning>
  **Important**: When signing requests, use the path **without query parameters**. For example, if your request is to `/trade-api/v2/portfolio/orders?limit=5`, sign only `/trade-api/v2/portfolio/orders` (strip the `?` and everything after it).
</Warning>

Sample code for generating the required headers is below. For end-to-end examples, see [Quick Start: Authenticated Requests](/getting_started/quick_start_authenticated_requests).

### Python

Load the private key stored in a file

```python theme={null}
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

def load_private_key_from_file(file_path):
    with open(file_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,  # or provide a password if your key is encrypted
            backend=default_backend()
        )
    return private_key
```

Sign text with private key

```python theme={null}
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

def sign_pss_text(private_key: rsa.RSAPrivateKey, text: str) -> str:
    message = text.encode('utf-8')
    try:
        signature = private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')
    except InvalidSignature as e:
        raise ValueError("RSA sign PSS failed") from e
```

Send a request to Kalshi API with signed header

```python theme={null}
import requests
import datetime

current_time = datetime.datetime.now()
timestamp = current_time.timestamp()
current_time_milliseconds = int(timestamp * 1000)
timestampt_str = str(current_time_milliseconds)

private_key = load_private_key_from_file('kalshi-key-2.key')

method = "GET"
base_url = 'https://external-api.demo.kalshi.co'
path='/trade-api/v2/portfolio/balance'

# Strip query parameters from path before signing
path_without_query = path.split('?')[0]
msg_string = timestampt_str + method + path_without_query
sig = sign_pss_text(private_key, msg_string)

headers = {
    'KALSHI-ACCESS-KEY': 'a952bcbe-ec3b-4b5b-b8f9-11dae589608c',
    'KALSHI-ACCESS-SIGNATURE': sig,
    'KALSHI-ACCESS-TIMESTAMP': timestampt_str
}

response = requests.get(base_url + path, headers=headers)

print(response.text)
```

### Javascript

Load the private key stored in a file

```javascript theme={null}
const fs = require('fs');
const path = require('path');

function loadPrivateKeyFromFile(filePath) {
    const absolutePath = path.resolve(filePath);
    const privateKeyPem = fs.readFileSync(absolutePath, 'utf8');
    return privateKeyPem;
}
```

Sign text with private key

```javascript theme={null}
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

Send a request to Kalshi API with signed header

```javascript theme={null}
const axios = require('axios');

const currentTimeMilliseconds = Date.now();
const timestampStr = currentTimeMilliseconds.toString();

const privateKeyPem = loadPrivateKeyFromFile('path/to/your/private-key.pem');

const method = "GET";
const baseUrl = 'https://external-api.demo.kalshi.co';
const path = '/trade-api/v2/portfolio/balance';

// Strip query parameters from path before signing
const pathWithoutQuery = path.split('?')[0];
const msgString = timestampStr + method + pathWithoutQuery;
const sig = signPssText(privateKeyPem, msgString);

const headers = {
    'KALSHI-ACCESS-KEY': 'your-api-key-id',
    'KALSHI-ACCESS-SIGNATURE': sig,
    'KALSHI-ACCESS-TIMESTAMP': timestampStr
};

axios.get(baseUrl + path, { headers })
    .then(response => {
        console.log(response.data);
    })
    .catch(error => {
        console.error('Error:', error);
    });
```


## Source: market_lifecycle.md

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.kalshi.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Market Lifecycle

> How markets move from creation to settlement

Markets on Kalshi follow a lifecycle from creation through trading to determination and settlement. This page describes the states a market passes through and what to expect at each stage.

## Statuses

The REST API returns these statuses on `GET /markets` and `GET /markets/{ticker}`:

| Status        | Meaning                                                                                   |
| ------------- | ----------------------------------------------------------------------------------------- |
| `initialized` | Created but not yet open for trading. Transitions to `active` when `open_time` passes.    |
| `active`      | Open for trading.                                                                         |
| `inactive`    | Temporarily deactivated by the exchange. Trading is paused but the market has not closed. |
| `closed`      | Past `close_time`. No new orders accepted. Awaiting determination.                        |
| `determined`  | Result is known. Settlement timer is running.                                             |
| `disputed`    | Result has been challenged. May be re-determined.                                         |
| `amended`     | Re-determined after a dispute. Settlement timer restarts.                                 |
| `finalized`   | Settlement complete. Positions have been paid out. Terminal state.                        |

When filtering with `GET /markets?status=`, the values map as follows:

| Filter value | Matches                                                  |
| ------------ | -------------------------------------------------------- |
| `unopened`   | `initialized` (before `open_time`)                       |
| `open`       | `active`                                                 |
| `paused`     | `inactive`                                               |
| `closed`     | Any market past `close_time` that is not yet `finalized` |
| `settled`    | `finalized`                                              |

## Transitions

Some transitions are implicit (time-based), others are explicit (event-driven).

**Implicit (no WebSocket event):**

* `initialized` → `active`: when `open_time` passes. There is no `activated` WebSocket event for this transition.
* `active` / `inactive` → `closed`: when `close_time` passes.

**Explicit (WebSocket event emitted):**

* `active` → `inactive`: exchange deactivates the market. Event: `deactivated`.
* `inactive` → `active`: exchange reactivates a paused market. Event: `activated`. All resting orders are cancelled on this reactivation.
* `closed` → reopened `active`: `close_time` is moved into the future. Events: `close_date_updated`, then `activated`.
* Close time updated: `close_time` changes. Event: `close_date_updated`. This can happen when a market is closed ahead of its scheduled close time, including before determination.
* `closed` → `determined`: result is set. Event: `determined`.
* `determined` / `amended` → `finalized`: positions paid out. Event: `settled`.

## Time fields

Markets have several time fields:

| Field                      | Meaning                                                                                                                                                   |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `open_time`                | When the market opens for trading.                                                                                                                        |
| `close_time`               | When trading stops. May be moved earlier if `can_close_early` is true.                                                                                    |
| `expected_expiration_time` | When the outcome is expected to be known.                                                                                                                 |
| `latest_expiration_time`   | Latest possible expiration time.                                                                                                                          |
| `expiration_time`          | Deprecated legacy field. Prefer `latest_expiration_time` for the legacy expiry semantics; use `expected_expiration_time` if you want the forecasted time. |

## Determination and settlement

After a market closes and the outcome is known, the market is determined and `result` is set to `yes`, `no`, or `scalar`.

A settlement timer then runs for `settlement_timer_seconds`, which is visible in the REST response. During this window the market remains at `determined` and the result may be disputed.

Once settlement completes, positions are paid out. In REST, settled markets end up at `finalized` rather than a separate `settled` status, and `settlement_ts` is populated.

## Orders after close

Once `close_time` passes, all order operations, including cancellations, are rejected with `MARKET_INACTIVE`. Resting orders are cancelled shortly after close, and cancellation updates are published on the usual user channels.

## WebSocket

Market lifecycle events are delivered on two channels:

| Channel                         | Markets covered                   | Event types                                                                                              |
| ------------------------------- | --------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `market_lifecycle_v2`           | All markets except MVE (`KXMVE*`) | `created`, `activated`, `deactivated`, `close_date_updated`, `determined`, `settled`, `metadata_updated` |
| `multivariate_market_lifecycle` | MVE markets only (`KXMVE*`)       | `created`, `activated`, `deactivated`, `close_date_updated`, `determined`, `settled`                     |

Both channels also emit `event_lifecycle` messages when new events are created.

The `market_lifecycle_v2` channel additionally emits `event_fee_update` messages when an event-level fee override is set or cleared.

The WebSocket `settled` event corresponds to settlement being processed; in REST, settled markets end up at `finalized`.

## FAQ

<AccordionGroup>
  <Accordion title="Why can `expected_expiration_time` be before `close_time`?">
    `expected_expiration_time` is the time the event is likely to resolve (for a sports game, typically a few hours after the scheduled start). `close_time` is when the market automatically closes for trading, and may be set well into the future to allow for rescheduling. That means `expected_expiration_time` can be earlier than `close_time`.
  </Accordion>

  <Accordion title="Why might `GET /markets/{ticker}` return `404` right after a `created` event?">
    The market may not be queryable immediately after a `created` event. Retry with backoff.
  </Accordion>

  <Accordion title="Do event responses include a top-level `status` field?">
    `GET /events` supports a `status` filter with values `unopened`, `open`, `closed`, and `settled`. The filter matches on child market statuses, not an event-level status; an event appears in results if **any** of its child markets has a matching status. For example, an event with four open markets and one settled market matches both `status=open` and `status=settled`. Use `with_nested_markets=true` if you need individual market statuses.
  </Accordion>
</AccordionGroup>


## Source: orderbook_responses.md

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.kalshi.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Orderbook Responses

> Understanding Kalshi orderbook structure and binary prediction market mechanics

## Getting Orderbook Data

The [Get Market Orderbook](/api-reference/market/get-market-order-book) endpoint returns the current state of bids for a specific market.

### Request Format

```
GET /markets/{ticker}/orderbook
```

No authentication is required for this endpoint.

### Example Request

<CodeGroup>
  ```python Python theme={null}
  import requests

  # Get orderbook for a specific market
  market_ticker = "KXHIGHNY-24JAN01-T60"
  url = f"https://external-api.kalshi.com/trade-api/v2/markets/{market_ticker}/orderbook"

  response = requests.get(url)
  orderbook_data = response.json()
  ```

  ```javascript JavaScript theme={null}
  // Get orderbook for a specific market
  const marketTicker = "KXHIGHNY-24JAN01-T60";
  const url = `https://external-api.kalshi.com/trade-api/v2/markets/${marketTicker}/orderbook`;

  fetch(url)
    .then(response => response.json())
    .then(data => console.log(data));
  ```

  ```curl cURL theme={null}
  curl -X GET "https://external-api.kalshi.com/trade-api/v2/markets/KXHIGHNY-24JAN01-T60/orderbook"
  ```
</CodeGroup>

## Response Structure

The orderbook response is wrapped in an `orderbook_fp` object containing two arrays of bids: `yes_dollars` for YES positions and `no_dollars` for NO positions. Each bid is a two-element string array: `[price_dollars, count_fp]`.

* **`price_dollars`**: Price as a dollar string (e.g., `"0.4200"` = \$0.42)
* **`count_fp`**: Number of contracts as a fixed-point string (e.g., `"13.00"` = 13 contracts)

Both values are strings to support subpenny pricing and fractional contract sizes. See [Fixed-Point Migration](/getting_started/fixed_point_migration) for details.

### Example Response

```json theme={null}
{
  "orderbook_fp": {
    "yes_dollars": [
      ["0.0100", "200.00"],
      ["0.1500", "100.00"],
      ["0.2000", "50.00"],
      ["0.2500", "20.00"],
      ["0.3000", "11.00"],
      ["0.3100", "10.00"],
      ["0.3200", "10.00"],
      ["0.3300", "11.00"],
      ["0.3400", "9.00"],
      ["0.3500", "11.00"],
      ["0.4100", "10.00"],
      ["0.4200", "13.00"]
    ],
    "no_dollars": [
      ["0.0100", "100.00"],
      ["0.1600", "3.00"],
      ["0.2500", "50.00"],
      ["0.2800", "19.00"],
      ["0.3600", "5.00"],
      ["0.3700", "50.00"],
      ["0.3800", "300.00"],
      ["0.4400", "29.00"],
      ["0.4500", "20.00"],
      ["0.5600", "17.00"]
    ]
  }
}
```

### Understanding the Arrays

* **First element**: Price in dollars as a string (e.g., `"0.4200"`)
* **Second element**: Number of contracts as a fixed-point string (e.g., `"13.00"`)
* Arrays are sorted by price in **ascending order**
* The **highest** bid (best bid) is the **last** element in each array

## Why Only Bids?

<Info>
  **Important**: Kalshi's orderbook only returns bids, not asks. This is because in binary prediction markets, there's a reciprocal relationship between YES and NO positions.
</Info>

In binary prediction markets, every position has a complementary opposite:

* A **YES BID** at price X is equivalent to a **NO ASK** at price (\$1.00 - X)
* A **NO BID** at price Y is equivalent to a **YES ASK** at price (\$1.00 - Y)

### The Reciprocal Relationship

Since binary markets must sum to \$1.00, these relationships always hold:

| Action            | Equivalent To     | Why                                                                |
| ----------------- | ----------------- | ------------------------------------------------------------------ |
| YES BID at \$0.60 | NO ASK at \$0.40  | Willing to pay $0.60 for YES = Willing to receive $0.40 to take NO |
| NO BID at \$0.30  | YES ASK at \$0.70 | Willing to pay $0.30 for NO = Willing to receive $0.70 to take YES |

This reciprocal nature means that by showing only bids, the orderbook provides complete market information while avoiding redundancy.

## Calculating Spreads

To find the bid-ask spread for a market:

1. **YES spread**:
   * Best YES bid: Highest price in the `yes_dollars` array
   * Best YES ask: \$1.00 - (Highest price in the `no_dollars` array)
   * Spread = Best YES ask - Best YES bid

2. **NO spread**:
   * Best NO bid: Highest price in the `no_dollars` array
   * Best NO ask: \$1.00 - (Highest price in the `yes_dollars` array)
   * Spread = Best NO ask - Best NO bid

### Example Calculation

```python theme={null}
from decimal import Decimal

# Using the example orderbook above
best_yes_bid = Decimal("0.4200")  # Highest YES bid (last in array)
best_yes_ask = Decimal("1.00") - Decimal("0.5600")  # $1.00 - highest NO bid = $0.44

spread = best_yes_ask - best_yes_bid  # $0.44 - $0.42 = $0.02

# The spread is $0.02
# You can buy YES at $0.44 (implied ask) and sell at $0.42 (bid)
```

## Working with Orderbook Data

### Display Best Prices

<CodeGroup>
  ```python Python theme={null}
  from decimal import Decimal

  def display_best_prices(orderbook_data):
      """Display the best bid prices and implied asks"""
      ob = orderbook_data['orderbook_fp']

      # Best bids (if any exist)
      if ob.get('yes_dollars'):
          best_yes_bid = ob['yes_dollars'][-1][0]  # Last element is highest
          print(f"Best YES Bid: ${best_yes_bid}")

      if ob.get('no_dollars'):
          best_no_bid = ob['no_dollars'][-1][0]  # Last element is highest
          best_yes_ask = Decimal("1.00") - Decimal(best_no_bid)
          print(f"Best YES Ask: ${best_yes_ask} (implied from NO bid)")

      print()

      if ob.get('no_dollars'):
          best_no_bid = ob['no_dollars'][-1][0]  # Last element is highest
          print(f"Best NO Bid: ${best_no_bid}")

      if ob.get('yes_dollars'):
          best_yes_bid = ob['yes_dollars'][-1][0]  # Last element is highest
          best_no_ask = Decimal("1.00") - Decimal(best_yes_bid)
          print(f"Best NO Ask: ${best_no_ask} (implied from YES bid)")
  ```

  ```javascript JavaScript theme={null}
  function displayBestPrices(orderbookData) {
    const ob = orderbookData.orderbook_fp;

    // Best bids (if any exist)
    if (ob.yes_dollars && ob.yes_dollars.length > 0) {
      const bestYesBid = ob.yes_dollars[ob.yes_dollars.length - 1][0];
      console.log(`Best YES Bid: $${bestYesBid}`);
    }

    if (ob.no_dollars && ob.no_dollars.length > 0) {
      const bestNoBid = ob.no_dollars[ob.no_dollars.length - 1][0];
      const bestYesAsk = (1 - parseFloat(bestNoBid)).toFixed(4);
      console.log(`Best YES Ask: $${bestYesAsk} (implied from NO bid)`);
    }

    console.log();

    if (ob.no_dollars && ob.no_dollars.length > 0) {
      const bestNoBid = ob.no_dollars[ob.no_dollars.length - 1][0];
      console.log(`Best NO Bid: $${bestNoBid}`);
    }

    if (ob.yes_dollars && ob.yes_dollars.length > 0) {
      const bestYesBid = ob.yes_dollars[ob.yes_dollars.length - 1][0];
      const bestNoAsk = (1 - parseFloat(bestYesBid)).toFixed(4);
      console.log(`Best NO Ask: $${bestNoAsk} (implied from YES bid)`);
    }
  }
  ```
</CodeGroup>

### Calculate Market Depth

```python theme={null}
from decimal import Decimal

def calculate_depth(orderbook_data, depth_dollars="0.05"):
    """Calculate total volume within X dollars of best bid"""
    ob = orderbook_data['orderbook_fp']
    depth = Decimal(depth_dollars)

    yes_depth = Decimal("0")
    no_depth = Decimal("0")

    # YES side depth (iterate backwards from best bid)
    if ob.get('yes_dollars'):
        best_yes = Decimal(ob['yes_dollars'][-1][0])
        for price_str, count_str in reversed(ob['yes_dollars']):
            if best_yes - Decimal(price_str) <= depth:
                yes_depth += Decimal(count_str)
            else:
                break

    # NO side depth (iterate backwards from best bid)
    if ob.get('no_dollars'):
        best_no = Decimal(ob['no_dollars'][-1][0])
        for price_str, count_str in reversed(ob['no_dollars']):
            if best_no - Decimal(price_str) <= depth:
                no_depth += Decimal(count_str)
            else:
                break

    return {"yes_depth": str(yes_depth), "no_depth": str(no_depth)}
```

## Next Steps

* Learn about [making authenticated requests](/getting_started/api_keys) to place orders
* Explore [WebSocket connections](/websockets) for real-time orderbook updates
* Read about [market mechanics](https://kalshi.com/learn) on the Kalshi website


## Source: quick_start_market_data.md

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.kalshi.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Quick Start: Market Data

> Learn how to access real-time market data without authentication

This guide will walk you through accessing Kalshi's public market data endpoints without authentication. You'll learn how to retrieve series information, events, markets, and orderbook data for the popular "Who will have a higher net approval" market.

## Making Unauthenticated Requests

Kalshi provides several public endpoints that don't require API keys. These endpoints allow you to access market data directly from our production servers at `https://external-api.kalshi.com/trade-api/v2`.

<Info>
  **Note about the API URL**: Despite the "elections" subdomain, the production Trade API provides access to ALL Kalshi markets - not just election-related ones. This includes markets on economics, climate, technology, entertainment, and more.
</Info>

<Info>
  No authentication headers are required for the endpoints in this guide. You can start making requests immediately!
</Info>

## Step 1: Get Series Information

Let's start by fetching information about the KXHIGHNY series ([Highest temperature in NYC today?](https://kalshi.com/markets/kxhighny/highest-temperature-in-nyc)). This series tracks the highest temperature recorded in Central Park, New York on a given day. We'll use the [Get Series](/api-reference/market/get-series) endpoint.

<CodeGroup>
  ```python Python theme={null}
  import requests

  # Get series information for KXHIGHNY
  url = "https://external-api.kalshi.com/trade-api/v2/series/KXHIGHNY"
  response = requests.get(url)
  series_data = response.json()

  print(f"Series Title: {series_data['series']['title']}")
  print(f"Frequency: {series_data['series']['frequency']}")
  print(f"Category: {series_data['series']['category']}")
  ```

  ```javascript JavaScript theme={null}
  // Get series information for KXHIGHNY
  fetch('https://external-api.kalshi.com/trade-api/v2/series/KXHIGHNY')
    .then(response => response.json())
    .then(data => {
      console.log(`Series Title: ${data.series.title}`);
      console.log(`Frequency: ${data.series.frequency}`);
      console.log(`Category: ${data.series.category}`);
    });
  ```

  ```curl cURL theme={null}
  curl -X GET "https://external-api.kalshi.com/trade-api/v2/series/KXHIGHNY"
  ```
</CodeGroup>

## Step 2: Get Today's Events and Markets

Now that we have the series information, let's get the markets for this series. We'll use the [Get Markets](/api-reference/market/get-markets) endpoint with the series ticker filter to find all active markets. If there are no open markets today, remove `status=open` or use `status=all` to see the full series history.

<CodeGroup>
  ```python Python theme={null}
  # Get all open markets for the KXHIGHNY series
  markets_url = f"https://external-api.kalshi.com/trade-api/v2/markets?series_ticker=KXHIGHNY&status=open"
  markets_response = requests.get(markets_url)
  markets_data = markets_response.json()

  print(f"\nActive markets in KXHIGHNY series:")
  for market in markets_data['markets']:
      print(f"- {market['ticker']}: {market['title']}")
      print(f"  Event: {market['event_ticker']}")
      print(f"  Yes Price: ${market['yes_bid_dollars']} | Volume: {market['volume_fp']}")
      print()

  # Get details for a specific event if you have its ticker
  if markets_data['markets']:
      # Let's get details for the first market's event
      event_ticker = markets_data['markets'][0]['event_ticker']
      event_url = f"https://external-api.kalshi.com/trade-api/v2/events/{event_ticker}"
      event_response = requests.get(event_url)
      event_data = event_response.json()

      print(f"Event Details:")
      print(f"Title: {event_data['event']['title']}")
      print(f"Category: {event_data['event']['category']}")
  ```

  ```javascript JavaScript theme={null}
  // Get markets for the KXHIGHNY series
  async function getSeriesMarkets() {
    // Get all open markets for this series
    const marketsResponse = await fetch('https://external-api.kalshi.com/trade-api/v2/markets?series_ticker=KXHIGHNY&status=open');
    const marketsData = await marketsResponse.json();

    console.log('\nActive markets in KXHIGHNY series:');
    marketsData.markets.forEach(market => {
      console.log(`- ${market.ticker}: ${market.title}`);
      console.log(`  Event: ${market.event_ticker}`);
      console.log(`  Yes Price: $${market.yes_bid_dollars} | Volume: ${market.volume_fp}`);
      console.log();
    });

    // Get details for a specific event if markets exist
    if (marketsData.markets.length > 0) {
      const eventTicker = marketsData.markets[0].event_ticker;
      const eventResponse = await fetch(`https://external-api.kalshi.com/trade-api/v2/events/${eventTicker}`);
      const eventData = await eventResponse.json();

      console.log('Event Details:');
      console.log(`Title: ${eventData.event.title}`);
      console.log(`Category: ${eventData.event.category}`);
    }
  }

  getSeriesMarkets();
  ```
</CodeGroup>

<Info>
  You can view these markets in the Kalshi UI at: [https://kalshi.com/markets/kxhighny](https://kalshi.com/markets/kxhighny)
</Info>

## Step 3: Get Orderbook Data

Now let's fetch the orderbook for a specific market to see the current bids and asks using the [Get Market Orderbook](/api-reference/market/get-market-order-book) endpoint. This snippet assumes you still have the `markets_data` from the previous step. If `markets_data['markets']` is empty, pick a market from a different series or remove the `status=open` filter.

<CodeGroup>
  ```python Python theme={null}
  # Get orderbook for a specific market
  # Replace with an actual market ticker from the markets list
  if not markets_data['markets']:
      raise ValueError("No open markets found. Try removing status=open or choose another series.")

  market_ticker = markets_data['markets'][0]['ticker']
  orderbook_url = f"https://external-api.kalshi.com/trade-api/v2/markets/{market_ticker}/orderbook"

  orderbook_response = requests.get(orderbook_url)
  orderbook_data = orderbook_response.json()

  print(f"\nOrderbook for {market_ticker}:")
  print("YES BIDS:")
  for price_dollars, count_fp in orderbook_data['orderbook_fp']['yes_dollars'][:5]:  # Show top 5
      print(f"  Price: ${price_dollars}, Quantity: {count_fp}")

  print("\nNO BIDS:")
  for price_dollars, count_fp in orderbook_data['orderbook_fp']['no_dollars'][:5]:  # Show top 5
      print(f"  Price: ${price_dollars}, Quantity: {count_fp}")
  ```

  ```javascript JavaScript theme={null}
  // Get orderbook data
  async function getOrderbook(marketTicker) {
    const response = await fetch(`https://external-api.kalshi.com/trade-api/v2/markets/${marketTicker}/orderbook`);
    const data = await response.json();

    console.log(`\nOrderbook for ${marketTicker}:`);
    console.log('YES BIDS:');
    data.orderbook_fp.yes_dollars.slice(0, 5).forEach(([priceDollars, countFp]) => {
      console.log(`  Price: $${priceDollars}, Quantity: ${countFp}`);
    });

    console.log('\nNO BIDS:');
    data.orderbook_fp.no_dollars.slice(0, 5).forEach(([priceDollars, countFp]) => {
      console.log(`  Price: $${priceDollars}, Quantity: ${countFp}`);
    });
  }
  ```
</CodeGroup>

## Working with Large Datasets

The Kalshi API uses cursor-based pagination to handle large datasets efficiently. To learn more about navigating through paginated responses, see our [Understanding Pagination](/getting_started/pagination) guide.

## Understanding Orderbook Responses

Kalshi's orderbook structure is unique due to the nature of binary prediction markets. The API only returns bids (not asks) because of the reciprocal relationship between YES and NO positions. To learn more about orderbook responses and why they work this way, see our [Orderbook Responses](/getting_started/orderbook_responses) guide.

## Next Steps

Now that you understand how to access market data without authentication, you can:

1. Explore other public series and events
2. Build real-time market monitoring tools
3. Create market analysis dashboards
4. Set up a WebSocket connection for live updates (requires authentication)

For authenticated endpoints that allow trading and portfolio management, check out our [API Keys guide](/getting_started/api_keys).


## Source: quick_start_create_order.md

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.kalshi.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Quick Start: Create your first order

> Learn how to find markets, place orders, check status, and cancel orders on Kalshi

This guide will walk you through the complete lifecycle of placing and managing orders on Kalshi.

## Prerequisites

Before you begin, you'll need:

* A Kalshi account with API access configured
* Python with the `requests` and `cryptography` libraries installed
* Your authentication functions set up (see our [authentication guide](/getting_started/quick_start_authenticated_requests))

<Info>
  This guide assumes you have the authentication code from our authentication guide, including the `get()` function for making authenticated requests.
</Info>

## Step 1: Find an Open Market

First, let's find an open market to trade on.

```python theme={null}
# Get the first open market (no auth required for public market data)
response = requests.get('https://external-api.demo.kalshi.co/trade-api/v2/markets?limit=1&status=open')
market = response.json()['markets'][0]

print(f"Selected market: {market['ticker']}")
print(f"Title: {market['title']}")
```

## Step 2: Place a Buy Order

Now let's place an order to buy 1 YES contract for 1 cent (limit order). We'll use a `client_order_id` to deduplicate orders - this allows you to identify duplicate orders before receiving the server-generated `order_id` in the response.

```python theme={null}
import uuid
from urllib.parse import urlparse

def post(private_key, api_key_id, path, data, base_url=BASE_URL):
    """Make an authenticated POST request to the Kalshi API."""
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    # Signing requires the full URL path from root (e.g. /trade-api/v2/portfolio/events/orders)
    sign_path = urlparse(base_url + path).path
    signature = create_signature(private_key, timestamp, "POST", sign_path)

    headers = {
        'KALSHI-ACCESS-KEY': api_key_id,
        'KALSHI-ACCESS-SIGNATURE': signature,
        'KALSHI-ACCESS-TIMESTAMP': timestamp,
        'Content-Type': 'application/json'
    }

    return requests.post(base_url + path, headers=headers, json=data)

# Place a buy order for 1 YES contract at 1 cent
order_data = {
    "ticker": market['ticker'],
    "side": "bid",
    "count": "1",
    "price": "0.0100",
    "time_in_force": "good_till_canceled",
    "self_trade_prevention_type": "taker_at_cross",
    "client_order_id": str(uuid.uuid4())  # Unique ID for deduplication
}

response = post(private_key, API_KEY_ID, '/portfolio/events/orders', order_data)

if response.status_code == 201:
    order = response.json()
    print(f"Order placed successfully!")
    print(f"Order ID: {order['order_id']}")
    print(f"Client Order ID: {order_data['client_order_id']}")
    print(f"Remaining Count: {order['remaining_count']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

## Complete Example Script

Here's a complete script that creates your first order:

```python theme={null}
import requests
import uuid
from urllib.parse import urlparse
# Assumes you have the authentication code from the prerequisites

# Add POST function to your existing auth code
def post(private_key, api_key_id, path, data, base_url=BASE_URL):
    """Make an authenticated POST request to the Kalshi API."""
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    # Signing requires the full URL path from root (e.g. /trade-api/v2/portfolio/events/orders)
    sign_path = urlparse(base_url + path).path
    signature = create_signature(private_key, timestamp, "POST", sign_path)

    headers = {
        'KALSHI-ACCESS-KEY': api_key_id,
        'KALSHI-ACCESS-SIGNATURE': signature,
        'KALSHI-ACCESS-TIMESTAMP': timestamp,
        'Content-Type': 'application/json'
    }

    return requests.post(base_url + path, headers=headers, json=data)

# Step 1: Find an open market
print("Finding an open market...")
response = requests.get('https://external-api.demo.kalshi.co/trade-api/v2/markets?limit=1&status=open')
market = response.json()['markets'][0]
print(f"Selected: {market['ticker']} - {market['title']}")

# Step 2: Place a buy order
print("\nPlacing order...")
client_order_id = str(uuid.uuid4())
order_data = {
    "ticker": market['ticker'],
    "side": "bid",
    "count": "1",
    "price": "0.0100",
    "time_in_force": "good_till_canceled",
    "self_trade_prevention_type": "taker_at_cross",
    "client_order_id": client_order_id
}

response = post(private_key, API_KEY_ID, '/portfolio/events/orders', order_data)

if response.status_code == 201:
    order = response.json()
    print(f"Order placed successfully!")
    print(f"Order ID: {order['order_id']}")
    print(f"Client Order ID: {client_order_id}")
    print(f"Remaining Count: {order['remaining_count']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

## Important Notes

### Client Order ID

The `client_order_id` field is optional, but strongly recommended for order deduplication:

* Generate a unique ID (like UUID4) for each order before submission when you want idempotent retries
* If network issues occur, you can resubmit with the same `client_order_id`
* The API will reject duplicate submissions with the same `client_order_id`, preventing accidental double orders
* Store this ID locally to track orders before receiving the server's `order_id`

### Error Handling

Common errors and how to handle them:

* `401 Unauthorized`: Check your API keys and signature generation
* `400 Bad Request`: Verify your order parameters (price must be 1-99 cents)
* `409 Conflict`: Order with this `client_order_id` already exists
* `429 Too Many Requests`: You've hit the rate limit - slow down your requests

## Next Steps

Now that you've created your first order, you can:

* Store the returned `order_id` and `client_order_id` for local tracking
* Amend your order price or quantity using POST `/portfolio/events/orders/{order_id}/amend`
* Cancel orders using DELETE `/portfolio/events/orders/{order_id}`
* Implement WebSocket connections for real-time updates
* Build automated trading strategies

For more information, check out:

* [API Reference Documentation](https://docs.kalshi.com/api-reference)
* [Kalshi Discord Community](https://discord.gg/kalshi)


## Source: rate_limits.md

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.kalshi.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Rate Limits and Tiers

> Token costs, tier budgets, and burst capacity for the Kalshi API

## Token-based limits

Every authenticated request costs **tokens**. Your tier sets your **budget**: the rate, in tokens per second, at which your balance refills. Your sustained rate for an endpoint is `budget ÷ cost`.

Most requests cost the default of **10 tokens**. For endpoints that cost more or less, [`GET /account/endpoint_costs`](/api-reference/account/list-non-default-endpoint-costs) is the authoritative list of non-default costs currently in effect.

## Read and Write buckets

You have two independent token budgets:

| Bucket    | Covers                                                                                                |
| --------- | ----------------------------------------------------------------------------------------------------- |
| **Read**  | `GET` endpoints and anything not routed to Write.                                                     |
| **Write** | Order placement, amends, cancels, order groups, the RFQ quote flow, and block trade proposal accepts. |

The split is by operation type, not by protocol. REST and FIX requests drain the same buckets.

## Bucket capacity and bursting

Each budget is a token bucket. The bucket refills continuously at your per-second budget, up to its capacity, and a request is allowed whenever the bucket holds enough tokens to cover its cost. There are no fixed windows and no per-second resets.

Basic and Advanced Predictions Read buckets, and Write buckets above the Basic tier, hold up to **two seconds of budget**. When you spend less than your budget, unspent tokens accumulate, and after two quiet seconds the bucket is full. You can then spend up to **twice your per-second budget in a single burst** before throttling back to the refill rate. This favors event-driven clients that sit idle most of the time and place a block of orders when the market moves.

Predictions Read buckets above Advanced, Perps Read buckets, and Basic-tier Write buckets hold one second of budget. You can spend a full second's budget at once, but idle time banks nothing beyond that.

### Example

A Premier Write bucket refills at 1,000 tokens per second and holds up to 2,000. At the default cost of 10 tokens per order, it sustains 100 orders per second.

| Time      | Requests              | Bucket (capacity 2,000)                |
| --------- | --------------------- | -------------------------------------- |
| 2 s idle  | none                  | fills to 2,000                         |
| 0 s       | 200 orders at once    | all accepted; 2,000 drops to 0         |
| 0 to 1 s  | none                  | refills to 1,000                       |
| after 1 s | 100 orders per second | holds near 1,000; spend matches refill |

## When you hit the limit

A rate-limited request returns `429 Too Many Requests` with the body:

```json theme={null}
{"error": "too many requests"}
```

429 responses do not currently include `Retry-After` or `X-RateLimit-*` headers. There is no penalty or cooldown. The bucket keeps refilling, and your next request succeeds once the balance covers its cost. At a 1,000 tokens-per-second refill, a 10-token order is covered again 10 ms after a 429. Apply exponential backoff on 429.

## Batch endpoints don't save tokens

A batch request costs the same as making each call individually. Every item in the batch is billed separately:

* [Batch Create Orders](/api-reference/orders/batch-create-orders-v2): submitting 25 orders costs `25 × 10 = 250` tokens.
* [Batch Cancel Orders](/api-reference/orders/batch-cancel-orders-v2): cancelling 25 orders costs `25 × 2 = 50` tokens.

The whole batch must fit in the bucket at once. A 25-order create batch needs 250 tokens available when it arrives, or the entire batch is rejected.

## Perps limits use separate buckets

The Perps API uses the same bucket mechanics, including the two-second Write bucket above Basic, but perps traffic is metered in its own Read and Write buckets. Perps calls do not draw down your event-contract budgets, and event-contract calls do not draw down your perps budgets. In effect you have up to four independent buckets: event-contract Read, event-contract Write, perps Read, and perps Write.

Check your perps tier and limits with [`GET /account/limits/perps`](/margin-rest/account/get-perps-account-api-limits), the perps counterpart of [`GET /account/limits`](/api-reference/account/get-account-api-limits).

See the [Perps API](/margin) overview for the full perps surface.

## Tiers and budgets

Per-second token budgets in each event-contract bucket:

<div style={{width: '100%', overflowX: 'auto'}}>
  <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '1rem'}}>
    <thead>
      <tr style={{backgroundColor: 'rgba(255, 255, 255, 0.05)', borderBottom: '2px solid rgba(255, 255, 255, 0.1)'}}>
        <th style={{padding: '1rem 1.5rem', textAlign: 'left', fontWeight: '600'}}>Tier</th>
        <th style={{padding: '1rem 1.5rem', textAlign: 'right', fontWeight: '600'}}>Read budget</th>
        <th style={{padding: '1rem 1.5rem', textAlign: 'right', fontWeight: '600'}}>Write budget</th>
      </tr>
    </thead>

    <tbody>
      <tr><td style={{padding: '0.9rem 1.5rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>Basic</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>200</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>100</td></tr>
      <tr style={{backgroundColor: 'rgba(255, 255, 255, 0.02)'}}><td style={{padding: '0.9rem 1.5rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>Advanced</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>300</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>300</td></tr>
      <tr><td style={{padding: '0.9rem 1.5rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>Expert</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>600</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>600</td></tr>
      <tr style={{backgroundColor: 'rgba(255, 255, 255, 0.02)'}}><td style={{padding: '0.9rem 1.5rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>Premier</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>1,000</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>1,000</td></tr>
      <tr><td style={{padding: '0.9rem 1.5rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>Paragon</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>2,000</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>2,000</td></tr>
      <tr style={{backgroundColor: 'rgba(255, 255, 255, 0.02)'}}><td style={{padding: '0.9rem 1.5rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>Prime</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>4,000</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right', borderBottom: '1px solid rgba(255, 255, 255, 0.1)'}}>4,000</td></tr>
      <tr><td style={{padding: '0.9rem 1.5rem'}}>Prestige</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right'}}>6,000</td><td style={{padding: '0.9rem 1.5rem', textAlign: 'right'}}>8,000</td></tr>
    </tbody>
  </table>
</div>

Write bucket capacity is twice the per-second budget above the Basic tier.

## Tier qualification

* **Basic**: complete account signup.
* **Advanced**: call the [Upgrade Account API Usage Level endpoint](/api-reference/account/upgrade-account-api-usage-level).
* **Expert, Premier, Paragon, Prime, and Prestige**: earned automatically from your trading volume (see [Earning higher tiers](#earning-higher-tiers-by-volume) below), or assigned by Kalshi.

<Info>
  Kalshi may, at its discretion, adjust your tier at any time, including downgrading you from higher tiers following prolonged inactivity. Members may request an upgrade by contacting support with a description of their use case.
</Info>

## Earning higher tiers by volume

Once a day, Kalshi reviews your trading volume and grants Expert, Premier, Paragon, Prime, or Prestige if you qualify. Your **volume share** is your trailing 30-day volume (counting both sides of every trade you are part of, as maker and as taker) divided by twice the previous calendar month's total exchange volume:

`volume share = your trailing 30-day volume ÷ (previous month's exchange volume × 2)`

A qualifying review grants the tier for **30 days**, and each daily review renews the window while you keep qualifying. Each tier has a higher **Earn** threshold to gain it and a lower **Keep** threshold to hold it, so a brief dip does not cost you the tier:

| Tier     | Earn   | Keep  |
| -------- | ------ | ----- |
| Expert   | 0.075% | 0.05% |
| Premier  | 0.125% | 0.10% |
| Paragon  | 0.25%  | 0.20% |
| Prime    | 0.50%  | 0.40% |
| Prestige | 1.00%  | 0.80% |

If your volume falls below the **Keep** threshold, the tier does not drop immediately. It lapses when your current 30-day grant runs out.

## Your grants

Your tier is the highest level among your active **grants**. Each grant raises you to a level on one lane, `event_contract` (predictions) or `margined` (perps), until it expires, and records its source:

* **`volume`**: earned automatically from your trading volume.
* **`manual`**: assigned by Kalshi.

Fetch your grants from [`GET /account/limits`](/api-reference/account/get-account-api-limits), returned alongside your current `usage_tier`:

```json theme={null}
{
  "usage_tier": "premier",
  "read":  { "refill_rate": 1000, "bucket_capacity": 1000 },
  "write": { "refill_rate": 1000, "bucket_capacity": 2000 },
  "grants": [
    { "exchange_instance": "event_contract", "level": "premier", "expires_ts": 1751558400, "source": "volume" },
    { "exchange_instance": "event_contract", "level": "advanced", "source": "manual" }
  ]
}
```

A grant with no `expires_ts` is permanent. You keep your best grant at each level: a longer-lived manual grant is never shortened by a volume grant, and if you qualify by volume while holding a manual grant near expiry, the grant is extended to a fresh 30 days.


## Source: historical_data.md

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.kalshi.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Historical Data

> Accessing historical exchange data via the Kalshi API.

## Overview

As trading activity on Kalshi grows, so does the volume of settled markets, completed trades, and fulfilled orders. To keep the live API fast and responsive, Kalshi partitions exchange data into **live** and **historical** tiers.

Live endpoints return current and recent data: open and recently closed markets, active orders, and recent fills. Older data that is no longer actively referenced is made available through a separate set of historical endpoints.

This separation means that if you query for data that is older than the cutoff (described below), you'll need to use the historical API instead of the standard live endpoints. The partitioning happens for **markets**, **market\_candlesticks**,
**trades**, and **orders**. Old **Events** and **Series** will always still be available through their original endpoints.

## How It Works

The boundary between live and historical data is defined by a set of **cutoff timestamps**, which you can retrieve at any time via `GET /historical/cutoff`. Any record older than the relevant cutoff must be queried through the corresponding historical endpoint.

The cutoff timestamps will be regularly updated, advancing forward over time. The target window for live data is **3 months**.

## Cutoff Timestamps

| Field               | Partitioned By                       | Meaning                                                                                                                                               |
| ------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `market_settled_ts` | Market settlement time               | Markets and their candlesticks that settled before this timestamp are only available via `GET /historical/markets`                                    |
| `trades_created_ts` | Trade fill time                      | Trades that occurred before this timestamp are only available via `GET /historical/trades`. User fills are only available via `GET /historical/fills` |
| `orders_updated_ts` | Order cancellation or execution time | Orders canceled or fully executed before this timestamp are only available via `GET /historical/orders`                                               |

<Note>
  Resting (active) orders are unaffected and always appear in `GET /portfolio/orders`, regardless of the cutoff.
</Note>

## Historical Endpoints

| Endpoint                                        | Description                                    |
| ----------------------------------------------- | ---------------------------------------------- |
| `GET /historical/cutoff`                        | Returns the current cutoff timestamps          |
| `GET /historical/markets`                       | Settled markets older than the cutoff          |
| `GET /historical/markets/{ticker}`              | Single historical market by ticker             |
| `GET /historical/markets/{ticker}/candlesticks` | Candlestick data for historical markets        |
| `GET /historical/trades`                        | All trades older than the cutoff               |
| `GET /historical/fills`                         | User-scoped trade fills older than the cutoff  |
| `GET /historical/orders`                        | Canceled/executed orders older than the cutoff |

## Impacted Live Endpoints

The following live endpoints will no longer return data older than the corresponding cutoff:

| Live Endpoint                                 | Cutoff Field        | Impact                                                                                          |
| --------------------------------------------- | ------------------- | ----------------------------------------------------------------------------------------------- |
| `GET /markets`, `GET /markets/{ticker}`       | `market_settled_ts` | Settled markets and their candlesticks older than the cutoff will not appear                    |
| `GET /events` with `with_nested_markets=true` | `market_settled_ts` | Nested markets older than the cutoff will not be included, only markets impacted                |
| `GET /markets/trades`                         | `trades_created_ts` | Trades older than the cutoff will not appear                                                    |
| `GET /portfolio/fills`                        | `trades_created_ts` | Fills older than the cutoff will not appear                                                     |
| `GET /portfolio/orders`                       | `orders_updated_ts` | Completed/canceled orders older than the cutoff will not appear (resting orders are unaffected) |

## Migration Guide

1. **Fetch the cutoff**: call `GET /historical/cutoff` to get the current timestamps.
2. **Route queries accordingly**: if the data you need is older than the relevant cutoff, use the corresponding `GET /historical/...` endpoint instead.
3. **Combine results if needed**: for use cases like building a complete fill history, query both the live and historical endpoints and merge the results.

<Info>
  The historical endpoints support the same [cursor-based pagination](/getting_started/pagination) as their live counterparts.
</Info>
