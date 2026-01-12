import random
import time
import requests
from threading import Thread, Lock
from dotenv import load_dotenv
import os

# =========================
# 환경 변수 로드
# =========================
load_dotenv()

UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")

# =========================
# 기본 설정
# =========================
SPRING_ORDER_URL = "http://localhost:8080/api/orders"
BOT_MEMBER_ID = 26
SECRET_TOKEN = "heartbit-internal-secret-token"

THREADS = 4
ORDERS_PER_THREAD = 100
ORDER_INTERVAL = 0.1

print_lock = Lock()
success = 0
fail = 0

# =========================
# DB 기준 categoryId
# =========================
CATEGORY_MAP = {
    "BTC": 41, "ETH": 42, "SOL": 43, "XRP": 44, "BNB": 45,
    "ADA": 46, "DOGE": 47, "AVAX": 48, "DOT": 49, "LTC": 50,
    "LINK": 51, "TRX": 52, "ATOM": 53, "FIL": 54, "ALGO": 55,
    "VET": 56, "XTZ": 57, "SHIB": 58, "EOS": 59, "MATIC": 60
}

# =========================
# 업비트 API
# =========================
def fetch_upbit_markets():
    """업비트에 존재하는 전체 마켓 코드 조회"""
    res = requests.get("https://api.upbit.com/v1/market/all")
    res.raise_for_status()
    return {m["market"] for m in res.json()}


def fetch_upbit_prices(coins):
    """KRW 마켓에 존재하는 코인들의 현재가 조회"""
    all_markets = fetch_upbit_markets()

    markets = [
        f"KRW-{coin}" for coin in coins
        if f"KRW-{coin}" in all_markets
    ]

    if not markets:
        raise RuntimeError("유효한 KRW 마켓이 하나도 없음")

    res = requests.get(
        "https://api.upbit.com/v1/ticker",
        params={"markets": ",".join(markets)}
    )

    if res.status_code != 200:
        raise RuntimeError(
            f"업비트 API 실패 (status={res.status_code}) → {res.text}"
        )

    price_map = {}
    for item in res.json():
        coin = item["market"].split("-")[1]
        price_map[coin] = item["trade_price"]

    return price_map


# =========================
# 가격 생성 로직
# =========================
def random_price(coin, base_prices):
    """기준가 대비 ±5% 랜덤 가격"""
    base = base_prices[coin]
    rate = random.uniform(-0.05, 0.05)
    return round(base * (1 + rate), 4)


# =========================
# 주문 생성 / 전송
# =========================
def create_order(coins, base_prices):
    coin = random.choice(coins)
    order_type = random.choice(["BUY", "SELL"])

    return {
        "memberId": BOT_MEMBER_ID,
        "categoryId": CATEGORY_MAP[coin],
        "orderPrice": random_price(coin, base_prices),
        "orderCount": round(random.uniform(0.1, 3), 4),
        "orderType": order_type,
        "isBot": True,
        "_coin": coin
    }


def send_order(order):
    global success, fail

    try:
        res = requests.post(
            SPRING_ORDER_URL,
            json=order,
            headers={
                "X-Internal-Token": SECRET_TOKEN,
                "Content-Type": "application/json"
            },
            timeout=2
        )

        with print_lock:
            if res.status_code == 200:
                success += 1
                print(
                    f"✅ [BOT] {order['_coin']} "
                    f"{order['orderType']} "
                    f"{order['orderCount']} @ {order['orderPrice']}"
                )
            else:
                fail += 1
                print(f"❌ FAIL {res.status_code}")
                print(f"   요청: {order}")

    except Exception as e:
        with print_lock:
            fail += 1
            print(f"💥 요청 예외: {e}")
            print(f"   요청: {order}")


# =========================
# BOT 스레드
# =========================
def bot_worker(coins, base_prices):
    for _ in range(ORDERS_PER_THREAD):
        order = create_order(coins, base_prices)
        send_order(order)
        time.sleep(ORDER_INTERVAL)


# =========================
# main
# =========================
def main():
    print("\n🚀 BOT 주문 시뮬레이션 시작")

    base_prices = fetch_upbit_prices(CATEGORY_MAP.keys())
    coins = list(base_prices.keys())

    print("📈 업비트 기준가 로딩 완료")
    for c, p in base_prices.items():
        print(f" - {c}: {p}")

    start = time.time()

    threads = []
    for _ in range(THREADS):
        t = Thread(target=bot_worker, args=(coins, base_prices))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    elapsed = time.time() - start
    total = success + fail

    print("\n==============================")
    print(f"총 주문 수 : {total}")
    print(f"성공      : {success}")
    print(f"실패      : {fail}")
    print(f"소요 시간 : {elapsed:.2f}s")
    print(f"평균 TPS  : {total / elapsed:.2f}")
    print("==============================")


if __name__ == "__main__":
    main()
