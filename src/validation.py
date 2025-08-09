"""
Validation helpers for Binance Futures symbols and filters.
"""
from decimal import Decimal, ROUND_DOWN, getcontext
from typing import Optional, Dict, Any
import logging

getcontext().prec = 28

from api_client import BinanceFuturesClient

logger = logging.getLogger("BasicBot")

def parse_symbol_info(exchange_info: Dict[str, Any], symbol: str) -> Optional[Dict[str, Any]]:
    for s in exchange_info.get("symbols", []):
        if s.get("symbol") == symbol:
            return s
    return None

def _get_filter_value(symbol_info: Dict[str, Any], filter_type: str, key: str):
    for f in symbol_info.get("filters", []):
        if f.get("filterType") == filter_type:
            return f.get(key)
    return None

def quantize_qty(qty: float, step_size: str) -> Decimal:
    step = Decimal(step_size)
    qty_d = Decimal(str(qty))
    return (qty_d // step * step).quantize(step)

def quantize_price(price: float, tick_size: str) -> Decimal:
    tick = Decimal(tick_size)
    p = Decimal(str(price))
    return (p // tick * tick).quantize(tick)

def validate_symbol_and_params(client: BinanceFuturesClient, symbol: str,
                               quantity: float, price: Optional[float] = None,
                               stop_price: Optional[float] = None) -> Dict[str, Any]:
    result = {"ok": False, "msg": "", "symbol": symbol}
    try:
        info = client.get_exchange_info()
    except Exception as e:
        result["msg"] = f"Failed to fetch exchangeInfo: {e}"
        return result

    sym_info = parse_symbol_info(info, symbol)
    if not sym_info:
        result["msg"] = f"Symbol {symbol} not found in exchangeInfo"
        return result

    min_qty = _get_filter_value(sym_info, "LOT_SIZE", "minQty")
    step_size = _get_filter_value(sym_info, "LOT_SIZE", "stepSize")
    max_qty = _get_filter_value(sym_info, "LOT_SIZE", "maxQty")

    tick_size = _get_filter_value(sym_info, "PRICE_FILTER", "tickSize")
    min_price = _get_filter_value(sym_info, "PRICE_FILTER", "minPrice")
    max_price = _get_filter_value(sym_info, "PRICE_FILTER", "maxPrice")

    qty_dec = Decimal(str(quantity))
    if min_qty and qty_dec < Decimal(str(min_qty)):
        result["msg"] = f"Quantity {quantity} below minQty {min_qty}"
        return result
    if max_qty and qty_dec > Decimal(str(max_qty)):
        result["msg"] = f"Quantity {quantity} above maxQty {max_qty}"
        return result
    
    adj_qty = quantize_qty(quantity, step_size) if step_size else qty_dec
    if adj_qty == 0:
        result["msg"] = f"Quantity {quantity} quantized to 0 with stepSize {step_size}"
        return result

    adj_price = None
    if price is not None:
        price_dec = Decimal(str(price))
        if min_price and price_dec < Decimal(str(min_price)):
            result["msg"] = f"Price {price} below minPrice {min_price}"
            return result
        if max_price and price_dec > Decimal(str(max_price)):
            result["msg"] = f"Price {price} above maxPrice {max_price}"
            return result
        adj_price = quantize_price(price, tick_size) if tick_size else price_dec

    adj_stop_price = None
    if stop_price is not None:
        stop_price_dec = Decimal(str(stop_price))
        if min_price and stop_price_dec < Decimal(str(min_price)):
            result["msg"] = f"Stop price {stop_price} below minPrice {min_price}"
            return result
        if max_price and stop_price_dec > Decimal(str(max_price)):
            result["msg"] = f"Stop price {stop_price} above maxPrice {max_price}"
            return result
        adj_stop_price = quantize_price(stop_price, tick_size) if tick_size else stop_price_dec

    result.update({
        "ok": True, "msg": "validated",
        "adj_quantity": float(adj_qty),
        "adj_price": float(adj_price) if adj_price is not None else None,
        "adj_stop_price": float(adj_stop_price) if adj_stop_price is not None else None,
        "symbol_info": {"baseAsset": sym_info.get("baseAsset"), "quoteAsset": sym_info.get("quoteAsset")}
    })
    return result
