# bot/order.py
import random
from typing import Optional, Dict
from bot.config import COINS, CATEGORY_MAP, BOT_ID
from bot.price import random_price

def create_order() -> Optional[Dict]:
    coin = random.choice(COINS)
    price = random_price(coin)

    if price is None:
        return None

    order_type = random.choice(["BUY", "SELL"])

    return {
        "botId": BOT_ID,
        "categoryId": CATEGORY_MAP[coin],
        "orderPrice": price,
        "orderCount": round(random.uniform(0.1, 3), 4),
        "orderType": order_type,
        "_coin": coin
    }
