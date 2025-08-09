import argparse
import logging
import time
from api_client import BinanceFuturesClient
from market_orders import place_market_order
from limit_orders import place_limit_order
from advanced.twap import run_twap

def print_order_summary(result):
    """Formats and prints a user-friendly summary of an order result."""
    if not result or result.get("error"):
        print(f"\nOrder Failed: {result.get('error', 'Unknown error')}")
        return

    if result.get("dry_run"):
        print("\nDry Run Successful. The signed query string is:")
        print(f"   {result.get('signed_query')}")
        return

    if result.get("orderId"):
        print("\nOrder Placed Successfully!")
        print("---------------------------------")
        print(f"  Symbol:     {result.get('symbol')}")
        print(f"  Order ID:   {result.get('orderId')}")
        print(f"  Side:       {result.get('side')}")
        print(f"  Type:       {result.get('type')}")
        print(f"  Quantity:   {result.get('origQty')}")
        
        if result.get('type') in ['LIMIT', 'STOP']:
            print(f"  Price:      {result.get('price')}")
        if result.get('stopPrice') and float(result.get('stopPrice')) > 0:
            print(f"  Stop Price: {result.get('stopPrice')}")
            
        print(f"  Status:     {result.get('status')}")
        print("---------------------------------")

def run_normal_order(client, args):
    """Place a normal MARKET or LIMIT/STOP-LIMIT order using the appropriate module."""
    if args.type == "MARKET":
        result = place_market_order(
            client=client,
            symbol=args.symbol,
            side=args.side,
            quantity=args.quantity,
            dry_run=args.dry_run
        )
    elif args.type == "LIMIT":
        if not args.price:
            logging.error("Price is required for LIMIT orders")
            print_order_summary({"error": "Price is required for LIMIT orders"})
            return
        
        result = place_limit_order(
            client=client,
            symbol=args.symbol,
            side=args.side,
            quantity=args.quantity,
            price=args.price,
            time_in_force=args.time_in_force or "GTC",
            dry_run=args.dry_run,
            stop_price=args.stop_price
        )
    else:
        result = {"error": f"Unsupported order type: {args.type}"}
    
    print_order_summary(result)

def run_twap_order(client, args):
    """Execute a TWAP order using the dedicated TWAP module."""
    result = run_twap(
        client=client,
        symbol=args.symbol,
        side=args.side,
        total_quantity=args.quantity,
        slices=args.slices,
        interval_sec=args.interval,
        dry_run=args.dry_run
    )
    
    if result and not result.get("error"):
        print("\nTWAP Strategy Completed!")
        print("---------------------------------")
        print(f"  Symbol:           {result.get('symbol')}")
        print(f"  Side:             {result.get('side')}")
        print(f"  Total Quantity:   {result.get('total_quantity')}")
        summary = result.get('summary', {})
        print(f"  Slices Attempted: {summary.get('slices_attempted')}")
        print(f"  Slices Successful: {summary.get('slices_successful')}")
        print(f"  Total Executed:   {summary.get('total_executed')}")
        print(f"  Average Price:    ${summary.get('avg_price'):.4f}")
        print("---------------------------------")
    else:
        print_order_summary(result)


def main():
    parser = argparse.ArgumentParser(description="A CLI-based trading bot for Binance Futures.")
    parser.add_argument("--symbol", required=True, help="Trading symbol (e.g., BTCUSDT)")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL"], help="Order side: BUY or SELL")
    parser.add_argument("--type", required=True, choices=["MARKET", "LIMIT", "TWAP"], help="Order type. Use LIMIT for both regular limit and stop-limit orders.")
    parser.add_argument("--quantity", type=float, required=True, help="Order quantity")
    parser.add_argument("--price", type=float, help="The limit price for a LIMIT or STOP-LIMIT order.")
    parser.add_argument("--stop-price", type=float, help="The trigger price for a STOP-LIMIT order. If provided, turns a LIMIT order into a STOP-LIMIT order.")
    parser.add_argument("--time-in-force", dest="time_in_force", help="Time in force for LIMIT orders (e.g., GTC, IOC, FOK)")
    parser.add_argument("--dry-run", action="store_true", help="Prepare and sign the order but do not send it.")
    
    parser.add_argument("--slices", type=int, default=10, help="For TWAP orders: the number of smaller orders to split into.")
    parser.add_argument("--interval", type=int, default=5, help="For TWAP orders: the seconds to wait between each slice.")
    
    args = parser.parse_args()

    client = BinanceFuturesClient()

    if args.type == "TWAP":
        run_twap_order(client, args)
    else:
        run_normal_order(client, args)

if __name__ == "__main__":
    main()
