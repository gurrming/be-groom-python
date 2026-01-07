import os
import random
import time
import requests
import psycopg2
from threading import Thread, Lock
from dotenv import load_dotenv

# =========================
# 환경 설정
# =========================
load_dotenv()
SPRING_ORDER_URL = os.getenv("SPRING_ORDER_URL", "http://localhost:8080/api/orders")
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "heartbit-internal-secret-token")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "dbname": os.getenv("DB_NAME", "app"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "0000"),
    "port": int(os.getenv("DB_PORT", 15432))
}

SIMULATION_MODES = {
    "NORMAL": {"interval": 0.4, "total_orders": 50, "threads": 2},
    "STRESS": {"interval": 0.05, "total_orders": 500, "threads": 6},
    "LIMIT": {"interval": 0.01, "total_orders": 2000, "threads": 20},
}
SIMULATION_MODE = "NORMAL"
BURST_PROBABILITY = 0.08
BURST_MULTIPLIER = 6

print_lock = Lock()

# =========================
# DB 로딩
# =========================
def load_category_ids():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT category_id, symbol FROM category WHERE category_delete = false")
    rows = cur.fetchall()
    conn.close()
    return {symbol: cid for cid, symbol in rows}

def load_user_ids():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT member_id FROM member WHERE member_email LIKE 'test_user_%'")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        raise RuntimeError("❌ 테스트 USER 계정이 없습니다.")
    return [r[0] for r in rows]

CATEGORY_MAP = load_category_ids()
USER_IDS = load_user_ids()

# =========================
# 코인/가격 관리
# =========================
class CoinMarket:
    def __init__(self, coin_config):
        self.market_prices = {c: coin_config[c]["price"] for c in coin_config if c in CATEGORY_MAP}
        self.coin_weights = {c: coin_config[c]["weight"] for c in coin_config if c in CATEGORY_MAP}
        self.lock = Lock()
    
    def apply_price_impact(self, coin, order_type, amount):
        with self.lock:
            impact = amount * 0.0005
            if order_type == "BUY":
                self.market_prices[coin] *= (1 + impact)
            else:
                self.market_prices[coin] *= (1 - impact)
    
    def get_price(self, coin):
        return round(self.market_prices[coin], 4)

COIN_MARKET = CoinMarket({
    "BTC": {"price": 50000, "weight": 40},
    "ETH": {"price": 3000,  "weight": 25},
    "SOL": {"price": 120,   "weight": 10},
    "XRP": {"price": 0.8,   "weight": 8},
    # ... 나머지 코인 생략
})

AVAILABLE_COINS = list(COIN_MARKET.market_prices.keys())

# =========================
# 주문 생성/전송
# =========================
class OrderGenerator:
    @staticmethod
    def decide_order_type():
        return random.choices(["BUY", "SELL"], weights=[55, 45])[0]

    @staticmethod
    def generate_order(user_type, member_id):
        coin = random.choices(
            AVAILABLE_COINS, weights=[COIN_MARKET.coin_weights[c] for c in AVAILABLE_COINS]
        )[0]
        order_type = OrderGenerator.decide_order_type()
        order_count = round(random.uniform(0.1, 5.0), 4)
        COIN_MARKET.apply_price_impact(coin, order_type, order_count)
        return {
            "memberId": None if user_type == "BOT" else member_id,
            "categoryId": CATEGORY_MAP[coin],
            "orderPrice": COIN_MARKET.get_price(coin),
            "orderCount": order_count,
            "orderType": order_type,
            "isBot": user_type == "BOT",
            "_coin": coin
        }

class OrderSender:
    def __init__(self):
        self.success_count = 0
        self.fail_count = 0
        self.lock = Lock()

    def send_order(self, order, user_type):
        try:
            res = requests.post(
                SPRING_ORDER_URL,
                json=order,
                headers={"X-Internal-Token": SECRET_TOKEN, "Content-Type": "application/json"},
                timeout=2
            )
            with self.lock:
                if res.status_code == 200:
                    self.success_count += 1
                    with print_lock:
                        print(f"✅ [{user_type}] {order['_coin']} {order['orderType']} "
                              f"{order['orderCount']} @ {order['orderPrice']}")
                else:
                    self.fail_count += 1
                    with print_lock:
                        print(f"❌ [{user_type}] FAIL {res.status_code}, {res.text}")
        except Exception as e:
            with self.lock:
                self.fail_count += 1
                with print_lock:
                    print(f"💥 [{user_type}] 요청 예외: {e}, 데이터: {order}")

ORDER_SENDER = OrderSender()

# =========================
# 스레드 시뮬레이션
# =========================
def run_simulation(user_type, member_id):
    config = SIMULATION_MODES[SIMULATION_MODE]
    for _ in range(config["total_orders"]):
        burst = random.random() < BURST_PROBABILITY
        count = BURST_MULTIPLIER if burst else 1
        for _ in range(count):
            order = OrderGenerator.generate_order(user_type, member_id)
            ORDER_SENDER.send_order(order, user_type)
        time.sleep(config["interval"])

# =========================
# main
# =========================
def main():
    config = SIMULATION_MODES[SIMULATION_MODE]
    print(f"\n🚀 시뮬레이션 시작 [{SIMULATION_MODE}]")
    start = time.time()
    threads = []
    user_index = 0

    for i in range(config["threads"]):
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
    total_orders = ORDER_SENDER.success_count + ORDER_SENDER.fail_count

    print("\n==============================")
    print(f"⏱ 총 시간: {elapsed:.2f}s")
    print(f"📦 총 주문 시도: {total_orders}")
    print(f"✅ 성공: {ORDER_SENDER.success_count}")
    print(f"❌ 실패: {ORDER_SENDER.fail_count}")
    print(f"⚡ 평균 TPS: {total_orders / elapsed:.2f}")
    print("==============================")

if __name__ == "__main__":
    main()
