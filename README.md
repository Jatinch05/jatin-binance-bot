# Binance Futures CLI Trading Bot

This project is a command-line interface (CLI) trading bot for the Binance USDT-M Futures Testnet. It is built with a focus on modularity, robustness, and reusability, allowing for easy execution of various order types.

## Features

* **Standard Orders**: Full support for `MARKET` and `LIMIT` orders.
* **Advanced Orders**: Full support for `STOP-LIMIT` and `TWAP` (Time-Weighted Average Price) orders.
* **Pre-Trade Validation**: All orders are validated against the latest exchange rules (tick size, step size, min/max quantity) before being sent.
* **Resilient Networking**: A custom API client with exponential backoff handles API rate limits and server errors gracefully.
* **Secure**: Uses environment variables to protect sensitive API credentials.
* **Dual Logging**:
    * `bot.log`: Human-readable log for high-level events.
    * `api_requests.log`: Detailed developer log with raw API request/response data for debugging.

## Project Structure

```
[project_root]/
├── src/
│   ├── api_client.py
│   ├── cli.py
│   ├── limit_orders.py
│   ├── market_orders.py
│   ├── validation.py
│   └── advanced/
│       └── twap.py
├── test_validation.py
├── .env
├── .gitignore
├── bot.log
├── api_requests.log
└── README.md
```

## Prerequisites

* Python 3.8+
* A Binance Testnet account
* Testnet API Key and Secret

## Setup Instructions

1.  **Clone the Repository**:
    ```bash
    git clone <your-github-repo-url>
    cd <your-repo-name>
    ```

2.  **Install Dependencies**:
    The project's dependencies are listed in `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Create Environment File**:
    Create a file named `.env` in the root directory of the project and add your Testnet API credentials:
    ```
    BINANCE_API_KEY="your_testnet_api_key_here"
    BINANCE_API_SECRET="your_testnet_api_secret_here"
    ```

## How to Run the Bot

All commands should be run from the **root directory** of the project.

### **Example 1: Place a Market Order**

Place a market order to buy 0.001 BTC.

```bash
python src/cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### **Example 2: Place a Limit Order**

Place a limit order to sell 0.1 ETH at a price of $3000.

```bash
python src/cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3000
```

### **Example 3: Place a Stop-Limit Order (for Risk Management)**

Place an order to sell 0.1 ETH at a limit price of $2999 if the contract price drops to $3000.

```bash
python src/cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 2999 --stop-price 3000
```

### **Example 4: Execute a TWAP Order**

Execute a large order to buy 0.5 BTC by splitting it into 10 smaller orders, placed 30 seconds apart.

```bash
python src/cli.py --symbol BTCUSDT --side BUY --type TWAP --quantity 0.5 --slices 10 --interval 30
