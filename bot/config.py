import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# DB 연결 정보 (기존 설정 활용)

def get_db_connection():
    return psycopg2.connect(
        host="localhost", port="15432",
        database="app", user="postgres", password="0000"
    )

'''
def get_db_connection():
    return psycopg2.connect(
        host = "heartbit-db.c3qieeu84ouk.ap-southeast-2.rds.amazonaws.com",
        port = "5432",
        database = "heartbit",
        user = "postgre",
        password = "heartbit,,1234",
        connect_timeout = 5,
        options = "-c client_encoding=UTF8"
    )
'''

def load_categories_from_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # DB에 저장된 모든 코인을 가져옴
    cur.execute("SELECT symbol, category_id FROM public.category;")
    db_data = cur.fetchall()
    cur.close()
    conn.close()
    return {row[0]: row[1] for row in db_data}


def _filter_by_allowed_symbols(category_map: dict) -> dict:
    """BOT_SYMBOLS 환경 변수가 있으면 해당 심볼만 사용 (쉼표 구분)."""
    allowed = os.getenv("BOT_SYMBOLS", "").strip()
    if not allowed:
        return category_map
    symbols = [s.strip().upper() for s in allowed.split(",") if s.strip()]
    if not symbols:
        return category_map
    return {k: v for k, v in category_map.items() if k.upper() in symbols}


# 실시간으로 카테고리 맵 생성 (BOT_SYMBOLS 설정 시 해당 코인만 사용)
_raw_category_map = load_categories_from_db()
CATEGORY_MAP = _filter_by_allowed_symbols(_raw_category_map)
COINS = list(CATEGORY_MAP.keys())

# 기존 환경 변수들
SPRING_ORDER_URL = os.getenv("SPRING_ORDER_URL")
BOT_ID = int(os.getenv("BOT_ID"))
SECRET_TOKEN = os.getenv("SECRET_TOKEN")
THREADS = int(os.getenv("THREADS"))
ORDER_INTERVAL = float(os.getenv("ORDER_INTERVAL"))


def _check_order_config():
    """주문 API 설정 검증 (403 방지용)."""
    missing = []
    if not (SPRING_ORDER_URL and SPRING_ORDER_URL.strip()):
        missing.append("SPRING_ORDER_URL")
    if not (SECRET_TOKEN and str(SECRET_TOKEN).strip()):
        missing.append("SECRET_TOKEN")
    if missing:
        print("⚠️  .env에 다음 변수가 비어 있습니다: " + ", ".join(missing))
        print("   → 403 에러는 보통 토큰/URL 미설정 또는 Spring 서버와 토큰 불일치 때문입니다.")
    elif SPRING_ORDER_URL:
        print(f"📡 주문 API: {SPRING_ORDER_URL}")