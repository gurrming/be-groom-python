import random
import time
import requests
import psycopg2
from threading import Thread, Lock

SPRING_ORDER_URL = "http://localhost:8080/api/orders"


# =========================
# 토큰 설정
# =========================
SECRET_TOKEN = "heartbit-internal-secret-token"


# =========================
# PostgreSQL 설정
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
SIMULATION_MODE = "NORMAL"  # NORMAL | STRESS | LIMIT

if SIMULATION_MODE == "NORMAL":
    ORDER_INTERVAL = 0.4
    TOTAL_ORDERS_PER_THREAD = 50
    THREADS = 2

elif SIMULATION_MODE == "STRESS":
    ORDER_INTERVAL = 0.05
    TOTAL_ORDERS_PER_THREAD = 500
    THREADS = 6

elif SIMULATION_MODE == "LIMIT":
    ORDER_INTERVAL = 0.01
    TOTAL_ORDERS_PER_THREAD = 2000
    THREADS = 20

BURST_PROBABILITY = 0.08
BURST_MULTIPLIER = 6

price_lock = Lock()
print_lock = Lock()

success_count = 0
fail_count = 0

# =========================
# 코인 시작가 + 가중치
# =========================
COIN_CONFIG = {
    "BTC":  {"price": 50000, "weight": 40},
    "ETH":  {"price": 3000,  "weight": 25},
    "SOL":  {"price": 120,   "weight": 10},
    "XRP":  {"price": 0.8,   "weight": 8},
    "BNB":  {"price": 350,   "weight": 7},
    "ADA":  {"price": 1.2,   "weight": 5},
    "DOGE": {"price": 0.25,  "weight": 4},
    "AVAX": {"price": 25,    "weight": 3},
    "DOT":  {"price": 10,    "weight": 2},
    "LTC":  {"price": 150,   "weight": 2},
    "LINK": {"price": 15,    "weight": 2},
    "TRX":  {"price": 0.1,   "weight": 2},
    "ATOM": {"price": 9,     "weight": 2},
    "FIL":  {"price": 6,     "weight": 2},
    "ALGO": {"price": 0.2,   "weight": 1},
    "VET":  {"price": 0.03,  "weight": 1},
    "XTZ":  {"price": 0.9,   "weight": 1},
    "SHIB": {"price": 0.00001, "weight": 1},
    "EOS":  {"price": 0.7,   "weight": 1},
    "MATIC":{"price": 0.8,   "weight": 2}
}

# =========================
# DB 로딩
# =========================
def load_category_ids():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT category_id, symbol
        FROM category
        WHERE category_delete = false
    """)
    rows = cur.fetchall()
    conn.close()
    # symbol 기준으로 매핑
    return {symbol: cid for cid, symbol in rows}

def load_user_ids():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT member_id
        FROM member
        WHERE member_email LIKE 'test_user_%'
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise RuntimeError("❌ 테스트 USER 계정이 없습니다.")
    return [r[0] for r in rows]

CATEGORY_MAP = load_category_ids()
USER_IDS = load_user_ids()

AVAILABLE_COINS = [c for c in COIN_CONFIG if c in CATEGORY_MAP]

market_prices = {coin: COIN_CONFIG[coin]["price"] for coin in AVAILABLE_COINS}
coin_weights = {coin: COIN_CONFIG[coin]["weight"] for coin in AVAILABLE_COINS}

# =========================
# 가격 영향
# =========================
def apply_price_impact(coin, order_type, amount):
    with price_lock:
        impact = amount * 0.0005
        if order_type == "BUY":
            market_prices[coin] *= (1 + impact)
        else:
            market_prices[coin] *= (1 - impact)

def decide_order_type():
    return random.choices(["BUY", "SELL"], weights=[55, 45])[0]

# =========================
# 주문 생성
# =========================
def generate_order(user_type, member_id):
    coin = random.choices(
        AVAILABLE_COINS,
        weights=[coin_weights[c] for c in AVAILABLE_COINS],
        k=1
    )[0]

    order_type = decide_order_type()
    order_count = round(random.uniform(0.1, 5.0), 4)

    apply_price_impact(coin, order_type, order_count)

    return {
        "memberId": None if user_type == "BOT" else member_id,
        "categoryId": CATEGORY_MAP[coin],
        "orderPrice": round(market_prices[coin], 4),
        "orderCount": order_count,
        "orderType": order_type,
        "isBot": user_type == "BOT",
        "_coin": coin
    }

# =========================
# 주문 전송 + 출력
# =========================
# =========================
# 주문 전송 + 출력 (디버깅 강화)
# =========================
def send_order(order, user_type):
    global success_count, fail_count

    try:
        res = requests.post(
            SPRING_ORDER_URL, 
            json=order,
            headers={
                "X-Secret-Token": SECRET_TOKEN,  # 토큰 추가
                "Content-Type": "application/json"          # JSON 전송
            },
            timeout=2)

        with print_lock:
            if res.status_code == 200:
                success_count += 1
                print(f"✅ [{user_type}] {order['_coin']} {order['orderType']} "
                      f"{order['orderCount']} @ {order['orderPrice']}")
            else:
                fail_count += 1
                print(f"❌ [{user_type}] FAIL {res.status_code}")
                print(f"   요청 데이터: {order}")
                print(f"   서버 응답: {res.text}")

    except Exception as e:
        with print_lock:
            fail_count += 1
            print(f"💥 [{user_type}] 요청 예외: {e}")
            print(f"   요청 데이터: {order}")

# =========================
# 스레드 실행
# =========================
def run_simulation(user_type, member_id):
    for _ in range(TOTAL_ORDERS_PER_THREAD):
        burst = random.random() < BURST_PROBABILITY
        count = BURST_MULTIPLIER if burst else 1

        for _ in range(count):
            order = generate_order(user_type, member_id)
            send_order(order, user_type)

        time.sleep(ORDER_INTERVAL)

# =========================
# main
# =========================
def main():
    print(f"\n🚀 시뮬레이션 시작 [{SIMULATION_MODE}]")
    start = time.time()
    threads = []

    user_index = 0

    for i in range(THREADS):
        if i % 2 == 0:
            t = Thread(target=run_simulation, args=("BOT", None))
        else:
            user_id = USER_IDS[user_index % len(USER_IDS)]
            user_index += 1
            t = Thread(target=run_simulation, args=("USER", user_id))

        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start
    total_orders = success_count + fail_count

    print("\n==============================")
    print(f"⏱ 총 시간: {elapsed:.2f}s")
    print(f"📦 총 주문 시도: {total_orders}")
    print(f"✅ 성공: {success_count}")
    print(f"❌ 실패: {fail_count}")
    print(f"⚡ 평균 TPS: {total_orders / elapsed:.2f}")
    print("==============================")

if __name__ == "__main__":
    main()
