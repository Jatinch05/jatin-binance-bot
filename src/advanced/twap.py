"""
TWAP strategy module for Binance Futures Testnet (USDT-M).

Functions:
- run_twap(client, symbol, side, total_quantity, slices, interval_sec, dry_run=False)

Behavior:
- Splits total_quantity into `slices` equal parts (last slice gets remainder due to quantization).
- For each slice:
    - Validates and quantizes slice quantity using validate_symbol_and_params
    - If dry_run: builds and returns signed query string for inspection
    - Else: places a MARKET order and records the response
- Sleeps `interval_sec` between slices (not after last slice)
- Returns a summary dict with per-slice results.
"""
import time
import logging
from decimal import Decimal, getcontext
from typing import Dict, Any, List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_client import BinanceFuturesClient
from validation import validate_symbol_and_params

getcontext().prec = 28
logger = logging.getLogger("BasicBot")


def _split_quantity(total_qty: float, slices: int) -> List[Decimal]:
    """
    Split total_qty into `slices` Decimal parts. The sum of parts <= total_qty,
    with the remainder (due to quantization) placed into the last slice.
    This function returns Decimal parts; further quantization by exchange filters
    will be applied during validation.
    """
    total = Decimal(str(total_qty))
    if slices <= 0:
        raise ValueError("slices must be >= 1")
    base = (total / Decimal(slices)).quantize(Decimal("1.00000000")) 
    parts = [base for _ in range(slices)]
    summed = sum(parts)
    remainder = total - summed
    if remainder != 0:
        parts[-1] = (parts[-1] + remainder)
    return parts


def run_twap(client: BinanceFuturesClient, symbol: str, side: str,
             total_quantity: float, slices: int = 5, interval_sec: int = 10,
             dry_run: bool = False) -> Dict[str, Any]:
    """
    Execute a TWAP: splits total_quantity into slices and places MARKET orders.

    Returns:
      {
        "symbol": symbol,
        "side": side,
        "total_quantity": total_quantity,
        "slices": slices,
        "interval_sec": interval_sec,
        "results": [ {slice_index, requested_qty, adj_qty, dry_run_signed_query or resp or error, timestamp}, ... ],
        "summary": { "total_executed": X, "avg_price": Y, ...}
      }
    """
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")

    if slices < 1:
        raise ValueError("slices must be >= 1")

    logger.info("Starting TWAP: symbol=%s side=%s total_qty=%s slices=%d interval=%ds dry_run=%s",
                symbol, side, total_quantity, slices, interval_sec, dry_run)

    slice_parts = _split_quantity(total_quantity, slices)
    results: List[Dict[str, Any]] = []
    total_executed = Decimal("0")
    total_quote = Decimal("0")

    for i, part in enumerate(slice_parts):
        requested = float(part)
        ts = int(time.time() * 1000)
        logger.info("TWAP slice %d/%d requested_qty=%s", i + 1, slices, requested)

        v = validate_symbol_and_params(client, symbol, requested, price=None)
        if not v.get("ok"):
            logger.error("TWAP slice %d validation failed: %s", i + 1, v.get("msg"))
            results.append({"slice": i + 1, "requested_qty": requested, "ok": False, "error": v.get("msg")})
            if i != slices - 1:
                time.sleep(interval_sec)
            continue

        adj_qty = v.get("adj_quantity", requested)
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": adj_qty,
            "timestamp": client._timestamp(),
            "recvWindow": client.recv_window
        }

        if dry_run:
            qs = "&".join(f"{k}={params[k]}" for k in sorted(params))
            try:
                sig = client._sign(qs)
                signed = qs + "&signature=" + sig
                logger.info("TWAP slice %d dry-run signed query: %s", i + 1, signed)
                results.append({"slice": i + 1, "requested_qty": requested, "adj_quantity": adj_qty,
                                "dry_run": True, "signed_query": signed, "timestamp": ts})
            except Exception as e:
                logger.exception("TWAP slice %d dry-run signing failed: %s", i + 1, e)
                results.append({"slice": i + 1, "requested_qty": requested, "error": str(e), "timestamp": ts})
        else:
            try:
                resp = client._request_with_backoff("POST", "/fapi/v1/order", {
                    "symbol": params["symbol"], "side": params["side"], "type": params["type"], "quantity": params["quantity"]
                }, signed=True)
                logger.info("TWAP slice %d response: %s", i + 1, resp)
                results.append({"slice": i + 1, "requested_qty": requested, "adj_quantity": adj_qty,
                                "resp": resp, "timestamp": ts})
                executed_qty = Decimal(str(resp.get("executedQty", "0"))) if isinstance(resp.get("executedQty", "0"), (str, float, int)) else Decimal("0")
                avg_price = Decimal(str(resp.get("avgPrice", "0"))) if resp.get("avgPrice") else Decimal("0")
                if executed_qty > 0 and avg_price > 0:
                    total_executed += executed_qty
                    total_quote += (executed_qty * avg_price)
            except Exception as e:
                logger.exception("TWAP slice %d failed: %s", i + 1, e)
                results.append({"slice": i + 1, "requested_qty": requested, "error": str(e), "timestamp": ts})

        if i != slices - 1:
            logger.info("TWAP sleeping for %ds before next slice", interval_sec)
            time.sleep(interval_sec)

    avg_price = (total_quote / total_executed) if (total_executed > 0) else Decimal("0")

    summary = {
        "total_executed": float(total_executed),
        "avg_price": float(avg_price),
        "slices_attempted": slices,
        "slices_successful": sum(1 for r in results if r.get("resp") and float(r["resp"].get("executedQty", 0)) > 0)
    }

    logger.info("TWAP completed: %s", summary)

    return {
        "symbol": symbol,
        "side": side,
        "total_quantity": total_quantity,
        "slices": slices,
        "interval_sec": interval_sec,
        "dry_run": dry_run,
        "results": results,
        "summary": summary
    }
