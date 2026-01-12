import random
import time
import requests
import multiprocessing as mp
from multiprocessing import Queue, Value, Lock

# =========================
# 기본 설정
# =========================
SPRING_ORDER_URL = "http://localhost:8080/api/orders"

BOT_MEMBER_ID = 26
SECRET_TOKEN = "heartbit-internal-secret-token"

PRODUCER_PROCESSES = 6
CONSUMER_PROCESSES = 4

QUEUE_MAXSIZE = 500
MAX_SAFE_QUEUE = 400

ORDER_INTERVAL = 0.06
FAIL_BACKOFF = 0.2

# =========================
# categoryId
# =========================
CATEGORY_MAP = {
    "BTC": 41, "ETH": 42, "SOL": 43, "XRP": 44, "BNB": 45,
    "ADA": 46, "DOGE": 47, "AVAX": 48, "DOT": 49, "LTC": 50,
    "LINK": 51, "TRX": 52, "ATOM": 53, "FIL": 54, "ALGO": 55,
    "VET": 56, "XTZ": 57, "SHIB": 58, "EOS": 59, "MATIC": 60
}

COINS = list(CATEGORY_MAP.keys())

BASE_PRICE = {
    "BTC": 50000, "ETH": 3000, "SOL": 120, "XRP": 0.8,
    "BNB": 350, "ADA": 1.2, "DOGE": 0.25, "AVAX": 25,
    "DOT": 10, "LTC": 150, "LINK": 15, "TRX": 0.1,
    "ATOM": 9, "FIL": 6, "ALGO": 0.2, "VET": 0.03,
    "XTZ": 0.9, "SHIB": 0.00001, "EOS": 0.7, "MATIC": 0.8
}

# =========================
# 주문 생성
# =========================
def random_price(coin):
    return round(BASE_PRICE[coin] * (1 + random.uniform(-0.05, 0.05)), 4)

def create_order():
    coin = random.choice(COINS)
    return {
        "memberId": BOT_MEMBER_ID,
        "categoryId": CATEGORY_MAP[coin],
        "orderPrice": random_price(coin),
        "orderCount": round(random.uniform(0.1, 3), 4),
        "orderType": random.choice(["BUY", "SELL"]),
        "isBot": True
    }

# =========================
# Producer
# =========================
def producer(order_queue, stop_event, queue_count, queue_lock, pid):
    print(f"🟢 Producer-{pid} 시작")

    while not stop_event.is_set():
        try:
            if queue_count.value >= MAX_SAFE_QUEUE:
                time.sleep(0.05)
                continue

            order_queue.put(create_order(), timeout=1)

            with queue_lock:
                queue_count.value += 1

            time.sleep(ORDER_INTERVAL)

        except Exception:
            time.sleep(0.01)

# =========================
# Consumer
# =========================
def consumer(
    order_queue, stop_event,
    queue_count, queue_lock,
    success_count, fail_count,
    cid
):
    print(f"🔵 Consumer-{cid} 시작")

    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=10
    )
    session.mount("http://", adapter)

    session.headers.update({
        "X-Internal-Token": SECRET_TOKEN,
        "Content-Type": "application/json"
    })

    while not stop_event.is_set():
        try:
            order = order_queue.get(timeout=1)

            with queue_lock:
                queue_count.value -= 1

            res = session.post(SPRING_ORDER_URL, json=order, timeout=2)

            if res.status_code == 200:
                with queue_lock:
                    success_count.value += 1
            else:
                with queue_lock:
                    fail_count.value += 1
                time.sleep(FAIL_BACKOFF)

        except Exception:
            with queue_lock:
                fail_count.value += 1
            time.sleep(0.01)

# =========================
# main
# =========================
def main():
    print("\n🚀 BOT 스트레스 테스트 시작")

    order_queue = Queue(maxsize=QUEUE_MAXSIZE)

    queue_count = Value("i", 0)
    success_count = Value("i", 0)
    fail_count = Value("i", 0)

    queue_lock = Lock()
    stop_event = mp.Event()

    processes = []

    for i in range(PRODUCER_PROCESSES):
        p = mp.Process(
            target=producer,
            args=(order_queue, stop_event, queue_count, queue_lock, i)
        )
        p.start()
        processes.append(p)

    for i in range(CONSUMER_PROCESSES):
        c = mp.Process(
            target=consumer,
            args=(
                order_queue, stop_event,
                queue_count, queue_lock,
                success_count, fail_count,
                i
            )
        )
        c.start()
        processes.append(c)

    last_success = 0

    try:
        while True:
            time.sleep(1)
            cur = success_count.value
            tps = cur - last_success
            last_success = cur

            print(
                f"📦 Queue={queue_count.value} | "
                f"TPS={tps} | "
                f"✅ Success={success_count.value} | "
                f"❌ Fail={fail_count.value}"
            )

    except KeyboardInterrupt:
        print("\n🛑 종료 중...")
        stop_event.set()

    for p in processes:
        p.join()

    print("✅ BOT 종료 완료")

if __name__ == "__main__":
    main()
