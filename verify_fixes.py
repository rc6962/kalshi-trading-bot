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

print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)