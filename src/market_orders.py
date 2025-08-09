"""
Place MARKET orders on Binance Futures Testnet (USDT-M)
"""
import logging
from typing import Dict, Any

from api_client import BinanceFuturesClient
from validation import validate_symbol_and_params

logger = logging.getLogger("BasicBot")


def place_market_order(client: BinanceFuturesClient, symbol: str, side: str, quantity: float, dry_run: bool = False) -> Dict[str, Any]:
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")

    v = validate_symbol_and_params(client, symbol, quantity, price=None)
    if not v.get("ok"):
        logger.error("Validation failed: %s", v.get("msg"))
        return {"error": v.get("msg")}

    adj_qty = v.get("adj_quantity", quantity)
    logger.info("Placing MARKET %s %s qty=%s (dry_run=%s)", side, symbol, adj_qty, dry_run)

    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": adj_qty
    }

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
    logger.info("Market order response: %s", resp)
    return resp


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    client = BinanceFuturesClient(api_key=os.environ.get("BINANCE_API_KEY"), api_secret=os.environ.get("BINANCE_API_SECRET"))
    print(place_market_order(client, "BTCUSDT", "BUY", 0.001, dry_run=True))
