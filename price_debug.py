# debug_price.py
import time
from bot.price import get_cached_price, random_price
from bot.interpolator import SmoothPriceInterpolator

COINS = ["BTC", "ETH"]  # 테스트할 코인
interpolator = SmoothPriceInterpolator(alpha=0.15, steps=5)

ORDER_INTERVAL = 0.5  # 시뮬레이션용
ITERATIONS = 100       # 반복 수

for i in range(ITERATIONS):
    print(f"\n=== Iteration {i+1} ===")
    for coin in COINS:
        raw_price = get_cached_price(coin)
        if raw_price is None:
            print(f"{coin} 가격 불러오기 실패")
            continue

        sim_price = random_price(coin)  # price.py 랜덤 변동
        smooth_prices = interpolator.smooth(coin, sim_price)

        print(f"[{coin}] RAW={raw_price:.2f} | SIM={sim_price:.2f}")
        print(f"[{coin}] SMOOTH={smooth_prices}")

    time.sleep(ORDER_INTERVAL)
