import psycopg2

# =========================
# DB 연결 설정
# =========================
conn = psycopg2.connect(
    host="localhost",
    port=15432,
    dbname="app",
    user="postgres",
    password="0000"
)
cur = conn.cursor()

# =========================
# 1. 최근 주문 확인
# =========================
cur.execute("""
SELECT order_id, member_id, is_bot, order_type, order_price, remaining_count, order_status, order_time
FROM orders
ORDER BY order_time DESC
LIMIT 10;
""")
recent_orders = cur.fetchall()
print("\n최근 10개 주문")
for o in recent_orders:
    print(o)

# =========================
# 2. BOT 주문 확인
# =========================
cur.execute("""
SELECT order_id, member_id, is_bot, order_type, order_price, remaining_count, order_status
FROM orders
WHERE is_bot = true
ORDER BY order_time DESC
LIMIT 10;
""")
bot_orders = cur.fetchall()
print("\n최근 BOT 주문 10개")
for o in bot_orders:
    print(o)

# =========================
# 3. USER 주문 확인
# =========================
cur.execute("""
SELECT order_id, member_id, is_bot, order_type, order_price, remaining_count, order_status
FROM orders
WHERE is_bot = false
ORDER BY order_time DESC
LIMIT 10;
""")
user_orders = cur.fetchall()
print("\n최근 USER 주문 10개")
for o in user_orders:
    print(o)

# =========================
# 4. 카테고리별 잔량 확인
# =========================
cur.execute("""
SELECT category_id, order_type, SUM(remaining_count) as total_remaining
FROM orders
WHERE order_status IN ('OPEN','PARTIAL')
GROUP BY category_id, order_type
ORDER BY category_id, order_type;
""")
category_summary = cur.fetchall()
print("\n카테고리별 총 잔량 (OPEN + PARTIAL)")
for s in category_summary:
    print(s)

cur.close()
conn.close()
