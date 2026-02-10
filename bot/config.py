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

# def get_db_connection():
#     return psycopg2.connect(
#         host = "heartbit-db.c3qieeu84ouk.ap-southeast-2.rds.amazonaws.com",
#         port = "5432",
#         database = "heartbit",
#         user = "postgre",
#         password = "heartbit,,1234",
#         connect_timeout = 5,
#         options = "-c client_encoding=UTF8"
#     )


def load_categories_from_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # DB에 저장된 모든 코인을 가져옴
    cur.execute("SELECT symbol, category_id FROM public.category;")
    db_data = cur.fetchall()
    cur.close()
    conn.close()
    return {row[0]: row[1] for row in db_data}

# 실시간으로 카테고리 맵 생성
CATEGORY_MAP = load_categories_from_db()
COINS = list(CATEGORY_MAP.keys())

# 기존 환경 변수들
SPRING_ORDER_URL = os.getenv("SPRING_ORDER_URL")
BOT_ID = int(os.getenv("BOT_ID"))
SECRET_TOKEN = os.getenv("SECRET_TOKEN")
THREADS = int(os.getenv("THREADS"))
ORDER_INTERVAL = float(os.getenv("ORDER_INTERVAL"))