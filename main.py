import random
import time
import requests
from threading import Thread, Lock



# 기본 설정
SPRING_ORDER_URL = "http://localhost:8080/api/orders"
BOT_MEMBER_ID = 26
SECRET_TOKEN = "heartbit-internal-secret-token"

THREADS = 4
ORDERS_PER_THREAD = 100
ORDER_INTERVAL = 0.1

print_lock = Lock()
success = 0
fail = 0



# categoryId (DB 기준)
CATEGORY_MAP = {
    "BTC": 41, "ETH": 42, "SOL": 43, "XRP": 44, "BNB": 45,
    "ADA": 46, "DOGE": 47, "AVAX": 48, "DOT": 49, "LTC": 50,
    "LINK": 51, "TRX": 52, "ATOM": 53, "FIL": 54, "ALGO": 55,
    "VET": 56, "XTZ": 57, "SHIB": 58, "EOS": 59, "MATIC": 60
}

COINS = list(CATEGORY_MAP.keys())


# 시작가
BASE_PRICE = {
    "BTC": 50000,
    "ETH": 3000,
    "SOL": 120,
    "XRP": 0.8,
    "BNB": 350,
    "ADA": 1.2,
    "DOGE": 0.25,
    "AVAX": 25,
    "DOT": 10,
    "LTC": 150,
    "LINK": 15,
    "TRX": 0.1,
    "ATOM": 9,
    "FIL": 6,
    "ALGO": 0.2,
    "VET": 0.03,
    "XTZ": 0.9,
    "SHIB": 0.00001,
    "EOS": 0.7,
    "MATIC": 0.8
}



# 가격 생성 (±5% 랜덤)
def random_price(coin):
    base = BASE_PRICE[coin]
    change_rate = random.uniform(-0.05, 0.05)  # -5% ~ +5%
    return round(base * (1 + change_rate), 4)



# 주문 생성
def create_order():
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



# 주문 전송
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
                print(f"   응답: {res.text}")

    except Exception as e:
        with print_lock:
            fail += 1
            print(f"💥 요청 예외: {e}")
            print(f"   요청: {order}")



# BOT 하나의 동작
def bot_worker():
    for _ in range(ORDERS_PER_THREAD):
        send_order(create_order())
        time.sleep(ORDER_INTERVAL)



# main
def main():
    print("\n🚀 BOT 주문 시뮬레이션 시작")
    start = time.time()

    threads = []
    for _ in range(THREADS):
        t = Thread(target=bot_worker)
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
