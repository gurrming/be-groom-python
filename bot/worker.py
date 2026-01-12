import time
import requests
from threading import Thread, Lock, Event

from bot.config import (
    SPRING_ORDER_URL,
    SECRET_TOKEN,
    THREADS,
    ORDER_INTERVAL
)
from bot.order import create_order

print_lock = Lock()
stop_event = Event()

success = 0
fail = 0


def send_order(order: dict):
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
                print(f"   응답: {res.text}")

    except Exception as e:
        with print_lock:
            fail += 1
            print(f"💥 요청 예외: {e}")


def bot_worker():
    while not stop_event.is_set():
        send_order(create_order())
        time.sleep(ORDER_INTERVAL)


def start():
    print("\n🚀 BOT 주문 시뮬레이션 시작 (무한 실행)")
    start_time = time.time()

    threads = []
    for i in range(THREADS):
        t = Thread(target=bot_worker, name=f"BOT-{i}")
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 종료 신호 감지")
        stop_event.set()

    for t in threads:
        t.join()

    elapsed = time.time() - start_time
    total = success + fail

    print("\n==============================")
    print(f"총 주문 수 : {total}")
    print(f"성공      : {success}")
    print(f"실패      : {fail}")
    print(f"평균 TPS  : {total / elapsed:.2f}")
    print("==============================")
