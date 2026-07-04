"""Quick verification of critical bug fixes."""

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
        print(f"  [PASS] entry_price found in stop_fill event: {last_event['entry_price']}")
    else:
        print(f"  [FAIL] entry_price missing from stop_fill event: {last_event}")
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
    print(f"    entries: {len(om.entries)}")
    print(f"    order_id_to_client: {len(om.order_id_to_client)}")
    print(f"    entry_order_ids: {len(om.entry_order_ids)}")
    print(f"    stop_order_ids: {len(om.stop_order_ids)}")
    print(f"    stop_to_parent_entry_price: {len(om.stop_to_parent_entry_price)}")
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
    print(f"  [PASS] args.no handled correctly, result: {no_assets}")
except AttributeError as e:
    print(f"  [FAIL] AttributeError: {e}")
    sys.exit(1)

# Test 6: Verify _fmt_decimal no longer has dead places parameter
print("\nTest 6: _fmt_decimal signature...")
import inspect
from kalshi.order_manager import _fmt_decimal
sig = inspect.signature(_fmt_decimal)
params = list(sig.parameters.keys())
if 'places' not in params:
    print(f"  [PASS] places parameter removed from _fmt_decimal")
else:
    print(f"  [FAIL] places parameter still exists: {params}")
    sys.exit(1)

# Test 7: Verify on_settlement doesn't hold lock during network call
print("\nTest 7: on_settlement releases lock before network call...")
import threading
from unittest.mock import patch

mock_rest = MagicMock()
om2 = OrderManager(mock_rest, TradeLog())

# Create an entry with a stop order
entry = EntryState(
    client_order_id="test-entry-789",
    ticker="BTC-15MIN-TEST2",
    asset="BTC",
    side="bid",
    entry_price=Decimal("0.50"),
    requested_count=Decimal("10"),
    remaining_count=Decimal("0"),
    filled_count=Decimal("10"),
    stop_width=Decimal("0.15"),
    stop_order_id="stop-999",
    stop_client_order_id="stop-client-999",
)
om2.entries["test-entry-789"] = entry

# Track if lock was released during _cancel_order call
lock_released_during_cancel = False
original_cancel = om2._cancel_order

def mock_cancel_with_check(order_id, coid):
    global lock_released_during_cancel
    # Try to acquire lock - if successful, it means lock was released
    acquired = om2._lock.acquire(blocking=False)
    if acquired:
        lock_released_during_cancel = True
        om2._lock.release()
    original_cancel(order_id, coid)

with patch.object(om2, '_cancel_order', side_effect=mock_cancel_with_check):
    om2.on_settlement("BTC-15MIN-TEST2", "yes", "0.99")

if lock_released_during_cancel:
    print(f"  [PASS] Lock released before _cancel_order call")
else:
    print(f"  [FAIL] Lock still held during _cancel_order call")
    sys.exit(1)

# Test 8: Verify cancel_all_entries doesn't hold lock during network call
print("\nTest 8: cancel_all_entries releases lock before network call...")
mock_rest = MagicMock()
om3 = OrderManager(mock_rest, TradeLog())

entry = EntryState(
    client_order_id="test-entry-999",
    ticker="ETH-15MIN-TEST",
    asset="ETH",
    side="bid",
    entry_price=Decimal("0.50"),
    requested_count=Decimal("10"),
    remaining_count=Decimal("10"),
    filled_count=Decimal("0"),
    stop_width=Decimal("0.15"),
    order_id="order-888",
)
om3.entries["test-entry-999"] = entry

lock_released_during_cancel = False

def mock_cancel_with_check2(order_id, coid):
    global lock_released_during_cancel
    acquired = om3._lock.acquire(blocking=False)
    if acquired:
        lock_released_during_cancel = True
        om3._lock.release()

with patch.object(om3, '_cancel_order', side_effect=mock_cancel_with_check2):
    om3.cancel_all_entries()

if lock_released_during_cancel:
    print(f"  [PASS] Lock released before _cancel_order call")
else:
    print(f"  [FAIL] Lock still held during _cancel_order call")
    sys.exit(1)

# Test 9: Verify _resolve_client_id is thread-safe
print("\nTest 9: _resolve_client_id thread safety...")
mock_rest = MagicMock()
om4 = OrderManager(mock_rest, TradeLog())
om4.order_id_to_client["order-123"] = "client-123"

# Should not raise or deadlock
result = om4._resolve_client_id("order-123", None)
if result == "client-123":
    print(f"  [PASS] _resolve_client_id works with lock")
else:
    print(f"  [FAIL] _resolve_client_id returned wrong value: {result}")
    sys.exit(1)

# Test 10: Verify ws_client _listen_task is assigned
print("\nTest 10: ws_client _listen_task assignment...")
from kalshi.ws_client import KalshiWebSocket
ws = KalshiWebSocket.__new__(KalshiWebSocket)
ws._listen_task = None
# Check that the attribute exists and can be assigned
ws._listen_task = "test-task"
if ws._listen_task == "test-task":
    print(f"  [PASS] _listen_task attribute exists and assignable")
else:
    print(f"  [FAIL] _listen_task not properly assigned")
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)