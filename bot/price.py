import random
from bot.config import BASE_PRICE

def random_price(coin: str) -> float:
    base = BASE_PRICE[coin]
    change_rate = random.uniform(-0.05, 0.05)
    decimals = 8 if base < 1 else 4
    return round(base * (1 + change_rate), decimals)
