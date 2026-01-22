# bot/price.py
import random
import time
import requests
from typing import Optional, Dict, Tuple

UPBIT_MARKET_URL = "https://api.upbit.com/v1/market/all"
UPBIT_TICKER_URL = "https://api.upbit.com/v1/ticker"

# ===== 캐시 설정 =====
PRICE_TTL = 1.0  # seconds
PRICE_CACHE: Dict[str, Tuple[float, float]] = {}

# KRW 마켓 캐시
_KRW_MARKETS = None


def load_krw_markets():
    global _KRW_MARKETS

    if _KRW_MARKETS is not None:
        return _KRW_MARKETS

    res = requests.get(UPBIT_MARKET_URL, timeout=3)
    res.raise_for_status()

    _KRW_MARKETS = {
        m["market"].replace("KRW-", "")
        for m in res.json()
        if m["market"].startswith("KRW-")
    }
    return _KRW_MARKETS


def fetch_upbit_price(coin: str) -> Optional[float]:
    krw_markets = load_krw_markets()

    if coin not in krw_markets:
        return None

    res = requests.get(
        UPBIT_TICKER_URL,
        params={"markets": f"KRW-{coin}"},
        timeout=2
    )

    if res.status_code != 200:
        return None

    return res.json()[0]["trade_price"]


def get_cached_price(coin: str) -> Optional[float]:
    now = time.time()

    # 1️⃣ 캐시 hit
    if coin in PRICE_CACHE:
        price, timestamp = PRICE_CACHE[coin]
        if now - timestamp < PRICE_TTL:
            return price

    # 2️⃣ 캐시 miss → 업비트 호출
    price = fetch_upbit_price(coin)

    if price is None:
        return None

    PRICE_CACHE[coin] = (price, now)
    return price


def format_price(price: float):
    if price >= 100:
        return int(round(price))
    elif price >= 10:
        return round(price, 1)
    else:
        return round(price, 2)


def random_price(coin: str) -> Optional[float]:
    base_price = get_cached_price(coin)

    if base_price is None:
        return None

    change_rate = random.uniform(-0.05, 0.05)
    price = base_price * (1 + change_rate)

    decimals = 8 if price < 1 else 4
    return format_price(price)