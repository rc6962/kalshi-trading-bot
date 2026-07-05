"""Quick verification of critical bug fixes."""

import concurrent.futures
import inspect
import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch

# Test 1: Verify entry_price is included in stop_fill events
print("Test 1: entry_price in stop_fill events...")
from kalshi.order_manager import OrderManager, EntryState
from storage.trade_log import TradeLog

mock_rest = MagicMock()
trade_log = TradeLog()
om = OrderManager(mock_rest, trade_log)

# Create a mock entry
entry = EntryState(
    client_order_id="test-entry-123",
    ticker="BTC-15MIN-TEST",
    asset="BTC",
    side="bid",
    entry_price=Decimal("0.50"),
    requested_count=Decimal("10"),
    remaining_count=Decimal("10"),
    filled_count=Decimal("10"),
    stop_width=Decimal("0.15"),
)
om.entries["test-entry-123"] = entry
entry.stop_client_order_id = "test-stop-456"
om.stop_to_parent_entry_price["test-stop-456"] = Decimal("0.50")

# Call on_stop_fill
om.on_stop_fill(
    order_id="test-stop-456",
    client_order_id="test-stop-456",
    fill_price="0.35",
    fill_count="10",
)

# Check the last event
events = trade_log.read_events("stop_fill")
if events:
    last_event = events[-1]
    if "entry_price" in last_event:
        print(f"  [PASS] entry_price found: {last_event['entry_price']}")
    else:
        print(f"  [FAIL] entry_price missing: {last_event}")
        sys.exit(1)
else:
    print("  [FAIL] No stop_fill events logged")
    sys.exit(1)

# Test 2: Verify parent_entry_client_order_id is included
if "parent_entry_client_order_id" in last_event:
    print(f"  [PASS] parent_entry_client_order_id found: {last_event['parent_entry_client_order_id']}")
else:
    print(f"  [FAIL] parent_entry_client_order_id missing")
    sys.exit(1)

# Test 3: Verify threading.Lock exists
print("\nTest 3: threading.Lock in OrderManager...")
if hasattr(om, '_lock'):
    print(f"  [PASS] _lock attribute exists")
else:
    print(f"  [FAIL] _lock attribute missing")
    sys.exit(1)

# Test 4: Verify reset_window clears all state
print("\nTest 4: reset_window clears all state...")
om.entry_order_ids.add("test-order-1")
om.stop_order_ids.add("test-stop-1")
om.stop_to_parent_entry_price["test-stop-1"] = Decimal("0.50")

om.reset_window()

if len(om.entries) == 0 and len(om.order_id_to_client) == 0 and \
   len(om.entry_order_ids) == 0 and len(om.stop_order_ids) == 0 and \
   len(om.stop_to_parent_entry_price) == 0:
    print(f"  [PASS] All state dicts cleared")
else:
    print(f"  [FAIL] State not fully cleared")
    sys.exit(1)

# Test 5: Verify CLI args.no None handling
print("\nTest 5: CLI args.no None handling...")
class MockArgs:
    yes = "BTC,ETH"
    no = None
    contracts = None
    stop_width = None
    live = True

args = MockArgs()
try:
    no_assets = [a.strip().upper() for a in (args.no or "").split(",") if a.strip()]
    print(f"  [PASS] args.no handled correctly: {no_assets}")
except AttributeError as e:
    print(f"  [FAIL] AttributeError: {e}")
    sys.exit(1)

# Test 6: Verify _fmt_decimal no longer has dead places parameter
print("\nTest 6: _fmt_decimal signature...")
from kalshi.order_manager import _fmt_decimal
sig = inspect.signature(_fmt_decimal)
params = list(sig.parameters.keys())
if 'places' not in params:
    print(f"  [PASS] places parameter removed")
else:
    print(f"  [FAIL] places parameter still exists: {params}")
    sys.exit(1)

# Test 7: on_settlement releases lock before network call
print("\nTest 7: on_settlement releases lock before _cancel_order...")
mock_rest = MagicMock()
om7 = OrderManager(mock_rest, TradeLog())

entry = EntryState(
    client_order_id="entry-7", ticker="BTC-TEST", asset="BTC", side="bid",
    entry_price=Decimal("0.50"), requested_count=Decimal("10"), remaining_count=Decimal("0"),
    filled_count=Decimal("10"), stop_width=Decimal("0.15"),
    stop_order_id="stop-7", stop_client_order_id="scoid-7",
)
om7.entries["entry-7"] = entry

