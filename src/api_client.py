"""
Binance Futures API client (Testnet-ready)
- Signed requests with HMAC-SHA256
- Exponential backoff for 429/5xx
- get_exchange_info() helper
"""
import os
import time
import json
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import requests
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")


TESTNET_BASE_URL = "https://testnet.binancefuture.com"
FAPI_EXCHANGE_INFO = "/fapi/v1/exchangeInfo"

PROJECT_ROOT = Path(__file__).parent.parent
BOT_LOG_PATH = PROJECT_ROOT / "bot.log"
API_LOG_PATH = PROJECT_ROOT / "api_requests.log"

logger = logging.getLogger("BasicBot")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(BOT_LOG_PATH)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(ch)

api_logger = logging.getLogger("api")
if not api_logger.handlers:
    api_logger.setLevel(logging.INFO) 
    api_fh = logging.FileHandler(API_LOG_PATH)
    api_fh.setLevel(logging.DEBUG) 
    api_fh.setFormatter(logging.Formatter("%(message)s"))
    api_logger.addHandler(api_fh)


class BinanceAPIError(Exception):
    pass


class BinanceFuturesClient:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 base_url: str = TESTNET_BASE_URL, recv_window: int = 5000):
        self.api_key = api_key or os.environ.get("BINANCE_API_KEY")
        self.api_secret = (api_secret or os.environ.get("BINANCE_API_SECRET") or "").encode()
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"X-MBX-APIKEY": self.api_key})
        logger.debug("BinanceFuturesClient initialized (base_url=%s)", self.base_url)

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, query_string: str) -> str:
        if not self.api_secret:
            raise ValueError("API secret required for signing")
        return hmac.new(self.api_secret, query_string.encode("utf-8"), hashlib.sha256).hexdigest()

    def _request_with_backoff(self, method: str, path: str, params: Dict[str, Any], signed: bool = False,
                              max_retries: int = 5) -> Dict[str, Any]:
        url = self.base_url + path
        params = params.copy() if params else {}
        if signed:
            params.setdefault("timestamp", self._timestamp())
            params.setdefault("recvWindow", self.recv_window)
            query_string = "&".join(f"{k}={params[k]}" for k in sorted(params))
            signature = self._sign(query_string)
            query_string = query_string + f"&signature={signature}"
            full_url = url + "?" + query_string
        else:
            query_string = "&".join(f"{k}={params[k]}" for k in params) if params else ""
            full_url = url + ("?" + query_string if query_string else "")

        attempt = 0
        backoff = 0.5
        while attempt <= max_retries:
            api_logger.debug(json.dumps({
                "attempt": attempt,
                "url": full_url,
                "method": method
            }))
            try:
                if method.upper() == "GET":
                    resp = self.session.get(full_url, timeout=10)
                elif method.upper() == "POST":
                    resp = self.session.post(full_url, timeout=10)
                elif method.upper() == "DELETE":
                    resp = self.session.delete(full_url, timeout=10)
                else:
                    raise ValueError("Unsupported method")

                api_logger.debug(json.dumps({
                    "status_code": resp.status_code,
                    "response": resp.text
                }))

                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code in (429, 418) or 500 <= resp.status_code < 600:
                    logger.warning("API returned %s. Backing off %.1fs (attempt %d)", resp.status_code, backoff, attempt)
                    time.sleep(backoff)
                    attempt += 1
                    backoff *= 2
                    continue
                raise BinanceAPIError(f"HTTP {resp.status_code}: {resp.text}")
            except requests.RequestException as e:
                logger.exception("Network error on request: %s", e)
                time.sleep(backoff)
                attempt += 1
                backoff *= 2

        raise BinanceAPIError("Max retries exceeded")

    def get_exchange_info(self) -> Dict[str, Any]:
        logger.debug("Fetching exchangeInfo")
        return self._request_with_backoff("GET", FAPI_EXCHANGE_INFO, params={}, signed=False)


if __name__ == "__main__":
    client = BinanceFuturesClient()
    try:
        info = client.get_exchange_info()
        print("exchangeInfo keys:", list(info.keys()))
        print("symbols found:", len(info.get("symbols", [])))
    except Exception as e:
        logger.exception("Failed to fetch exchangeInfo: %s", e)
