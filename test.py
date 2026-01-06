import random
import time
import requests
import psycopg2
from threading import Thread

SPRING_ORDER_URL = "http://localhost:8080/api/orders"

# =========================
# PostgreSQL 연결 정보
# =========================
DB_CONFIG = {
    "host": "localhost",
    "dbname": "app",
    "user": "postgres",
    "password": "0000",
    "port": 15432
}

# =========================
# 시뮬레이션 모드
# =========================
SIMULATION_MODE = "NORMAL"  # NORMAL | STRESS

if SIMULATION_MODE == "NORMAL":
    ORDER_INTERVAL = 0.4
    TOTAL_ORDERS_PER_USER = 50
elif SIMULATION_MODE == "STRESS":
    ORDER_INTERVAL = 0.05
    TOTAL_ORDERS_PER_USER = 500

BURST_PROBABILITY = 0.08
BURST_MULTIPLIER = 6

# =========================
# 시장 가격 (임의)
# =========================
market_prices = {
    "BTC": 50000.0, "ETH": 3000.0, "SOL": 20.0, "XRP": 0.8,
    "ADA": 1.2, "DOGE": 0.25, "AVAX": 25.0, "DOT": 10.0
}

COIN_WEIGHTS = {
    "BTC": 40, "ETH": 25, "SOL": 10, "XRP": 8,
    "ADA": 7, "DOGE": 5, "AVAX": 3, "DOT": 2
}

# =========================
# DB에서 실제 category_id 조회
# =========================
def load_category_ids():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT category_id, category_name FROM category WHERE category_delete = false")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise RuntimeError("❌ category 테이블에 데이터가 없습니다.")

    # { "BTC": 41, "ETH": 42, ... }
    return {name: cid for cid, name in rows}

CATEGORY_MAP = load_category_ids()
AVAILABLE_COINS = list(CATEGORY_MAP.keys())

print("✅ 로드된 카테고리:", CATEGORY_MAP)

# =========================
# 유틸 함수
# =========================
def update_market_prices():
    for coin in market_prices:
        change = random.uniform(-0.05, 0.05)
        market_prices[coin] *= (1 + change)
        market_prices[coin] = max(market_prices[coin], 0.01)

def decide_order_type():
    return random.choices(["BUY", "SELL"], weights=[55, 45], k=1)[0]

# =========================
# 주문 생성
# =========================
def generate_order(user_type="BOT", member_id=None):
    coin = random.choices(
        population=list(COIN_WEIGHTS.keys()),
        weights=list(COIN_WEIGHTS.values()),
        k=1
    )[0]

    is_bot = (user_type == "BOT")

    if not is_bot and member_id is None:
        raise ValueError("USER 주문에는 member_id가 필요합니다")

    return {
        "memberId": member_id if not is_bot else None,
        "categoryId": CATEGORY_MAP[coin],
        "orderPrice": round(market_prices[coin], 2),
        "orderCount": round(random.uniform(0.1, 5.0), 4),
        "orderType": decide_order_type(),  # BUY / SELL
        "isBot": is_bot                     # ⭐ DTO 기준 핵심
    }

# =========================
# 주문 전송
# =========================
def send_order(order):
    try:
        response = requests.post(SPRING_ORDER_URL, json=order, timeout=2)

        who = "BOT" if order["isBot"] else f"USER({order['memberId']})"

        if response.status_code in (200, 201):
            print(
                f"✅ {who} | "
                f"CID={order['categoryId']} | "
                f"{order['orderType']} | "
                f"{order['orderCount']} @ {order['orderPrice']}"
            )
        else:
            print(f"⚠️ 주문 실패 | {response.status_code} | {response.text}")

    except requests.exceptions.RequestException as e:
        print("❌ 서버 연결 실패:", e)


# =========================
# 시뮬레이션 실행
# =========================
def run_simulation(user_type="BOT", member_id=None):
    total_sent = 0

    for _ in range(TOTAL_ORDERS_PER_USER):
        update_market_prices()

        burst = random.random() < BURST_PROBABILITY
        burst_count = BURST_MULTIPLIER if burst else 1

        for _ in range(burst_count):
            order = generate_order(user_type, member_id)
            send_order(order)
            total_sent += 1

        time.sleep(ORDER_INTERVAL)

    print(f"\n🏁 {user_type} 종료 | 총 주문 수: {total_sent}")

# =========================
# main
# =========================
def main():
    print(f"\n🚀 시뮬레이션 시작 [{SIMULATION_MODE}]")

    start_time = time.time()

    bot_thread = Thread(target=run_simulation, args=("BOT", None))
    user_thread = Thread(target=run_simulation, args=("USER", 2))  # member_id는 DB 기준

    bot_thread.start()
    user_thread.start()

    bot_thread.join()
    user_thread.join()

    elapsed = time.time() - start_time
    print(f"\n⏱ 총 소요 시간: {elapsed:.2f}s")

if __name__ == "__main__":
    main()