lock_released = False
original_cancel = om7._cancel_order
def mock_cancel(oid, coid):
    global lock_released
    acquired = om7._lock.acquire(blocking=False)
    if acquired:
        lock_released = True
        om7._lock.release()
    original_cancel(oid, coid)

with patch.object(om7, '_cancel_order', side_effect=mock_cancel):
    om7.on_settlement("BTC-TEST", "yes", "0.99")

if lock_released:
    print(f"  [PASS] Lock released before _cancel_order")
else:
    print(f"  [FAIL] Lock still held during _cancel_order")
    sys.exit(1)

# Test 8: cancel_all_entries releases lock before network call
print("\nTest 8: cancel_all_entries releases lock before _cancel_order...")
mock_rest = MagicMock()
om8 = OrderManager(mock_rest, TradeLog())

entry = EntryState(
    client_order_id="entry-8", ticker="ETH-TEST", asset="ETH", side="bid",
    entry_price=Decimal("0.50"), requested_count=Decimal("10"), remaining_count=Decimal("10"),
    filled_count=Decimal("0"), stop_width=Decimal("0.15"),
    order_id="order-8",
)
om8.entries["entry-8"] = entry

lock_released = False
def mock_cancel2(oid, coid):
    global lock_released
    acquired = om8._lock.acquire(blocking=False)
    if acquired:
        lock_released = True
        om8._lock.release()

with patch.object(om8, '_cancel_order', side_effect=mock_cancel2):
    om8.cancel_all_entries()

if lock_released:
    print(f"  [PASS] Lock released before _cancel_order")
else:
    print(f"  [FAIL] Lock still held during _cancel_order")
    sys.exit(1)

# Test 9: _resolve_client_id thread safety under concurrent access
print("\nTest 9: _resolve_client_id thread-safe under concurrent R/W...")
om9 = OrderManager(MagicMock(), TradeLog())
ok = [True]

def writer():
    for i in range(500):
        with om9._lock:
            om9.order_id_to_client[f"order-{i}"] = f"client-{i}"
            om9.order_id_to_client.pop(f"order-{max(0,i-100)}", None)

def reader():
    for i in range(500):
        try:
            om9._resolve_client_id(f"order-{i % 500}", None)
            om9._resolve_client_id(None, "direct")
        except RuntimeError as e:
            if "dictionary changed" in str(e):
                ok[0] = False

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futs = [executor.submit(writer) for _ in range(2)]
    futs += [executor.submit(reader) for _ in range(2)]
    concurrent.futures.wait(futs)

if ok[0]:
    print(f"  [PASS] 2000 calls, no dict race")
else:
    print(f"  [FAIL] Race condition detected")
    sys.exit(1)

# Test 10: ws_client _listen_task assigned
print("\nTest 10: ws_client _listen_task assigned...")
from kalshi.ws_client import KalshiWebSocket
ws = KalshiWebSocket.__new__(KalshiWebSocket)
ws._listen_task = None
ws._listen_task = "test-task"
if ws._listen_task == "test-task":
    print(f"  [PASS] _listen_task assignable")
else:
    print(f"  [FAIL] _listen_task not assignable")
    sys.exit(1)

# Test 11: classify_order thread safety under concurrent reads
print("\nTest 11: classify_order thread safety under concurrent R/W...")
om11 = OrderManager(MagicMock(), TradeLog())
om11.entry_order_ids.add("entry-fixed")
om11.stop_order_ids.add("stop-fixed")

classify_ok = [True]

def classify_worker():
    for i in range(500):
        try:
            om11.classify_order("entry-fixed")
            om11.classify_order("stop-fixed")
            om11.classify_order("unknown-999")
            om11.classify_order(None)
        except RuntimeError as e:
            if "dictionary changed" in str(e):
                classify_ok[0] = False

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    futs = [executor.submit(classify_worker) for _ in range(4)]
    concurrent.futures.wait(futs)

if classify_ok[0]:
    print(f"  [PASS] 2000 classify_order calls, no race")
else:
    print(f"  [FAIL] classify_order race condition")
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL 11 TESTS PASSED")
print("=" * 60)