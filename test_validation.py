import os
import json
import sys
from dotenv import load_dotenv

# --- The Magic Fix ---
# This block tells Python where to find your 'src' folder.
# 1. os.path.dirname(__file__) gets the directory of this test file (your project root).
# 2. os.path.join(...) creates a full path to your 'src' folder (e.g., 'D:\Binance-bot\src').
# 3. sys.path.append(...) adds this 'src' path to the list of places Python looks for modules.
# This line MUST come BEFORE you try to import your own modules.
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Now that Python knows where to look, these imports will work perfectly.
from api_client import BinanceFuturesClient
from validation import validate_symbol_and_params

def run_tests():
    """
    Runs a series of validation tests against the Binance API.
    """
    print("--- Running Validation Tests from Root ---")
    
    load_dotenv()
    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        print("\n[ERROR] API keys not found. Please set them in a .env file to run tests.")
        return

    client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)

    test_cases = [
        {"symbol": "BTCUSDT", "quantity": 0.005, "price": None, "stop_price": None, "desc": "Valid BTCUSDT market order"},
        {"symbol": "ETHUSDT", "quantity": 0.1, "price": 3000.0, "stop_price": None, "desc": "Valid ETHUSDT limit order"},
        {"symbol": "LINKUSDT", "quantity": 10, "price": 15.0, "stop_price": 16.0, "desc": "Valid LINKUSDT stop-limit order"},
        {"symbol": "BTCUSDT", "quantity": 0.00001, "price": 65000.0, "stop_price": None, "desc": "Invalid quantity (too small)"},
        {"symbol": "ETHUSDT", "quantity": 0.1, "price": 3000.123, "stop_price": None, "desc": "Price is quantized to be valid"},
        {"symbol": "FAKESYMBOL123", "quantity": 1, "price": 100, "stop_price": None, "desc": "Non-existent symbol"},
    ]

    for i, case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1}: {case['desc']} ---")
        try:
            result = validate_symbol_and_params(
                client=client,
                symbol=case["symbol"],
                quantity=case["quantity"],
                price=case["price"],
                stop_price=case["stop_price"]
            )
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"An unexpected error occurred during the test: {e}")


if __name__ == "__main__":
    run_tests()
