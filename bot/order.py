import random
from bot.config import COINS, CATEGORY_MAP, BOT_MEMBER_ID
from bot.price import random_price

def create_order() -> dict:
    coin = random.choice(COINS)
    order_type = random.choice(["BUY", "SELL"])

    return {
        "memberId": BOT_MEMBER_ID,
        "categoryId": CATEGORY_MAP[coin],
        "orderPrice": random_price(coin),
        "orderCount": round(random.uniform(0.1, 3), 4),
        "orderType": order_type,
        "isBot": True,
        "_coin": coin
    }
