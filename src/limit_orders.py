"""
Place LIMIT and STOP-LIMIT orders on Binance Futures Testnet (USDT-M)
"""
import logging
from typing import Dict, Any, Optional

from api_client import BinanceFuturesClient
from validation import validate_symbol_and_params

logger = logging.getLogger("BasicBot")


def place_limit_order(client: BinanceFuturesClient, symbol: str, side: str, quantity: float, price: float,
                      time_in_force: str = "GTC", dry_run: bool = False, stop_price: Optional[float] = None) -> Dict[str, Any]:
    """
    Places a LIMIT or STOP-LIMIT order.
    - If stop_price is None, a standard LIMIT order is placed.
    - If stop_price is provided, a STOP-LIMIT order is placed.
      (The API type for this is 'STOP' with both price and stopPrice).
    """
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")

    v = validate_symbol_and_params(client, symbol, quantity, price=price, stop_price=stop_price)
    if not v.get("ok"):
        logger.error("Validation failed: %s", v.get("msg"))
        return {"error": v.get("msg")}

    adj_qty = v.get("adj_quantity", quantity)
    adj_price = v.get("adj_price", price)
    adj_stop_price = v.get("adj_stop_price", stop_price)

    order_type = "STOP" if adj_stop_price else "LIMIT"
    
    log_msg = f"Placing {order_type} {side} {symbol} qty={adj_qty} price={adj_price}"
    if adj_stop_price:
        log_msg += f" stopPrice={adj_stop_price}"
    log_msg += f" tif={time_in_force} (dry_run={dry_run})"
    logger.info(log_msg)

    params = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": adj_qty,
        "price": adj_price,
        "timeInForce": time_in_force
    }

    if adj_stop_price:
        params["stopPrice"] = adj_stop_price
        params["workingType"] = "CONTRACT_PRICE"

    if dry_run:
        try:
            params.setdefault("timestamp", client._timestamp())
            params.setdefault("recvWindow", client.recv_window)
            qs = "&".join(f"{k}={params[k]}" for k in sorted(params))
            sig = client._sign(qs)
            return {"dry_run": True, "signed_query": qs + "&signature=" + sig}
        except Exception as e:
            logger.exception("Dry-run signing failed: %s", e)
            return {"error": str(e)}

    resp = client._request_with_backoff("POST", "/fapi/v1/order", params, signed=True)
    logger.info("Limit/Stop-Limit order response: %s", resp)
    return resp


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    client = BinanceFuturesClient(api_key=os.environ.get("BINANCE_API_KEY"), api_secret=os.environ.get("BINANCE_API_SECRET"))
    print(place_limit_order(client, "BTCUSDT", "SELL", 0.001, 64000.0, stop_price=65000.0, dry_run=True))
